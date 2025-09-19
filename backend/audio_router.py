# backend/audio_router.py
import json, os, re
from typing import Dict, List, Tuple, Optional
from .config import cfg

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()

class AudioRouter:
    """
    Ищет подходящий аудио-ответ по простым правилам:
    - точное вхождение нормализованных ключей (подстрока)
    - пересечение слов (очень простая эвристика)
    - если не нашли — отдаём default_audio
    """
    def __init__(self, index_path: str):
        if not os.path.isfile(index_path):
            raise RuntimeError(f"Audio index not found: {index_path}")
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # поддерживаем 2 схемы:
        #  A) {"default_audio": "...", "items":[{ "audio":"...", "keys":[...], "tag":"..." }] }
        #  B) [ { "id":"...", "audio":"...", "keys":[...], "screen_text":"" }, ... , {"id":"fallback", ...} ]
        if isinstance(data, dict) and "items" in data:
            self.default_audio = data.get("default_audio", "static/audio/fallback.mp3")
            raw_items = data.get("items", [])
        elif isinstance(data, list):
            fb = next((x for x in data if x.get("id") == "fallback"), None)
            self.default_audio = (fb or {}).get("audio", "static/audio/fallback.mp3")
            raw_items = data
        else:
            raise RuntimeError("Invalid index.json format")

        self.items: List[Dict] = []
        for it in raw_items:
            audio = it.get("audio")
            keys = it.get("keys") or []
            if not audio or not keys:
                continue
            tag = it.get("tag") or it.get("id") or os.path.splitext(os.path.basename(audio))[0]
            self.items.append({
                "audio": audio,
                "tag": tag,
                "keys_norm": [_norm(k) for k in keys if isinstance(k, str)]
            })

    def _rule_match(self, q: str) -> Optional[Dict]:
        n = _norm(q)
        if not n:
            return None
        best_item, best_score = None, 0
        n_words = set(n.split())

        for it in self.items:
            score = 0
            for k in it["keys_norm"]:
                if not k:
                    continue
                # 1) подстрока
                if k in n:
                    score += 5 + len(k)
                # 2) пересечение слов
                k_words = set(k.split())
                inter = len(n_words & k_words)
                if inter:
                    score += 3 * inter + (1 if len(k_words) == inter else 0)
            if score > best_score:
                best_item, best_score = it, score
        return best_item

    def find(self, query_text: str) -> Tuple[str, str, str]:
        """
        Возвращает (audio_url, tag, matched_by), где matched_by ∈ {"rules","default"}.
        """
        it = self._rule_match(query_text)
        if it:
            return it["audio"], it["tag"], "rules"
        return self.default_audio, "default", "default"

def create_audio_router():
    return AudioRouter(cfg.AUDIO_INDEX_PATH)
