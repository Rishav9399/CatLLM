from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import aiofiles
import os
import uuid
import shutil

from app.database.core import get_db
from app.database.models import Document, DocumentCategory, DocumentStatus
from app.services.ingestion.pdf_parser import PDFLayoutParser

router = APIRouter(
    prefix="/api/v1/documents",
    tags=["Documents & Ingestion"]
)

# Ensure our upload directory exists
UPLOAD_DIR = "./uploads/raw_documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    HTTP Transport Layer: Receives the file, creates a pending database record,
    and hands the actual heavy lifting off to the Service layer.
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Currently only PDF files are supported.")

    # 1. Generate a secure, unique filename to prevent overwriting
    secure_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, secure_filename)

    # 2. Stream the file to disk asynchronously (Never load a 100MB PDF into RAM)
    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            # Read in chunks
            while content := await file.read(1024 * 1024):  # 1MB chunks
                await out_file.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    file_size = os.path.getsize(file_path)

    # 3. Create the Database Record (Status: PENDING)
    new_doc = Document(
        filename=file.filename,
        file_type=file.content_type,
        file_size_bytes=file_size,
        category=DocumentCategory.STANDARD, # We can make this dynamic later
        status=DocumentStatus.PENDING
    )
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)

    # 4. The Architect's Move: Background processing!
    # The parser in the Canvas takes 2-3 seconds. We don't make the user wait.
    # We return a '202 Accepted' instantly, and run the parser in the background.
    background_tasks.add_task(process_document_pipeline, new_doc.id, file_path, file.filename)

    return {
        "message": "Document uploaded successfully. Processing started.",
        "document_id": str(new_doc.id),
        "status": new_doc.status
    }

async def process_document_pipeline(document_id: uuid.UUID, file_path: str, original_filename: str):
    """
    This is a stub for our Coordinator Service. 
    It will update the DB status to PARSING, instantiate the PDFLayoutParser 
    from our Canvas, get the chunks, and save them to the database.
    """
    print(f"--- Background worker started for {original_filename} ---")
    
    # In the next step, we will wire this function to actually instantiate 
    # the PDFLayoutParser from our Canvas and save the returned chunks to the DB!
    pass