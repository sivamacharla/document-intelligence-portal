"""Document parsing + chunking for PDF, Word, and text files, feeding the
embedding/indexing step of the RAG pipeline."""
from __future__ import annotations

import io

from docx import Document as DocxDocument
from pypdf import PdfReader

from ..config import CHUNK_OVERLAP_WORDS, CHUNK_SIZE_WORDS


def extract_text(content: bytes, content_type: str, filename: str) -> str:
    if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if filename.lower().endswith(".docx"):
        doc = DocxDocument(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs)

    return content.decode("utf-8", errors="ignore")


def chunk_text(text: str, size: int = CHUNK_SIZE_WORDS, overlap: int = CHUNK_OVERLAP_WORDS) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap
    return chunks
