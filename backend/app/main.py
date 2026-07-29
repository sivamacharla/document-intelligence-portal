from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import models
from .auth import require_role
from .db import Base, engine, get_db
from .routers import auth, chat, documents

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Enterprise AI Document Intelligence Portal")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/admin/stats")
def admin_stats(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    """RBAC-gated: only users with role=admin can reach this."""
    return {
        "total_users": db.query(models.User).count(),
        "total_documents": db.query(models.Document).count(),
        "total_chat_messages": db.query(models.ChatMessage).count(),
    }
