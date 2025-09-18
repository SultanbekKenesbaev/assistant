from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os, tempfile, subprocess

from .config import cfg
from .stt_vosk import create_stt
from .audio_router import create_audio_router

app = FastAPI()
templates = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"])
)

# Глобальные singletons
STT = None
AUDIO = None

@app.on_event("startup")
def _startup():
    global STT, AUDIO
    STT = create_stt()
    AUDIO = create_audio_router()

@app.get("/", response_class=HTMLResponse)
def index():
    tpl = templates.get_template("index.html")
    return tpl.render()

app.mount("/static", StaticFiles(directory="static"), name="static")

# ---- STT endpoint (получаем цельный файл, не кусочки) ----

def _ensure_wav(in_path: str) -> str:
    out_path = in_path + ".wav"
    proc = subprocess.run(
        ["ffmpeg", "-y", "-i", in_path, "-ac", "1", "-ar", "16000", out_path],
        capture_output=True, text=True
    )
    if proc.returncode != 0:
        err = (proc.stderr or "").splitlines()[-10:]
        raise HTTPException(status_code=400, detail="ffmpeg failed:\n" + "\n".join(err))
    return out_path

@app.post("/api/transcribe")
async def api_transcribe(file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename or ".webm")[-1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        data = await file.read()
        tmp.write(data)
        tmp.flush()
        raw_path = tmp.name
    wav_path = None
    try:
        wav_path = _ensure_wav(raw_path)
        text = STT.transcribe(wav_path)
        return {"text": text}
    finally:
        try: os.remove(raw_path)
        except: pass
        if wav_path:
            try: os.remove(wav_path)
            except: pass

# ---- Основной: получаем текст → отдаём URL нужного аудио ----

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
            user_text = user_text[len(w)+1:].strip()
            break

    audio_rel, tag, matched_by = AUDIO.find(user_text)

    # audio_rel лежит внутри /static/, так что фронт сможет воспроизвести
    audio_url = "/" + audio_rel.lstrip("/")

    return {
        "matched_tag": tag,
        "matched_by": matched_by,
        "audio_url": audio_url,
        # можно добавить короткий текст для экрана, если хочешь
        "screen_text": f"{tag} ({matched_by})"
    }
