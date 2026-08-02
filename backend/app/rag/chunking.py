"""Document parsing + chunking for PDF, Word, and text files, feeding the
embedding/indexing step of the RAG pipeline."""
from __future__ import annotations

import io
import re

from docx import Document as DocxDocument
from pypdf import PdfReader

from ..config import CHUNK_OVERLAP_WORDS, CHUNK_SIZE_WORDS


def _dewrap_pdf_text(text: str) -> str:
    """pypdf's extract_text() emits one line per visual line in the PDF,
    including line wraps in the middle of a sentence. Left as-is, downstream
    sentence-splitting treats every wrap as a sentence boundary and answers
    come out truncated mid-thought (e.g. "...using LangChain and").

    Re-joins lines that don't end a thought (no terminal punctuation, not a
    heading, not a new bullet) with the next line, so wrapped sentences
    read as one sentence again while headings/bullets stay on their own line.
    """
    lines = [l.strip() for l in text.split("\n")]
    paragraphs: list[str] = []
    buffer = ""

    for line in lines:
        if not line:
            if buffer:
                paragraphs.append(buffer)
                buffer = ""
            continue

        looks_like_heading = line.isupper() and len(line.split()) <= 6
        starts_new_bullet = bool(re.match(r"^[•●▪·\-–*]\s|^\d+[.)]\s", line))

        if looks_like_heading:
            if buffer:
                paragraphs.append(buffer)
            paragraphs.append(line)
            buffer = ""
        elif not buffer:
            buffer = line
        elif starts_new_bullet or re.search(r"[.!?:]$", buffer):
            paragraphs.append(buffer)
            buffer = line
        else:
            buffer = f"{buffer} {line}"

    if buffer:
        paragraphs.append(buffer)

    return "\n".join(paragraphs)


def _ensure_terminal_punctuation(text: str) -> str:
    """chunk_text() below flattens all whitespace -- including the newlines
    between paragraphs/headings -- into single spaces, since it works on a
    flat list of words. Without this, a heading like "EXPERIENCE" with no
    punctuation of its own would fuse with whatever line follows it once
    chunked, and sentence-splitting downstream could no longer tell them
    apart. Giving every non-empty line a terminal mark first means that
    boundary survives the flattening.
    """
    lines = [l.strip() for l in text.split("\n")]
    fixed = [l if not l or re.search(r"[.!?:]$", l) else f"{l}." for l in lines]
    return "\n".join(fixed)


def extract_text(content: bytes, content_type: str, filename: str) -> str:
    if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        raw = "\n".join(page.extract_text() or "" for page in reader.pages)
        text = _dewrap_pdf_text(raw)
    elif filename.lower().endswith(".docx"):
        doc = DocxDocument(io.BytesIO(content))
        text = "\n".join(p.text for p in doc.paragraphs)
    else:
        text = content.decode("utf-8", errors="ignore")

    return _ensure_terminal_punctuation(text)


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
