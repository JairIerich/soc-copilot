from typing import Any, Protocol, cast

from soc_copilot.config import Settings


class Embedder(Protocol):
    identity: str

    def encode(self, texts: list[str]) -> list[list[float]]: ...

    def split(self, text: str, size: int, overlap: int) -> list[str]: ...


class LocalEmbedder:
    def __init__(self, settings: Settings) -> None:
        from sentence_transformers import SentenceTransformer

        self.identity = settings.embedding_model
        self.model: Any = SentenceTransformer(
            settings.embedding_model,
            device=settings.embedding_device,
            cache_folder=str(settings.embedding_cache_dir),
            local_files_only=settings.embedding_offline,
            trust_remote_code=False,
        )

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.encode(
            texts,
            batch_size=32,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return cast(list[list[float]], vectors.tolist())

    def split(self, text: str, size: int, overlap: int) -> list[str]:
        size = min(size, int(self.model.max_seq_length) - 2)
        if overlap >= size:
            raise ValueError("overlap excede janela efetiva do modelo")
        offsets = self.model.tokenizer(
            text,
            add_special_tokens=False,
            return_offsets_mapping=True,
            truncation=False,
            verbose=False,
        )["offset_mapping"]
        chunks = []
        start = 0
        while start < len(offsets):
            end = min(start + size, len(offsets))
            chunks.append(text[offsets[start][0] : offsets[end - 1][1]])
            if end == len(offsets):
                break
            start = end - overlap
        return chunks
