"""Answer generation over retrieved context. Deterministic offline mock by
default (extractive-style synthesis from the retrieved chunks) so chat
works with zero setup; set LLM_PROVIDER=openai for a real generative model.

Returns (answer_text, cited_indices): cited_indices are positions into the
`contexts` list indicating which sources were actually used, in the order
their [1], [2]... markers appear in answer_text, so the caller can build a
sources list whose numbering matches the inline citations.
"""
from __future__ import annotations

import os
import re

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "have", "has", "had", "and", "or", "but", "of",
    "to", "in", "on", "for", "with", "about", "your", "you", "me", "my",
    "what", "how", "when", "where", "why", "who", "tell", "please", "can",
}


def _is_bare_heading(sentence: str) -> bool:
    """Filters out section headers like 'EXPERIENCE' or 'PROJECTS' that
    survive PDF/DOCX extraction as their own line -- they can keyword-match
    a question (e.g. "experience") without containing any actual answer.
    """
    words = sentence.split()
    return len(words) <= 3 and sentence == sentence.upper() and any(c.isalpha() for c in sentence)


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+|(?<=•)\s+|(?<=●)\s+", text)
    cleaned = [p.strip(" •●-•") for p in parts if p.strip(" •●-•")]
    return [s for s in cleaned if not _is_bare_heading(s)]


def _keywords(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {w for w in words if len(w) > 2 and w not in _STOPWORDS}


def generate_answer(question: str, contexts: list[str]) -> tuple[str, list[int]]:
    if os.getenv("LLM_PROVIDER") == "openai":
        return _openai_answer(question, contexts), []

    if not contexts:
        return "I couldn't find anything relevant to that in your uploaded documents.", []

    return _extractive_answer(question, contexts)


def _extractive_answer(question: str, contexts: list[str]) -> tuple[str, list[int]]:
    """Picks the sentences most relevant to the question instead of always
    dumping the same leading chunk of text, and tags each sentence with an
    inline [n] marker pointing at which retrieved chunk it came from.
    """
    query_terms = _keywords(question)

    # (sentence, source_index) pairs, deduped by sentence text
    entries: list[tuple[str, int]] = []
    seen: set[str] = set()
    for idx, ctx in enumerate(contexts):
        for s in _split_sentences(ctx):
            if s not in seen:
                seen.add(s)
                entries.append((s, idx))

    if not entries:
        return "I couldn't find anything relevant to that in your uploaded documents.", []

    if query_terms:
        scored = [(len(_keywords(s) & query_terms), s, idx) for s, idx in entries]
        matched = {s for score, s, idx in scored if score > 0}
        ordered = [(s, idx) for s, idx in entries if s in matched][:4]
    else:
        # question is too generic/vague to match specific sentences (e.g.
        # "tell me about yourself") -- fall back to a short lead summary
        ordered = entries[:3]

    # assign citation numbers in first-appearance order
    marker_for_idx: dict[int, int] = {}
    for _, idx in ordered:
        if idx not in marker_for_idx:
            marker_for_idx[idx] = len(marker_for_idx) + 1

    answer = " ".join(f"{s} [{marker_for_idx[idx]}]" for s, idx in ordered)
    answer = answer[:600].rstrip()

    cited_indices = sorted(marker_for_idx, key=marker_for_idx.get)
    return f"Based on your documents: {answer}", cited_indices


def _openai_answer(question: str, contexts: list[str]) -> str:
    from openai import OpenAI  # optional dependency

    client = OpenAI()
    context_block = "\n---\n".join(contexts)
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": "Answer only using the provided document context. If the answer isn't in the context, say so."},
            {"role": "user", "content": f"Context:\n{context_block}\n\nQuestion: {question}"},
        ],
    )
    return resp.choices[0].message.content or ""
