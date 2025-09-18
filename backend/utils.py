import os
import re
import subprocess
import uuid
from pathlib import Path

KAA_LATIN_CHARS = "A-Za-zÁáǴǵÍíŃńÓóÚúÝý"
KAA_CYR_CHARS = "А-Яа-яҚқҒғҢңӨөҮүЎўІі"

def ensure_dirs(*paths: str):
    for p in paths:
        Path(p).mkdir(parents=True, exist_ok=True)

def ffmpeg_to_wav(src_path: str, dst_path: str, rate: int = 16000):
    # webm/opus -> wav mono 16k
    cmd = [
        "ffmpeg", "-y", "-i", src_path,
        "-ac", "1", "-ar", str(rate),
        "-f", "wav", dst_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def unique_filename(ext: str) -> str:
    return f"{uuid.uuid4().hex}.{ext}"

def is_mostly_karakalpak(text: str, threshold: float = 0.7) -> bool:
    # Грубая эвристика: доля символов из KAA алфавитов
    if not text:
        return True
    allowed = re.findall(fr"[{KAA_LATIN_CHARS}{KAA_CYR_CHARS}\s\.,!?;:\-\(\)\"'0-9]", text)
    return (len(allowed) / max(len(text), 1)) >= threshold
