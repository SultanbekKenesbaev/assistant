import json, os, re
from typing import Dict, List, Tuple, Optional
from .config import cfg
from .llm import classify_to_tag

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()

class AudioRouter:
    def __init__(self, index_path: str):
        if not os.path.isfile(index_path):
            raise RuntimeError(f"Audio index not found: {index_path}")
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.default_audio = data.get("default_audio", "static/audio/default_not_found.mp3")
        self.items = data.get("items", [])
        # предрасчёт нормализованных ключей
        for item in self.items:
            item["tag"] = item.get("tag") or os.path.splitext(os.path.basename(item.get("audio","")))[0]
            item["keys_norm"] = [_norm(k) for k in item.get("keys", [])]

    def _rule_match(self, q: str) -> Optional[Dict]:
        n = _norm(q)
        best_item, best_score = None, 0
        for it in self.items:
            score = 0
            for k in it["keys_norm"]:
                # простая эвристика: ключ как подстрока или пересечение слов
                if k and (k in n or any(w in n.split() for w in k.split())):
                    score += len(k)
            if score > best_score:
                best_item, best_score = it, score
        return best_item

    def _llm_match(self, q: str) -> Optional[Dict]:
        tags = [it["tag"] for it in self.items]
        chosen = classify_to_tag(q, tags)
        if not chosen or chosen == "NONE":
            return None
        for it in self.items:
            if it["tag"] == chosen:
                return it
        return None

    def find(self, query_text: str) -> Tuple[str, str, str]:
        """
        Возвращает (audio_url, tag, matched_by), where matched_by in {"rules","llm","default"}.
        """
        it = self._rule_match(query_text)
        if it:
            return it["audio"], it["tag"], "rules"
        it = self._llm_match(query_text)
        if it:
            return it["audio"], it["tag"], "llm"
        return self.default_audio, "default", "default"

def create_audio_router():
    return AudioRouter(cfg.AUDIO_INDEX_PATH)
