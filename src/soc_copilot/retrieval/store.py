from typing import Any

import chromadb
import numpy as np
from chromadb.config import Settings as ChromaSettings

from soc_copilot.config import Settings
from soc_copilot.models import Chunk


class ChromaStore:
    def __init__(self, settings: Settings, embedding_identity: str) -> None:
        self.client = chromadb.PersistentClient(
            path=str(settings.chroma_dir), settings=ChromaSettings(anonymized_telemetry=False)
        )
        signature = f"v1:{embedding_identity}:{settings.chunk_tokens}:{settings.chunk_overlap}"
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection,
            embedding_function=None,
            metadata={"hnsw:space": "cosine", "hnsw:num_threads": 1, "pipeline": signature},
        )
        if (self.collection.metadata or {}).get("pipeline") != signature:
            raise ValueError(
                "Coleção usa outro modelo/chunking; escolha CHROMA_COLLECTION diferente e reingira"
            )

    def count(self) -> int:
        return self.collection.count()

    def sync_source(self, source: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("quantidade de vetores difere de chunks")
        old = set(self.collection.get(where={"source": source}, include=[])["ids"])
        for start in range(0, len(chunks), 128):
            batch = chunks[start : start + 128]
            metadata: list[Any] = [c.model_dump(exclude={"text", "chunk_id"}) for c in batch]
            self.collection.upsert(
                ids=[c.chunk_id for c in batch],
                documents=[c.text for c in batch],
                metadatas=metadata,
                embeddings=np.asarray(vectors[start : start + 128], dtype=np.float32),
            )
        stale = sorted(old - {c.chunk_id for c in chunks})
        if stale:
            self.collection.delete(ids=stale)

    def all_chunks(self) -> list[Chunk]:
        result = self.collection.get(include=["documents", "metadatas"])
        return [
            Chunk.model_validate({"chunk_id": identity, "text": text, **meta})
            for identity, text, meta in zip(
                result["ids"], result["documents"] or [], result["metadatas"] or [], strict=True
            )
        ]

    def vector_search(self, vector: list[float], limit: int) -> list[tuple[str, float]]:
        if not self.count():
            return []
        result = self.collection.query(
            query_embeddings=np.asarray([vector], dtype=np.float32),
            n_results=min(limit, self.count()),
            include=["distances"],
        )
        distances = (result["distances"] or [[]])[0]
        return [
            (identity, 1.0 - float(distance))
            for identity, distance in zip(result["ids"][0], distances, strict=True)
        ]
