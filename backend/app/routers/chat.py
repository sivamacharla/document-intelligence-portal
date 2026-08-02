from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..db import get_db
from ..rag.embeddings import get_embedder
from ..rag.llm import generate_answer
from ..rag.vector_store import get_store_for_user

router = APIRouter(prefix="/chat", tags=["chat"])


def _retrieve_and_answer(user_id: int, message: str):
    """Shared by both the plain and streaming endpoints: retrieval + answer
    generation is identical, only how the answer is delivered differs.
    """
    embedder = get_embedder()
    query_vec = embedder.embed([message])[0]
    store = get_store_for_user(user_id, embedder.dim if hasattr(embedder, "dim") else query_vec.shape[0])
    hits = store.search(query_vec, k=4)

    answer, cited_indices = generate_answer(message, [rec.chunk_text for rec, _ in hits])

    # order sources to match the [1], [2]... markers inline in the answer;
    # fall back to all retrieved hits if nothing was specifically cited
    ordered_hits = [hits[i] for i in cited_indices] if cited_indices else hits
    return answer, ordered_hits


@router.post("/query", response_model=schemas.ChatResponse)
def query(payload: schemas.ChatRequest, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    db.add(models.ChatMessage(user_id=user.id, conversation_id=payload.conversation_id, role="user", content=payload.message))

    answer, ordered_hits = _retrieve_and_answer(user.id, payload.message)

    db.add(models.ChatMessage(user_id=user.id, conversation_id=payload.conversation_id, role="assistant", content=answer))
    db.commit()

    sources = [
        schemas.ChatSource(document_id=rec.document_id, filename=rec.filename, chunk_preview=rec.chunk_text[:160], score=round(score, 4))
        for rec, score in ordered_hits
    ]
    return schemas.ChatResponse(answer=answer, sources=sources)


@router.post("/query/stream")
def query_stream(payload: schemas.ChatRequest, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    db.add(models.ChatMessage(user_id=user.id, conversation_id=payload.conversation_id, role="user", content=payload.message))
    db.commit()

    answer, ordered_hits = _retrieve_and_answer(user.id, payload.message)
    sources = [
        {"document_id": rec.document_id, "filename": rec.filename, "chunk_preview": rec.chunk_text[:160], "score": round(score, 4)}
        for rec, score in ordered_hits
    ]

    async def event_gen():
        # word-by-word delivery to simulate token streaming; the answer
        # itself is already fully computed above (offline mock is instant),
        # this just gives the client a real streaming wire format to consume
        for word in answer.split(" "):
            yield f"data: {json.dumps({'delta': word + ' '})}\n\n"
            await asyncio.sleep(0.03)

        db.add(models.ChatMessage(user_id=user.id, conversation_id=payload.conversation_id, role="assistant", content=answer))
        db.commit()

        yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.get("/history/{conversation_id}", response_model=list[schemas.ChatHistoryItem])
def history(conversation_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.user_id == user.id, models.ChatMessage.conversation_id == conversation_id)
        .order_by(models.ChatMessage.created_at)
        .all()
    )
