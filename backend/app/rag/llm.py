"""Answer generation over retrieved context. Deterministic offline mock by
default (extractive-style synthesis from the retrieved chunks) so chat
works with zero setup; set LLM_PROVIDER=openai for a real generative model.
"""
from __future__ import annotations

import os


def generate_answer(question: str, contexts: list[str]) -> str:
    if os.getenv("LLM_PROVIDER") == "openai":
        return _openai_answer(question, contexts)

    if not contexts:
        return "I couldn't find anything relevant to that in your uploaded documents."

    joined = " ".join(contexts)[:600]
    return f"Based on your documents: {joined}..."


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
