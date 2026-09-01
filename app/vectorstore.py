from __future__ import annotations

import hashlib
from dataclasses import dataclass

from sklearn.feature_extraction.text import HashingVectorizer

from .config import QDRANT_COLLECTION, QDRANT_URL, VECTOR_BACKEND
from .retrieval import LocalRetriever

@dataclass
class VectorHit:
    score: float
    source: str
    locator: str
    text: str

class SearchBackend:
    def __init__(self, chunks):
        self.chunks=chunks
        self.local=LocalRetriever(chunks)
        self.backend="local"
        self.qdrant=None
        self.vectorizer=HashingVectorizer(n_features=384, alternate_sign=False, norm="l2", analyzer="char_wb", ngram_range=(3,5))
        if VECTOR_BACKEND == "qdrant":
            try:
                from qdrant_client import QdrantClient
                from qdrant_client.models import Distance, VectorParams, PointStruct
                self.qdrant=QdrantClient(url=QDRANT_URL, timeout=5)
                try:
                    self.qdrant.get_collection(QDRANT_COLLECTION)
                except Exception:
                    self.qdrant.create_collection(QDRANT_COLLECTION, vectors_config=VectorParams(size=384, distance=Distance.COSINE))
                points=[]
                for ch in chunks:
                    vec=self.vectorizer.transform([ch.text]).toarray()[0].astype(float).tolist()
                    key=f"{ch.source}|{ch.locator}|{ch.text[:80]}"
                    pid=int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], 'big') & ((1<<63)-1)
                    points.append(PointStruct(id=pid, vector=vec, payload={"source":ch.source,"locator":ch.locator,"text":ch.text[:8000]}))
                if points:
                    self.qdrant.upsert(collection_name=QDRANT_COLLECTION, points=points, wait=True)
                self.backend="qdrant"
            except Exception:
                self.qdrant=None; self.backend="local"

    def search(self, query: str, top_k: int=8) -> list[VectorHit]:
        if self.qdrant is not None:
            vec=self.vectorizer.transform([query]).toarray()[0].astype(float).tolist()
            try:
                hits=self.qdrant.query_points(collection_name=QDRANT_COLLECTION, query=vec, limit=top_k, with_payload=True).points
                return [VectorHit(float(h.score), str((h.payload or {}).get("source","")), str((h.payload or {}).get("locator","")), str((h.payload or {}).get("text",""))) for h in hits]
            except Exception:
                pass
        return [VectorHit(h.score,h.chunk.source,h.chunk.locator,h.chunk.text) for h in self.local.search(query, top_k=top_k)]
