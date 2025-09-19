# backend/config.py (упрощённый вариант)
import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()

@dataclass(frozen=True)
class Config:
    STT_ENGINE: str = os.getenv("STT_ENGINE", "vosk").lower()
    VOSK_MODEL_PATH: str = os.getenv("VOSK_MODEL_PATH", "models/vosk-model-small-kz-0.15")

    AUDIO_INDEX_PATH: str = os.getenv("AUDIO_INDEX_PATH", "data/answers/index.json")
    STATIC_AUDIO_DIR: str = os.getenv("STATIC_AUDIO_DIR", "static/audio")

    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "./storage/outputs")
    FRONTEND_DIR: str = os.getenv("FRONTEND_DIR", "./frontend")

cfg = Config()
