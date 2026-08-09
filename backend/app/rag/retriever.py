from __future__ import annotations

import re

from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session

from app.models import Runbook


def _tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9_]+", text.lower()) if len(t) > 1]


class RunbookRetriever:
    """Lightweight BM25 retriever over ops runbooks (no GPU / embedding API required)."""

    def __init__(self, runbooks: list[Runbook]):
        self.runbooks = runbooks
        corpus = [_tokenize(f"{rb.title} {rb.service} {rb.tags} {rb.content}") for rb in runbooks]
        self.bm25 = BM25Okapi(corpus) if corpus else None

    @classmethod
    def from_db(cls, db: Session) -> "RunbookRetriever":
        return cls(db.query(Runbook).all())

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        if not self.runbooks or not self.bm25:
            return []
        scores = self.bm25.get_scores(_tokenize(query))
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
        results = []
        for idx, score in ranked:
            if score <= 0:
                continue
            rb = self.runbooks[idx]
            results.append(
                {
                    "slug": rb.slug,
                    "title": rb.title,
                    "service": rb.service,
                    "score": float(score),
                    "excerpt": rb.content[:700],
                    "tags": rb.tags,
                }
            )
        return results
