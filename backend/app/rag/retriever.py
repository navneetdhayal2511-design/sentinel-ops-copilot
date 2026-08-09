from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

import numpy as np
from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Runbook

EMBED_DIM = 256


def _tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9_]+", text.lower()) if len(t) > 1]


def _hash_embed(text: str, dim: int = EMBED_DIM) -> np.ndarray:
    """Deterministic bag-of-words hashing embedder (no API required)."""
    vec = np.zeros(dim, dtype=np.float32)
    tokens = _tokenize(text)
    if not tokens:
        return vec
    counts = Counter(tokens)
    for tok, count in counts.items():
        digest = hashlib.sha256(tok.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[idx] += sign * (1.0 + math.log(count))
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


class RunbookRetriever:
    """Hybrid retriever: BM25 + hashing embeddings (+ optional OpenAI embeddings)."""

    def __init__(self, runbooks: list[Runbook]):
        self.runbooks = runbooks
        self.corpus_text = [
            f"{rb.title} {rb.service} {rb.tags} {rb.content}" for rb in runbooks
        ]
        tokenized = [_tokenize(t) for t in self.corpus_text]
        self.bm25 = BM25Okapi(tokenized) if tokenized else None
        self.local_embeddings = [_hash_embed(t) for t in self.corpus_text]
        self.openai_embeddings: list[np.ndarray] | None = None
        if settings.openai_api_key and runbooks:
            self.openai_embeddings = self._openai_embed_batch(self.corpus_text)

    @classmethod
    def from_db(cls, db: Session) -> "RunbookRetriever":
        return cls(db.query(Runbook).all())

    def _openai_embed_batch(self, texts: list[str]) -> list[np.ndarray] | None:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key)
            resp = client.embeddings.create(
                model=settings.embedding_model,
                input=[t[:6000] for t in texts],
            )
            out = []
            for item in resp.data:
                v = np.array(item.embedding, dtype=np.float32)
                n = np.linalg.norm(v)
                out.append(v / n if n else v)
            return out
        except Exception:
            return None

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        if not self.runbooks:
            return []

        n = len(self.runbooks)
        bm25_scores = (
            np.array(self.bm25.get_scores(_tokenize(query)), dtype=np.float32)
            if self.bm25
            else np.zeros(n, dtype=np.float32)
        )
        if bm25_scores.max() > 0:
            bm25_norm = bm25_scores / bm25_scores.max()
        else:
            bm25_norm = bm25_scores

        q_local = _hash_embed(query)
        local_scores = np.array(
            [_cosine(q_local, emb) for emb in self.local_embeddings], dtype=np.float32
        )

        method = "hybrid-bm25+hash"
        dense_scores = local_scores
        if self.openai_embeddings is not None:
            q_oa = self._openai_embed_batch([query])
            if q_oa:
                dense_scores = np.array(
                    [_cosine(q_oa[0], emb) for emb in self.openai_embeddings],
                    dtype=np.float32,
                )
                method = "hybrid-bm25+openai"

        # Weighted fusion
        fused = 0.45 * bm25_norm + 0.55 * np.clip(dense_scores, 0, 1)
        ranked = sorted(enumerate(fused.tolist()), key=lambda x: x[1], reverse=True)[:top_k]

        results = []
        for idx, score in ranked:
            if score <= 0.01:
                continue
            rb = self.runbooks[idx]
            results.append(
                {
                    "slug": rb.slug,
                    "title": rb.title,
                    "service": rb.service,
                    "score": round(float(score), 4),
                    "bm25": round(float(bm25_norm[idx]), 4),
                    "dense": round(float(dense_scores[idx]), 4),
                    "excerpt": rb.content[:700],
                    "tags": rb.tags,
                    "method": method,
                    "citation": f"[{rb.slug}] {rb.title}",
                }
            )
        return results
