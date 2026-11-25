import hashlib
import logging
from pathlib import Path

from soc_copilot.config import Settings
from soc_copilot.embeddings.local import Embedder
from soc_copilot.ingest.parser import parse_file
from soc_copilot.models import Chunk, Event
from soc_copilot.retrieval.store import ChromaStore

logger = logging.getLogger(__name__)


def chunk_events(events: list[Event], embedder: Embedder, settings: Settings) -> list[Chunk]:
    chunks = []
    for event in events:
        for index, text in enumerate(
            embedder.split(event.text, settings.chunk_tokens, settings.chunk_overlap)
        ):
            identity = f"{event.source}:{event.record}:{index}:{text}"
            chunk_id = hashlib.sha256(identity.encode()).hexdigest()
            chunks.append(
                Chunk(**{**event.model_dump(), "text": text}, chunk_id=chunk_id, chunk_index=index)
            )
    return chunks


def ingest_file(
    path: Path, settings: Settings, embedder: Embedder, store: ChromaStore
) -> dict[str, int | str]:
    events = parse_file(path, settings.data_dir)
    chunks = chunk_events(events, embedder, settings)
    vectors = embedder.encode([chunk.text for chunk in chunks])
    source = path.resolve().relative_to(settings.data_dir.resolve()).as_posix()
    # Parse e embeddings terminam antes de modificar a coleção.
    store.sync_source(source, chunks, vectors)
    logger.info("ingest_completed events=%d chunks=%d", len(events), len(chunks))
    return {"source": source, "events": len(events), "chunks": len(chunks)}
