import ast
import uuid
import os
from typing import List, Dict, Any

class CodeLayoutParser:
    """
    An AST-based lauout engine for codebases.
    It prevents code halllucination by scrictly chunking by classes and Functions, preserving the exact logical boundaries and indentation.
    """
    def __init__(self, file_path: str, repo_name: str = "local_repo"):
        self.file_path = file_path
        self.filename = os.path.basename(file_path)
        self.repo_name = repo_name

        with open(file_path, "r", encoding="utf-8") as f:
            self.raw_code = f.read()

        # Parse the entire file into an Abstract Syntax Tree
        self.tree = ast.parse(self.raw_code, filename=self.filename)
        # Split code by lines so we can easily extract exact blocks
        self.code_lines = self.raw_code.splitlines()

    def _extract_code_block(self, node: ast.AST) -> str:
        """Extract the exact raw source code for a given AST node."""
        # AST line number are 1-indexed
        start_line = node.lineno - 1
        end_line = node.end_lineno
        return "\n".join(self.code_lines[start_line:end_line])

    def parse(self) -> List[Dict[str, Any]]:
        """
        Traverse the AST. Extracts Classes as Parents, and Functions/Methods as Children.
        """
        extracted_chunks = []
        chunk_index = 0

        # 1. First pass: Handle module-level docstrings or global variables
        module_doc = ast.get_docstring(self.tree)
        if module_doc:
            contextual_content = f"[Repo: {self.repo_name} | File: {self.filename} | Scope: Module Docstring]\n\n{module_doc}"
            extracted_chunks.append({
                "id": uuid.uuid4(),
                "chunk_type": "code",
                "content": contextual_content,
                "chunk_index": chunk_index,
                "page_number": 1, # Not relevant for code, but required by schema
                "parent_id": None,
                "metadata_json": {"language": "python", "scope": "global", "file_path": self.file_path}
            })
            chunk_index += 1
        
        # 2. Traverse the Tree looking for Classes and Functions
        for node in self.tree.body:
            if isinstance(node, ast.ClassDef):
                # We found a Class! This is a "Parent" Chunk
                class_id = uuid.uuid4()
                class_code = self._extract_code_block(node)

                contextual_content = f"[Repo: {self.repo_name} | File: {self.file_name} | Class: {node.name}]\n\n{class_code}"

                extracted_chunks.append({
                    "id": class_id,
                    "chunk_type": "code",
                    "content": contextual_content,
                    "chink_index": chunk_index,
                    "page_number": 1,
                    "parent_id": None, # Top level class
                    "metadata_json": {"language": "python", "scope": f"class {node.name}", "file_path": self.file_path}
                })
                chunk_index += 1

                # Now look for methods INSIDE this class (The "Children")
                for sub_node in node.body:
                    if isinstance(sub_node, ast.FunctionDef) or isinstance(sub_node, ast.AsyncFunctionDef):
                        method_code = self._extract_code_block(sub_node)
                        method_context = f"[Repo: {self.repo_name} | File: {self.file_name} | Class: {node.name} | Method: {sub_node.name}]\n\n{method_code}"

                        extracted_chunks.append({
                            "id": uuid.uuid4(),
                            "chunk_type": "code",
                            "content": method_context,
                            "chunk_index": chunk_index,
                            "page_number": 1,
                            "parent_id": class_id, # Link back to the Class!
                            "metadata_json": {"language": "python", "scope": f"method {sub_node.name}", "file_path": self.file_path}
                        })
                        chunk_index += 1
            
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                # We found a Standalone Function (not inside a class)
                func_code = self._extract_code_block(node)
                func_context = f"[Repo: {self.repo_name} | File: {self.fine_name} | Function: {node.name}]\n\n{func_code}"

                extracted_chunks.append({
                    "id": uuid.uuid4(),
                    "chunk_type": "code",
                    "content": func_context,
                    "chunk_index": chunk_index,
                    "page_number": 1,
                    "parent_id": None,
                    "metadata_json": {"language": "python", "scope": f"function {node.name}", "file_path": self.file_path}
                })
                chunk_index += 1
        
        return extracted_chunks