#!/usr/bin/env python3
import os
import subprocess
import random
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

# TikTok-style color palette (hex in ASS as &HBBGGRR&)
TIKTOK_COLORS = [
    "&H00FF00FF&",  # neon magenta
    "&H00FFFF00&",  # neon cyan
    "&H0000FFFF&",  # neon yellow
    "&H0080FF00&",  # bright green
    "&H00FF8000&"   # bright orange
]

# 1) Extract audio to WAV (16 kHz mono)
def extract_audio():
    subprocess.run([
        str(FFMPEG), "-y", "-i", str(IN_VIDEO),
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", str(WAV_FILE)
    ], check=True)
    print("[OK] Audio extracted to WAV.")

# 2) Transcribe with Whisper to get segments (timing)
def transcribe_segments():
    model = whisper.load_model("small")
    result = model.transcribe(str(WAV_FILE), language="pl")
    print("[OK] Whisper transcription done.")
    return result["segments"]

# 3) Generate karaoke-style ASS by weighted word durations and colorful styles
def generate_karaoke_ass(segments):
    subs = pysubs2.SSAFile()
    subs.info.update({"ScriptType": "v4.00+", "PlayResX": 1920, "PlayResY": 1080})

    # Base style (centered)
    style = pysubs2.SSAStyle()
    style.name         = "Karaoke"
    style.fontname     = "Arial Black"
    style.fontsize     = 56
    style.primarycolor = "&H00FFFFFF&"  # default white
    style.backcolor    = "&H80000000&"  # semi-transparent black
    style.outline      = 2
    style.shadow       = 1
    style.alignment    = 5  # middle-center
    subs.styles[style.name] = style

    # Center coordinates
    center_x = subs.info["PlayResX"] // 2
    center_y = subs.info["PlayResY"] // 2

    for seg in segments:
        raw = seg.get("text", "").strip()
        if not raw:
            continue
        # Word-level info if available
        word_objs = seg.get("words")
        # Fallback to splitting text
        if not word_objs:
            words = raw.split()
        else:
            words = word_objs
        start_ms = int(seg.get("start", 0) * 1000)
        end_ms   = int(seg.get("end", seg.get("start", 0) + len(words)*0.5) * 1000)

        # Random TikTok color per segment
        color = random.choice(TIKTOK_COLORS)
        # Initial override: position & color
        karaoke_text = f"{{\pos({center_x},{center_y})\c{color}}}"

        # Build karaoke tags
        if word_objs:
            for w in word_objs:
                dur_cs = max(int((w['end'] - w['start']) * 100), 1)
                karaoke_text += f"{{\k{dur_cs}}}{w['word']} "
        else:
            # uniform durations based on char count
            total_ms = end_ms - start_ms
            dur_cs = max(int((total_ms / len(words)) / 10), 1)
            for w in words:
                karaoke_text += f"{{\k{dur_cs}}}{w} "

        event = pysubs2.SSAEvent(
            start=start_ms,
            end=end_ms,
            style=style.name,
            text=karaoke_text.strip()
        )
        subs.append(event)

    subs.save(str(ASS_FILE))
    print(f"[OK] Saved TikTok karaoke ASS with {len(subs.events)} lines.")

# 4) Burn-in ASS into video using FFmpeg (relative ASS name, set cwd)
def burn_karaoke():
    vf_filter = f"ass={ASS_FILE.name}"
    subprocess.run([
        str(FFMPEG), "-y", "-i", str(IN_VIDEO),
        "-vf", vf_filter,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "copy", str(OUT_VIDEO)
    ], check=True, cwd=str(dir_proj))
    print(f"✅ Done! Output with TikTok-style karaoke: {OUT_VIDEO}")

if __name__ == "__main__":
    extract_audio()
    segments = transcribe_segments()
    generate_karaoke_ass(segments)
    burn_karaoke()
