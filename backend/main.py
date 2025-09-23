from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

import os
import json
import wave
import tempfile
import subprocess
from pathlib import Path

# если cfg и audio_router у тебя есть — оставляем
from .config import cfg  # можно не использовать, но пусть будет для совместимости
from .audio_router import create_audio_router

# ---- Настройки Vosk / аудио ----
os.environ.setdefault("VOSK_LOG_LEVEL", "0")  # тише логов Vosk

VOSK_MODEL_PATH = Path(os.getenv("VOSK_MODEL_PATH", "models/vosk-model-small-kz-0.15")).resolve()
VOSK_SAMPLE_RATE = int(os.getenv("VOSK_SAMPLE_RATE", "16000"))

# опционально: список доменных слов через запятую для подсказки распознавателю
# пример: VOSK_PHRASES="Нүкіс,Хорезм,район,ассистент"
VOSK_PHRASES = [p.strip() for p in os.getenv("VOSK_PHRASES", "").split(",") if p.strip()]

# опционально включить нормализацию громкости (может помочь со слабым микрофоном)
ENABLE_LOUDNORM = os.getenv("FFMPEG_LOUDNORM", "0") == "1"


# ---- Класс STT на базе Vosk ----
try:
    from vosk import Model, KaldiRecognizer
except Exception as e:
    raise RuntimeError(
        "Не удалось импортировать vosk. Убедись, что в requirements.txt есть 'vosk' "
        "и контейнер пересобран."
    ) from e


class VoskSTT:
    def __init__(self, model_path: Path, sample_rate: int = 16000, phrases: list[str] | None = None):
        if not model_path.exists():
            raise RuntimeError(f"Vosk модель не найдена: {model_path}")
        self.model = Model(str(model_path))
        self.sample_rate = sample_rate
        self.phrases = phrases or []

    def _make_recognizer(self, rate: int):
        # если есть подсказки — используем грамматику
        if self.phrases:
            grammar = json.dumps(self.phrases, ensure_ascii=False)
            rec = KaldiRecognizer(self.model, rate, grammar)
        else:
            rec = KaldiRecognizer(self.model, rate)
        rec.SetWords(True)
        return rec

    def transcribe_wav(self, wav_path: str) -> dict:
        # ожидаем WAV: PCM16 mono 16k — мы это гарантируем ниже через ffmpeg
        with wave.open(wav_path, "rb") as wf:
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != self.sample_rate:
                raise RuntimeError("Неверный формат WAV для Vosk (ожидается PCM16 mono 16k).")

            rec = self._make_recognizer(wf.getframerate())

            while True:
                data = wf.readframes(4000)
                if not data:
                    break
                rec.AcceptWaveform(data)

            final = json.loads(rec.FinalResult())
            text = (final.get("text") or "").strip()
            return {"text": text, "raw": final}


# ---- FastAPI и шаблоны ----
app = FastAPI()
templates = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"])
)

# Глобальные singletons
STT: VoskSTT | None = None
AUDIO = None


@app.on_event("startup")
def _startup():
    global STT, AUDIO
    STT = VoskSTT(VOSK_MODEL_PATH, sample_rate=VOSK_SAMPLE_RATE, phrases=VOSK_PHRASES)
    AUDIO = create_audio_router()


@app.get("/", response_class=HTMLResponse)
def index():
    tpl = templates.get_template("index.html")
    return tpl.render()


app.mount("/static", StaticFiles(directory="static"), name="static")


# ---- Утилита конвертации аудио в WAV PCM16 mono 16k ----
def _ensure_wav(in_path: str) -> str:
    """
    Приводим любой входной формат (webm/ogg/mp3/m4a/wav и т.п.) к WAV PCM16 mono 16k.
    Это критично для качества Vosk.
    """
    out_path = in_path + ".wav"
    cmd = [
        "ffmpeg", "-y",
        "-i", in_path,
        "-ac", "1",
        "-ar", str(VOSK_SAMPLE_RATE),
        "-acodec", "pcm_s16le",
    ]
    if ENABLE_LOUDNORM:
        # нормализация громкости (может занять немного больше времени)
        cmd.extend(["-af", "loudnorm=I=-23:TP=-2:LRA=11"])

    cmd.append(out_path)

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err_tail = (proc.stderr or "").splitlines()[-15:]
        raise HTTPException(status_code=400, detail="ffmpeg failed:\n" + "\n".join(err_tail))
    return out_path


# ---- STT endpoint: принимаем единый файл (не фрагменты) ----
@app.post("/api/transcribe")
async def api_transcribe(file: UploadFile = File(...)):
    if STT is None:
        raise HTTPException(status_code=503, detail="STT сервис не инициализирован")

    suffix = os.path.splitext(file.filename or ".webm")[-1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="Пустой файл")
        tmp.write(data)
        tmp.flush()
        raw_path = tmp.name

    wav_path = None
    try:
        wav_path = _ensure_wav(raw_path)
        result = STT.transcribe_wav(wav_path)
        # чтобы не ломать фронт, возвращаем только text (raw можно включить при отладке)
        return {"text": result["text"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT error: {e}")
    finally:
        for p in (raw_path, wav_path):
            if p:
                try:
                    os.remove(p)
                except Exception:
                    pass


# ---- Основной: текст → находим и отдаём URL аудиофайла ----
@app.post("/api/ask-text")
async def api_ask_text(req: Request):
    body = await req.json()
    user_text = (body.get("text") or "").strip()
    if not user_text:
        return JSONResponse({"error": "empty text"}, status_code=400)

    # убираем wake-word "Хурлиман/Khurliman/Hurliman"
    low = user_text.lower()
    for w in ("хурлиман", "hurli", "hurliman", "khurliman", "qurliman"):
        if low.startswith(w + " "):
            user_text = user_text[len(w) + 1:].strip()
            break

    audio_rel, tag, matched_by = AUDIO.find(user_text)

    # audio_rel лежит внутри /static/, фронт сможет воспроизвести
    audio_url = "/" + audio_rel.lstrip("/")

    return {
        "matched_tag": tag,
        "matched_by": matched_by,
        "audio_url": audio_url,
        "screen_text": f"{tag} ({matched_by})"
    }
