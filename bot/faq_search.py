"""
Same embedding + cosine similarity pattern as your rag_pipeline.py, applied
to the FAQ sheet. This is intentionally a separate, small in-memory index
rather than reusing the generic VectorStore class — the FAQ table is small
(dozens of rows, not thousands), so a fresh embed-on-startup is simpler
than persisting an index file. Don't over-engineer this part.
"""

import numpy as np
from google import genai
from google.genai import types
from bot.data_store import load_faqs

EMBED_MODEL = "gemini-embedding-001"

_client = genai.Client()
_faq_questions: list[str] = []
_faq_answers: list[str] = []
_faq_embeddings: np.ndarray | None = None


def build_faq_index():
    """Call once at startup. Embeds every FAQ question."""
    global _faq_questions, _faq_answers, _faq_embeddings
    faqs = load_faqs()
    _faq_questions = faqs["Question"].tolist()
    _faq_answers = faqs["Answer"].tolist()

    result = _client.models.embed_content(
        model=EMBED_MODEL,
        contents=_faq_questions,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
    )
    vecs = np.array([e.values for e in result.embeddings], dtype=np.float32)
    _faq_embeddings = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)


def search_faq(query: str, top_k: int = 2, min_score: float = 0.55) -> list[dict]:
    """
    Returns up to top_k FAQ entries whose question is semantically closest
    to the query, filtered by a minimum similarity score so unrelated
    questions don't return a false match.
    """
    if _faq_embeddings is None:
        build_faq_index()

    q_result = _client.models.embed_content(
        model=EMBED_MODEL,
        contents=query,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    q = np.array(q_result.embeddings[0].values, dtype=np.float32)
    q = q / np.linalg.norm(q)

    scores = _faq_embeddings @ q
    top_idx = np.argsort(-scores)[:top_k]

    return [
        {"question": _faq_questions[i], "answer": _faq_answers[i], "score": float(scores[i])}
        for i in top_idx if scores[i] >= min_score
    ]
