from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import aiofiles
import os
import uuid
import shutil

from app.database.core import get_db
from app.database.models import Document, DocumentCategory, DocumentStatus
from app.services.ingestion.coordinator import process_document_pipeline
from app.services.ingestion.pdf_parser import PDFLayoutParser

router = APIRouter(
    prefix="/api/v1/documents",
    tags=["Documents & Ingestion"]
)

# Ensure our upload directory exists
UPLOAD_DIR = "./uploads/raw_documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)

IMAGE_UPLOAD_DIR = "./uploads/images"
os.makedirs(IMAGE_UPLOAD_DIR, exist_ok=True)

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

@router.post("/upload_image")
async def upload_image(file: UploadFile = File(...)):
    """
    HTTP Transport Layer: Receives an image, saves it to the local uploads directory, 
    and returns the file path for the Swarm to attach.
    """
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files are allowed.")

    # 1. Generate a secure, unique filename
    secure_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(IMAGE_UPLOAD_DIR, secure_filename)

    # 2. Stream to disk asynchronously
    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            while content := await file.read(1024 * 1024):  # 1MB chunks
                await out_file.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save image: {str(e)}")

    # We return the URL path that the frontend can use to display it,
    # which is also the exact relative path the backend will read from disk.
    return {
        "file_path": f"/uploads/images/{secure_filename}"
    }
