from typing import List, Tuple
import numpy as np

# Совместимость, если вдруг будет NumPy 2.0
if not hasattr(np, "float_"):
    np.float_ = np.float64
if not hasattr(np, "int_"):
    np.int_ = np.int64
if not hasattr(np, "uint"):
    np.uint = np.uint64

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from .config import cfg

class RAG:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=cfg.CHROMA_DIR,
            settings=Settings(allow_reset=False, anonymized_telemetry=False)
        )
        # ⚠️ Больше не "kb", а имя из конфига
        self.collection = self.client.get_or_create_collection(cfg.CHROMA_COLLECTION)
        self.embedder = SentenceTransformer(cfg.EMBEDDING_MODEL)

    def embed(self, texts: List[str]) -> List[List[float]]:
        return self.embedder.encode(texts, normalize_embeddings=True).tolist()

    def search(self, query: str, top_k: int = None) -> List[Tuple[str, str]]:
        top_k = top_k or cfg.TOP_K
        qv = self.embed([query])[0]
        res = self.collection.query(query_embeddings=[qv], n_results=top_k)
        docs = res.get("documents", [[]])[0]
        metadatas = res.get("metadatas", [[]])[0]
        return list(zip(docs, [m.get("source", "") if m else "" for m in metadatas]))

rag = RAG()
