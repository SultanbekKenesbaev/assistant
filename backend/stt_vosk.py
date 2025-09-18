import json
import subprocess
import tempfile
import os
from vosk import Model, KaldiRecognizer
from .config import cfg

class VoskSTT:
    def __init__(self, model_path: str):
        if not os.path.isdir(model_path):
            raise RuntimeError(f"VOSK model not found at {model_path}")
        self.model = Model(model_path)

    def _to_wav16k_mono(self, in_path: str) -> str:
        out_path = in_path + ".wav"
        proc = subprocess.run(
            ["ffmpeg", "-y", "-i", in_path, "-ac", "1", "-ar", "16000", out_path],
            capture_output=True, text=True
        )
        if proc.returncode != 0:
            err = (proc.stderr or "").splitlines()[-10:]
            raise RuntimeError("ffmpeg failed: " + "\n".join(err))
        return out_path

    def transcribe(self, audio_path: str) -> str:
        wav = self._to_wav16k_mono(audio_path)
        try:
            import wave
            wf = wave.open(wav, "rb")
            if wf.getnchannels() != 1 or wf.getframerate() != 16000:
                wf.close()
                raise RuntimeError("WAV must be mono 16k")
            rec = KaldiRecognizer(self.model, wf.getframerate())
            rec.SetWords(False)
            text_chunks = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    res = json.loads(rec.Result())
                    if "text" in res and res["text"]:
                        text_chunks.append(res["text"])
            res = json.loads(rec.FinalResult())
            if "text" in res and res["text"]:
                text_chunks.append(res["text"])
            wf.close()
            out = " ".join(t for t in text_chunks if t).strip()
            return out
        finally:
            try: os.remove(wav)
            except Exception: pass

def create_stt():
    return VoskSTT(cfg.VOSK_MODEL_PATH)
