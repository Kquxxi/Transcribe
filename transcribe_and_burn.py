#!/usr/bin/env python3
import os
import subprocess
import random
import re
from pathlib import Path

import whisper
import pysubs2

# ------------------------------------------------------------------
# Ensure FFmpeg is found by prepending its bin directory to PATH
dl = r"C:\ffmpeg\bin"
os.environ["PATH"] = dl + os.pathsep + os.environ.get("PATH", "")
FFMPEG = Path(dl) / "ffmpeg.exe"
# ------------------------------------------------------------------

# Project paths
dir_proj = Path(__file__).parent
IN_VIDEO  = dir_proj / "in.mp4"
WAV_FILE  = dir_proj / "in.wav"
ASS_FILE  = dir_proj / "out_karaoke_tiktok.ass"
OUT_VIDEO = dir_proj / "out_with_karaoke_tiktok.mp4"

# List of Polish curse words to censor
CURSE_WORDS = [
    "kurwa", "chuj", "pizda", "skurwysyn",
    "jebany", "pedał", "jebać"
]

def censor_text(text: str) -> str:
    """
    Replace curse words in the text with asterisks.
    """
    pattern = re.compile(r"\b(" + "|".join(CURSE_WORDS) + r")\b", re.IGNORECASE)
    return pattern.sub(lambda m: "*" * len(m.group()), text)

# TikTok-friendly neon colors (BBGGRR format)
TIKTOK_COLORS = [
    "&H00FF00FF&",  # magenta
    "&H00FFFF00&",  # cyan
    "&H0000FFFF&",  # yellow
    "&H0080FF00&",  # green
    "&H00FF8000&"   # orange
]

# 1) Extract audio
def extract_audio():
    subprocess.run([
        str(FFMPEG), "-y", "-i", str(IN_VIDEO),
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", str(WAV_FILE)
    ], check=True)
    print("[OK] Audio extracted to WAV.")

# 2) Transcribe with Whisper
def transcribe_segments():
    model = whisper.load_model("small")
    result = model.transcribe(str(WAV_FILE), language="pl")
    print("[OK] Whisper transcription done.")
    return result["segments"]

# 3) Generate karaoke-style ASS with center positioning, nicer font, color and censorship
def generate_karaoke_ass(segments):
    subs = pysubs2.SSAFile()
    subs.info.update({"ScriptType": "v4.00+", "PlayResX": 1920, "PlayResY": 1080})

    # Define base centered style with a nicer font
    style = pysubs2.SSAStyle()
    style.name         = "Karaoke"
    style.fontname     = "Bebas Neue"
    style.fontsize     = 60
    style.primarycolor = "&H00FFFFFF&"
    style.backcolor    = "&H80000000&"
    style.outline      = 2
    style.shadow       = 1
    style.alignment    = 5  # middle-center
    style.margin_v     = 0
    subs.styles[style.name] = style

    # Center coordinates
    center_x = subs.info["PlayResX"] // 2
    center_y = subs.info["PlayResY"] // 2

    # Build events
    for seg in segments:
        text = seg.get("text", "").strip()
        text = censor_text(text)
        if not text:
            continue
        words = text.split()
        start_ms = int(seg["start"] * 1000)
        end_ms   = int(seg["end"] * 1000)
        total_ms = end_ms - start_ms
        total_chars = sum(len(w) for w in words)

        # Choose a random neon color for this segment
        color = random.choice(TIKTOK_COLORS)
        karaoke_text = f"{{\\pos({center_x},{center_y})\\c{color}}}"

        # Assign durations weighted by character length
        for w in words:
            dur_cs = max(int((len(w) / total_chars) * total_ms / 10), 1)
            karaoke_text += f"{{\\k{dur_cs}}}{w} "

        subs.append(pysubs2.SSAEvent(
            start=start_ms,
            end=end_ms,
            style=style.name,
            text=karaoke_text.strip()
        ))

    subs.save(str(ASS_FILE))
    print(f"[OK] Saved TikTok-style karaoke ASS with {len(subs.events)} lines.")

# 4) Burn-in ASS to video
def burn_karaoke():
    subprocess.run([
        str(FFMPEG), "-y", "-i", str(IN_VIDEO),
        "-vf", f"ass={ASS_FILE.name}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "copy", str(OUT_VIDEO)
    ], check=True, cwd=str(dir_proj))
    print(f"✅ Done! Output with karaoke: {OUT_VIDEO}")

if __name__ == "__main__":
    extract_audio()
    segments = transcribe_segments()
    generate_karaoke_ass(segments)
    burn_karaoke()