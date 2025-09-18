import os
import subprocess
from pathlib import Path
from .config import cfg
from .utils import unique_filename

def synthesize_tts(text: str, out_dir: str = None) -> str:
    out_dir = out_dir or cfg.OUTPUT_DIR
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    wav_cmd = [
        "espeak-ng",
        "-v", cfg.KAA_TTS_VOICE,
        "-s", str(cfg.TTS_WPM),
        "--stdout",
        text
    ]
    mp3_path = os.path.join(out_dir, unique_filename("mp3"))
    # espeak stdout -> ffmpeg to mp3
    ffmpeg_cmd = ["ffmpeg", "-y", "-i", "pipe:0", "-f", "mp3", mp3_path]
    p1 = subprocess.Popen(wav_cmd, stdout=subprocess.PIPE)
    p2 = subprocess.run(ffmpeg_cmd, stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return mp3_path
