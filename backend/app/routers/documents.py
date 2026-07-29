from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas, storage
from ..auth import get_current_user
from ..db import get_db
from ..rag.chunking import chunk_text, extract_text
from ..rag.embeddings import get_embedder
from ..rag.vector_store import ChunkRecord, get_store_for_user

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_TYPES = {"application/pdf", "text/plain", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


@router.post("/upload", response_model=schemas.DocumentOut)
async def upload_document(
    file: UploadFile,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    content = await file.read()
    content_type = file.content_type or "text/plain"

    text = extract_text(content, content_type, file.filename)
    chunks = chunk_text(text)
    if not chunks:
        raise HTTPException(status_code=400, detail="No extractable text found in document")

    storage_path = storage.save(file.filename, content)
    doc = models.Document(
        owner_id=user.id,
        filename=file.filename,
        storage_path=storage_path,
        content_type=content_type,
        chunk_count=len(chunks),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    embedder = get_embedder()
    vectors = embedder.embed(chunks)
    store = get_store_for_user(user.id, embedder.dim if hasattr(embedder, "dim") else vectors.shape[1])
    records = [ChunkRecord(document_id=doc.id, filename=doc.filename, chunk_text=c) for c in chunks]
    store.add(vectors, records)

    return doc


@router.get("", response_model=list[schemas.DocumentOut])
def list_documents(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    query = db.query(models.Document)
    if user.role != "admin":
        query = query.filter(models.Document.owner_id == user.id)
    return query.order_by(models.Document.created_at.desc()).all()


@router.delete("/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.owner_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this document")

    storage.delete(doc.storage_path)
    store = get_store_for_user(doc.owner_id, dim=256)
    store.remove_document(document_id)
    db.delete(doc)
    db.commit()
    return {"status": "deleted"}
