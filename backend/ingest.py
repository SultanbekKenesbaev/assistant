from __future__ import annotations
from pathlib import Path
from typing import List

# Устойчивый импорт cfg (работает и как модуль, и как скрипт)
try:
    from .config import cfg  # python -m backend.ingest
except ImportError:
    import os, sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # ../
    from backend.config import cfg  # python backend/ingest.py

import re
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader


def load_text_from_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in [".txt", ".md"]:
        return path.read_text(encoding="utf-8", errors="ignore")
    if ext == ".pdf":
        text = []
        reader = PdfReader(str(path))
        for page in reader.pages:
            t = page.extract_text() or ""
            text.append(t)
        return "\n".join(text)
    return ""


def chunk_text(text: str, max_len: int = 800, overlap: int = 100) -> List[str]:
    text = re.sub(r"\s+", " ", text).strip()
    chunks = []
    i = 0
    n = len(text)
    while i < n:
        end = min(i + max_len, n)
        chunk = text[i:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == n:
            break
        i = end - overlap
        if i < 0:
            i = 0
    return chunks


def main():
    # Отключаем анонимную телеметрию, чтобы не было "ClientStartEvent ..."
    client = chromadb.PersistentClient(
        path=cfg.CHROMA_DIR,
        settings=Settings(allow_reset=False, anonymized_telemetry=False),
    )
    coll_name = cfg.CHROMA_COLLECTION

    # Создаём/очищаем коллекцию
    try:
        coll = client.get_or_create_collection(coll_name)
        if coll.count() and coll.count() > 0:
            client.delete_collection(coll_name)
            coll = client.get_or_create_collection(coll_name)
    except Exception:
        # На случай гонок или старых версий API — просто пробуем пересоздать
        try:
            client.delete_collection(coll_name)
        except Exception:
            pass
        coll = client.get_or_create_collection(coll_name)

    embedder = SentenceTransformer(cfg.EMBEDDING_MODEL)

    docs_dir = Path(cfg.DOCS_DIR)
    docs, metas, ids = [], [], []

    for p in docs_dir.glob("**/*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in [".txt", ".md", ".pdf"]:
            continue
        raw = load_text_from_file(p)
        if not raw:
            continue
        for j, ch in enumerate(chunk_text(raw)):
            docs.append(ch)
            metas.append({"source": str(p)})
            ids.append(f"{p.name}-{j}")

    if not docs:
        print(f"No docs found in {cfg.DOCS_DIR}. Put .txt/.md/.pdf there.")
        return

    embs = embedder.encode(docs, normalize_embeddings=True).tolist()
    coll.add(documents=docs, metadatas=metas, ids=ids, embeddings=embs)
    print(f"Ingested {len(docs)} chunks from {cfg.DOCS_DIR} into '{coll_name}'")


if __name__ == "__main__":
    main()
