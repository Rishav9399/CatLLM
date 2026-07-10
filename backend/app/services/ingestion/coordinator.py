import asyncio
import uuid
import logging
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

# We import the Session Factory directly because background tasks 
# need to create their own independent database connections.
from app.database.core import AsyncSessionLocal
from app.database.models import Document, Chunk, DocumentStatus
from app.services.ingestion.pdf_parser import PDFLayoutParser

logger = logging.getLogger(__name__)

async def process_document_pipeline(document_id: uuid.UUID, file_path: str, original_filename: str):
    """
    The Master Conductor.
    Bridges the CPU-bound layout parser with the I/O-bound async database.
    """
    # Create an independent database session for this background thread
    async with AsyncSessionLocal() as db:
        try:
            # 1. Update status to PARSING
            await db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(status=DocumentStatus.PARSING)
            )
            await db.commit()
            
            logger.info(f"Starting layout extraction for {original_filename}")

            # 2. Instantiate our parser
            parser = PDFLayoutParser(file_path=file_path, filename=original_filename)
            
            # 3. THE ARCHITECT'S SHIELD: Run the blocking parser in a separate thread!
            # This prevents PyMuPDF/pdfplumber from freezing the FastAPI event loop.
            chunks_data = await asyncio.to_thread(parser.parse)
            
            # 4. Convert the raw Python dictionaries into SQLAlchemy ORM objects
            db_chunks = []
            for item in chunks_data:
                chunk = Chunk(
                    id=item["id"],
                    document_id=document_id,
                    chunk_type=item["chunk_type"],
                    content=item["content"],
                    chunk_index=item["chunk_index"],
                    page_number=item["page_number"],
                    parent_id=item["parent_id"],
                    metadata_json=item["metadata_json"]
                )
                db_chunks.append(chunk)
            
            # Bulk save all chunks to the database
            db.add_all(db_chunks)
            
            # 5. Update the Document status to EMBEDDING (ready for the Vector DB)
            await db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(
                    status=DocumentStatus.EMBEDDING,
                    total_chunks=len(db_chunks)
                )
            )
            await db.commit()
            logger.info(f"Successfully parsed {len(db_chunks)} chunks for {original_filename}")

        except Exception as e:
            logger.error(f"Failed to process document {document_id}: {str(e)}")
            # Rollback any failed database transactions
            await db.rollback()
            
            # Mark document as FAILED so the UI can notify the user
            await db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(status=DocumentStatus.FAILED)
            )
            await db.commit()