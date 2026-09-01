from __future__ import annotations

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .ingest import Chunk


@dataclass
class Hit:
    score: float
    chunk: Chunk


class LocalRetriever:
    """Small fully local lexical retriever.

    TF-IDF is intentionally used instead of a cloud embedding service so the demo
    works offline and confidential files never need to leave the machine.
    """

    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self.vectorizer: TfidfVectorizer | None = None
        self.matrix = None
        if chunks:
            self.vectorizer = TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(2, 5),
                min_df=1,
                max_features=70000,
                sublinear_tf=True,
            )
            self.matrix = self.vectorizer.fit_transform([c.text for c in chunks])

    def search(self, query: str, top_k: int = 8) -> list[Hit]:
        if not self.chunks or self.vectorizer is None or self.matrix is None:
            return []
        q = self.vectorizer.transform([query])
        scores = cosine_similarity(q, self.matrix).ravel()
        order = scores.argsort()[::-1][:top_k]
        return [Hit(float(scores[i]), self.chunks[i]) for i in order if scores[i] > 0]
