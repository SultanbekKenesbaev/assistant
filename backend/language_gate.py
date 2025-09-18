from .utils import is_mostly_karakalpak
from .llm import paraphrase_to_kaa

def enforce_kaa(text: str) -> str:
    try:
        if is_mostly_karakalpak(text, threshold=0.7):
            return text
        return paraphrase_to_kaa(text)
    except Exception:
        # если что-то пошло не так — лучше вернуть как есть, чем 500
        return text
