# pyrefly: ignore [missing-import]
import fitz  # PyMuPDF: Blazing fast C-bound PDF parser
# pyrefly: ignore [missing-import]
import pdfplumber # Specifically for vector-line table reconstruction
import os
import uuid
from typing import List, Dict, Any, Tuple
from collections import Counter

class PDFLayoutParser:
    """
    A hyper-optimized, CPU-bound layout engine.
    It reconstructs PDF context by analyzing font geometries and vector lines,
    avoiding expensive Vision AI models.
    """
    def __init__(self, file_path: str, filename: str, image_output_dir: str = "./uploads/images"):
        self.file_path = file_path
        self.filename = filename
        self.image_output_dir = image_output_dir
        
        # Ensure image directory exists
        os.makedirs(self.image_output_dir, exist_ok=True)
        
        # We open the document in both libraries simultaneously. 
        # fitz is for text/images, pdfplumber is strictly for tables.
        self.doc_fitz = fitz.open(self.file_path)
        self.doc_plumber = pdfplumber.open(self.file_path)
        
        # Calculate the base font size to heuristically detect headers
        self.base_font_size = self._calculate_base_font()

    def _calculate_base_font(self) -> float:
        """
        Scans the first 3 pages to find the most common font size.
        Anything significantly larger than this is mathematically a 'Header'.
        """
        font_sizes = []
        pages_to_scan = min(3, len(self.doc_fitz))
        
        for page_num in range(pages_to_scan):
            page = self.doc_fitz[page_num]
            blocks = page.get_text("dict")["blocks"]
            for b in blocks:
                if b['type'] == 0: # Type 0 is text
                    for line in b["lines"]:
                        for span in line["spans"]:
                            font_sizes.append(round(span["size"]))
                            
        if not font_sizes:
            return 11.0 # Fallback standard size
            
        # Return the most common font size
        return Counter(font_sizes).most_common(1)[0][0]

    def _intersects(self, bbox1: Tuple, bbox2: Tuple) -> bool:
        """Check if two bounding boxes intersect. Used to separate text from tables."""
        x0_1, y0_1, x1_1, y1_1 = bbox1
        x0_2, y0_2, x1_2, y1_2 = bbox2
        return not (x1_1 <= x0_2 or x0_1 >= x1_2 or y1_1 <= y0_2 or y0_1 >= y1_2)

    def _semantic_sliding_window(self, text: str, prefix: str, max_chars: int = 2000, overlap_chars: int = 300) -> List[str]:
        """
        The Architect's Sliding Window.
        Never cuts a word or sentence in half. Snaps boundaries to periods, newlines, or spaces.
        """
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            # If the remaining text fits in one chunk, take it all
            if text_len - start <= max_chars:
                chunks.append(f"{prefix}\n\n{text[start:].strip()}")
                break

            # Initial hard stop
            end = start + max_chars

            # 1. SNAP BACKWARDS: Find the safest place to end Chunk A
            # Try newline first, then a period + space (end of sentence), then just a space
            semantic_end = text.rfind('\n', start, end)
            if semantic_end == -1 or semantic_end <= start + (max_chars // 2):
                semantic_end = text.rfind('. ', start, end)
                
            if semantic_end != -1 and semantic_end > start:
                end = semantic_end + 1 # Include the period/newline
            else:
                # Absolute fallback: snap to the nearest space so we don't cut a word
                space_end = text.rfind(' ', start, end)
                if space_end != -1 and space_end > start:
                    end = space_end

            # Extract Chunk A
            chunks.append(f"{prefix}\n\n{text[start:end].strip()}")

            # 2. OVERLAP: Step backward for the next chunk, but snap it to a sentence start
            next_start = end - overlap_chars
            if next_start <= start:
                next_start = end # Failsafe to prevent infinite loops

            # SNAP FORWARDS: Find the nearest end-of-sentence in the overlap region
            semantic_next = text.find('. ', next_start, end)
            if semantic_next != -1:
                start = semantic_next + 2 # Start right after the period and space
            else:
                semantic_next = text.find('\n', next_start, end)
                if semantic_next != -1:
                    start = semantic_next + 1
                else:
                    space_next = text.find(' ', next_start, end)
                    if space_next != -1:
                        start = space_next + 1
                    else:
                        start = next_start # Fallback

        return chunks

    def parse(self) -> List[Dict[str, Any]]:
        """
        The Main Engine Loop. Reads top-to-bottom, applying rolling context.
        """
        extracted_chunks = []
        chunk_index = 0
        
        # THE ROLLING CONTEXT
        current_section = "General Introduction"
        current_parent_id = None # Will point to the UUID of the last detected header

        for page_num in range(len(self.doc_fitz)):
            page_fitz = self.doc_fitz[page_num]
            page_plumber = self.doc_plumber.pages[page_num]
            
            # 1. EXTRACT TABLES FIRST (So we can ignore their text later)
            tables = page_plumber.find_tables()
            table_bboxes = []
            
            for table in tables:
                table_bboxes.append(table.bbox)
                markdown_grid = self._table_to_markdown(table.extract())
                
                # The "One-Liner" Context Prefix
                contextual_content = f"[File: {self.filename} | Section: {current_section} | Type: Table]\n\n{markdown_grid}"
                
                chunk_id = uuid.uuid4()
                extracted_chunks.append({
                    "id": chunk_id,
                    "chunk_type": "table",
                    "content": contextual_content,
                    "chunk_index": chunk_index,
                    "page_number": page_num + 1,
                    "parent_id": current_parent_id,
                    "metadata_json": {"format": "markdown", "parent_section": current_section}
                })
                chunk_index += 1

            # 2. EXTRACT TEXT & DETECT HEADERS
            # We get blocks and sort them vertically (y0 coordinate) to read top-to-bottom
            blocks = page_fitz.get_text("dict")["blocks"]
            blocks.sort(key=lambda b: b["bbox"][1]) 

            for b in blocks:
                if b["type"] == 0: # Text Block
                    block_bbox = b["bbox"]
                    
                    # If this text is inside a table we already extracted, skip it!
                    is_in_table = any(self._intersects(block_bbox, t_bbox) for t_bbox in table_bboxes)
                    if is_in_table:
                        continue

                    # Analyze the text block
                    text_content = ""
                    max_font_in_block = 0
                    
                    for line in b["lines"]:
                        for span in line["spans"]:
                            text_content += span["text"] + " "
                            if span["size"] > max_font_in_block:
                                max_font_in_block = round(span["size"])
                    
                    text_content = text_content.strip()
                    if not text_content:
                        continue

                    # --- HEURISTIC HEADER DETECTION ---
                    # If the font is larger than our base body font by at least 2 points, it's a header.
                    if max_font_in_block >= self.base_font_size + 2:
                        current_section = text_content[:100] # Update the rolling context
                        current_parent_id = uuid.uuid4()     # Create a new parent lineage node
                        
                        # Save the header itself as a chunk
                        extracted_chunks.append({
                            "id": current_parent_id,
                            "chunk_type": "text",
                            "content": f"[File: {self.filename} | HEADER]\n\n{text_content}",
                            "chunk_index": chunk_index,
                            "page_number": page_num + 1,
                            "parent_id": None, # Headers are top-level
                            "metadata_json": {"is_header": True}
                        })
                        chunk_index += 1
                    
                    else:
                        # --- NORMAL PARAGRAPH (Contextualized & Token-Safe) ---
                        # If a paragraph block is dangerously long (e.g., > 2000 chars roughly ~500 tokens)
                        if len(text_content) > 2000:
                            prefix = f"[File: {self.filename} | Section: {current_section}]"
                            windowed_chunks = self._semantic_sliding_window(text_content, prefix)
                            
                            for slice_content in windowed_chunks:
                                extracted_chunks.append({
                                    "id": uuid.uuid4(),
                                    "chunk_type": "text",
                                    "content": slice_content,
                                    "chunk_index": chunk_index,
                                    "page_number": page_num + 1,
                                    "parent_id": current_parent_id, # Links back to the Header
                                    "metadata_json": {"is_windowed": True}
                                })
                                chunk_index += 1
                        else:
                            # Standard size paragraph
                            contextual_content = f"[File: {self.filename} | Section: {current_section}]\n\n{text_content}"
                            extracted_chunks.append({
                                "id": uuid.uuid4(),
                                "chunk_type": "text",
                                "content": contextual_content,
                                "chunk_index": chunk_index,
                                "page_number": page_num + 1,
                                "parent_id": current_parent_id,
                                "metadata_json": {}
                            })
                            chunk_index += 1
                        
                elif b["type"] == 1: # Image Block
                    # 3. RIP IMAGES TO DISK
                    image_bytes = b.get("image")
                    if image_bytes:
                        img_filename = f"{uuid.uuid4()}.png"
                        img_path = os.path.join(self.image_output_dir, img_filename)
                        
                        with open(img_path, "wb") as f:
                            f.write(image_bytes)
                            
                        chunk_id = uuid.uuid4()
                        extracted_chunks.append({
                            "id": chunk_id,
                            "chunk_type": "image",
                            # We leave content blank or placeholder for now. 
                            # The background VLM worker will update this later.
                            "content": f"[File: {self.filename} | Section: {current_section}]\n\n[IMAGE PENDING VLM ANALYSIS]",
                            "chunk_index": chunk_index,
                            "page_number": page_num + 1,
                            "parent_id": current_parent_id,
                            "metadata_json": {
                                "storage_path": img_path,
                                "status": "PENDING_VISION"
                            }
                        })
                        chunk_index += 1

        self.doc_fitz.close()
        self.doc_plumber.close()
        return extracted_chunks

    def _table_to_markdown(self, grid: List[List[str]]) -> str:
        """Converts a 2D array from pdfplumber into a Markdown table."""
        if not grid or not grid[0]:
            return ""
            
        md = ""
        for i, row in enumerate(grid):
            # Clean up newlines inside cells
            clean_row = [str(cell).replace('\n', ' ').strip() if cell else "" for cell in row]
            md += "| " + " | ".join(clean_row) + " |\n"
            
            # Add the markdown separator after the header row
            if i == 0:
                md += "|" + "|".join(["---"] * len(clean_row)) + "|\n"
        return md