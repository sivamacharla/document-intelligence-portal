from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..db import get_db
from ..rag.embeddings import get_embedder
from ..rag.llm import generate_answer
from ..rag.vector_store import get_store_for_user

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/query", response_model=schemas.ChatResponse)
def query(payload: schemas.ChatRequest, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    db.add(models.ChatMessage(user_id=user.id, conversation_id=payload.conversation_id, role="user", content=payload.message))

    embedder = get_embedder()
    query_vec = embedder.embed([payload.message])[0]
    store = get_store_for_user(user.id, embedder.dim if hasattr(embedder, "dim") else query_vec.shape[0])
    hits = store.search(query_vec, k=4)

    answer = generate_answer(payload.message, [rec.chunk_text for rec, _ in hits])

    db.add(models.ChatMessage(user_id=user.id, conversation_id=payload.conversation_id, role="assistant", content=answer))
    db.commit()

    sources = [
        schemas.ChatSource(document_id=rec.document_id, filename=rec.filename, chunk_preview=rec.chunk_text[:160], score=round(score, 4))
        for rec, score in hits
    ]
    return schemas.ChatResponse(answer=answer, sources=sources)


@router.get("/history/{conversation_id}", response_model=list[schemas.ChatHistoryItem])
def history(conversation_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.user_id == user.id, models.ChatMessage.conversation_id == conversation_id)
        .order_by(models.ChatMessage.created_at)
        .all()
    )
