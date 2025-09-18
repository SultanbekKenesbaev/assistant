# backend/config.py
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Config:
    # --- RAG / Chroma (можно оставить, если где-то используешь) ---
    CHROMA_COLLECTION: str = os.getenv("CHROMA_COLLECTION", "knowledge_base")
    CHROMA_DIR: str = os.getenv("CHROMA_DIR", "./storage/chroma")
    DOCS_DIR: str = os.getenv("DOCS_DIR", "./data/docs")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
    TOP_K: int = int(os.getenv("TOP_K", "5"))

    # --- STT: по умолчанию Vosk (казахский) ---
    STT_ENGINE: str = os.getenv("STT_ENGINE", "vosk").lower()  # 'vosk' | 'whisper'
    VOSK_MODEL_PATH: str = os.getenv("VOSK_MODEL_PATH", "models/vosk-model-small-kz-0.15")

    # (оставлено для совместимости, если где-то ещё импортируется)
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "small")
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")
    WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

    # --- Аудио-роутер (новое) ---
    AUDIO_INDEX_PATH: str = os.getenv("AUDIO_INDEX_PATH", "data/answers/index.json")
    STATIC_AUDIO_DIR: str = os.getenv("STATIC_AUDIO_DIR", "static/audio")

    # --- Лёгкая LLM-классификация запроса в тег (локально через Ollama) ---
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama").lower()
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen:1.8b")

    # (если вдруг будешь использовать совместимые OpenAI эндпоинты)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # --- Прочее ---
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "./storage/outputs")
    FRONTEND_DIR: str = os.getenv("FRONTEND_DIR", "./frontend")

cfg = Config()
