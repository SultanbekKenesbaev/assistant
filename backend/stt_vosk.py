# stt_vosk.py
import json
import os
import wave
import subprocess
import tempfile
from pathlib import Path

from vosk import Model, KaldiRecognizer

# Путь к модели: по умолчанию берем из env, иначе из ./models/vosk-model-small-kz-0.15
VOSK_MODEL_PATH = Path(os.getenv("VOSK_MODEL_PATH", "models/vosk-model-small-kz-0.15")).resolve()
SAMPLE_RATE = int(os.getenv("VOSK_SAMPLE_RATE", "16000"))

# Глобальная загрузка модели (один раз при старте процесса)
_vosk_model = None

def get_model() -> Model:
    global _vosk_model
    if _vosk_model is None:
        if not VOSK_MODEL_PATH.exists():
            raise RuntimeError(f"Vosk model not found at: {VOSK_MODEL_PATH}")
        _vosk_model = Model(str(VOSK_MODEL_PATH))
    return _vosk_model

def _ffmpeg_convert_to_wav_pcm16_mono_16k(src_path: Path, dst_path: Path) -> None:
    """
    Жёстко приводим любой входной звук к:
    - PCM s16le
    - mono
    - 16 kHz
    Это сильно влияет на качество для Vosk.
    """
    cmd = [
        "ffmpeg", "-y", "-i", str(src_path),
        "-ac", "1",
        "-ar", str(SAMPLE_RATE),
        "-f", "wav",
        "-acodec", "pcm_s16le",
        str(dst_path),
    ]
    # глушим болтовню ffmpeg, но ловим ошибки
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def transcribe_bytes(audio_bytes: bytes) -> dict:
    """
    Принимает произвольный аудиофайл (webm/ogg/wav/mp3 и т.д.) в виде bytes,
    конвертирует его через ffmpeg и кормит в Vosk.
    Возвращает словарь: {"text": "...", "result": [...raw json...] }
    """
    model = get_model()

    with tempfile.TemporaryDirectory() as td:
        tmp_in = Path(td) / "in.any"
        tmp_wav = Path(td) / "out.wav"

        tmp_in.write_bytes(audio_bytes)
        _ffmpeg_convert_to_wav_pcm16_mono_16k(tmp_in, tmp_wav)

        with wave.open(str(tmp_wav), "rb") as wf:
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != SAMPLE_RATE:
                # на всякий случай, но обычно мы уже привели всё как надо
                raise RuntimeError("Converted WAV has unexpected format.")

            rec = KaldiRecognizer(model, wf.getframerate())
            rec.SetWords(True)  # хотим слова с таймкодами

            # Можно задать "грамматику" для доменных слов, чтобы повысить точность
            # Пример:
            # phrases = ["Нұқыс", "район", "ассистент", "Қазақстан", "Назарбаев", "интернет", "разработчик"]
            # rec = KaldiRecognizer(model, wf.getframerate(), json.dumps(phrases, ensure_ascii=False))

            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                rec.AcceptWaveform(data)

            # Важно: соберем финальный результат
            final = json.loads(rec.FinalResult())

            # у Vosk финальное поле — "text", без пунктуации
            text = final.get("text", "").strip()
            return {
                "text": text,
                "result": final,  # тут полные данные: слова, таймкоды и т.д.
            }
