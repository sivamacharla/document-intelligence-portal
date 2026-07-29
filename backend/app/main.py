from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
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


# Serve the built Angular app (frontend/dist/frontend/browser) from the same
# origin/process in production, so the whole app is a single deployable
# service with no CORS to worry about. Falls back to index.html for any
# non-API path so Angular's client-side router handles it (SPA routing).
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist" / "frontend" / "browser"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets") if (FRONTEND_DIST / "assets").exists() else None

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
