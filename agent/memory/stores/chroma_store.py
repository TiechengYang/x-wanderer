import chromadb
from chromadb.config import Settings as ChromaSettings
from pathlib import Path
from typing import List, Optional, Dict, Any


class ChromaMemoryStore:
    def __init__(self, persist_dir: str = "data/chroma"):
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(allow_reset=True, anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name="wanderer_semantic_memory",
            metadata={"hnsw:space": "cosine"}
        )

    def add(self, id: str, content: str, metadata: Dict[str, Any] = None):
        self.collection.add(
            documents=[content],
            ids=[id],
            metadatas=[metadata or {}]
        )

    def search(self, query: str, n_results: int = 8, filter_metadata: Dict[str, Any] = None):
        return self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=filter_metadata
        )
