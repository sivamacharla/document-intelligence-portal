"""Answer generation over retrieved context. Deterministic offline mock by
default (extractive-style synthesis from the retrieved chunks) so chat
works with zero setup; set LLM_PROVIDER=openai for a real generative model.
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


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+|(?<=•)\s+|(?<=●)\s+", text)
    return [p.strip(" •●-•") for p in parts if p.strip(" •●-•")]


def _keywords(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {w for w in words if len(w) > 2 and w not in _STOPWORDS}


def generate_answer(question: str, contexts: list[str]) -> str:
    if os.getenv("LLM_PROVIDER") == "openai":
        return _openai_answer(question, contexts)

    if not contexts:
        return "I couldn't find anything relevant to that in your uploaded documents."

    return _extractive_answer(question, contexts)


def _extractive_answer(question: str, contexts: list[str]) -> str:
    """Picks the sentences most relevant to the question instead of always
    dumping the same leading chunk of text, so different questions against
    the same document actually produce different answers.
    """
    query_terms = _keywords(question)

    sentences: list[str] = []
    seen: set[str] = set()
    for ctx in contexts:
        for s in _split_sentences(ctx):
            if s not in seen:
                seen.add(s)
                sentences.append(s)

    if not sentences:
        return "I couldn't find anything relevant to that in your uploaded documents."

    if query_terms:
        scored = [(len(_keywords(s) & query_terms), s) for s in sentences]
        best = [s for score, s in scored if score > 0]
    else:
        best = []

    if best:
        # keep original document order among the matched sentences rather
        # than sorting purely by score, so the answer still reads coherently
        matched_set = set(best)
        ordered = [s for s in sentences if s in matched_set][:4]
        answer = " ".join(ordered)
    else:
        # question is too generic/vague to match specific sentences (e.g.
        # "tell me about yourself") -- fall back to a short lead summary
        answer = " ".join(sentences[:3])

    answer = answer[:500].rstrip()
    return f"Based on your documents: {answer}"


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
