# Enterprise AI Document Intelligence Portal

A full-stack AI-powered document intelligence platform: upload documents,
then search and query them through a conversational chatbot with
role-based access control.

## Architecture

**Backend** (`backend/`, FastAPI):
- **Auth** (`app/auth.py`) — JWT-based authentication, bcrypt password
  hashing, `require_role()` dependency for RBAC.
- **Storage** (`app/storage.py`) — local filesystem behind an S3-shaped
  interface (`save`/`read`/`delete`), so swapping in real S3 is a
  drop-in change.
- **RAG pipeline** (`app/rag/`):
  - `chunking.py` — parses PDF/DOCX/TXT and splits into overlapping chunks.
  - `embeddings.py` — pluggable embedder; deterministic hashed
    bag-of-words by default (offline, no download), or real
    `sentence-transformers` via `EMBEDDING_PROVIDER=huggingface`.
  - `vector_store.py` — per-user FAISS index (falls back to an exact
    numpy cosine-search index with the same interface if `faiss-cpu`
    isn't installed), so retrieval never crosses account boundaries.
  - `llm.py` — answer generation from retrieved chunks; offline
    extractive mock by default, real model via `LLM_PROVIDER=openai`.
- **Data** — SQLAlchemy models (`User`, `Document`, `ChatMessage`) on
  SQLite by default; point `DATABASE_URL` at Postgres for production.

**Frontend** (`frontend/`, Angular 17, standalone components):
- JWT stored client-side, attached via an `HttpInterceptor`
  (`core/auth.interceptor.ts`).
- Route guards (`core/auth.guard.ts`) gate `/chat` (any authenticated
  user) and `/admin` (role must be `admin`) — mirroring the backend's
  own RBAC check on `/admin/stats`, so the restriction is enforced twice,
  not just hidden in the UI.
- `chat/` — conversation UI + cited sources per answer.
- `documents/` — upload, list, delete.
- `admin/` — role-gated usage dashboard.

## Run it

**Backend:**
```bash
cd backend
python -m venv venv && venv\Scripts\activate   # or source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002
```

**Frontend** (in a second terminal):
```bash
cd frontend
npm install
npm start
```

Open `http://localhost:4200`, register a user (or an `admin`), upload a
PDF/DOCX/TXT file, and ask questions about it. Log in as an `admin`-role
account to see `/admin`.

**Or via Docker** (backend only — run the frontend with `npm start` against it):
```bash
docker compose up --build
```

## Why this design

Every "swap for the real thing" seam is explicit and isolated: storage
behind an interface for S3, embeddings/LLM behind provider flags, vector
store behind a FAISS-or-fallback interface. The app is fully functional
offline for a portfolio demo, but nothing about the architecture would
need to change to point it at production infrastructure.
