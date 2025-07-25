#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path

# 0) Ensure ffmpeg exe is on PATH for both whisper and moviepy
FF_BIN = r"C:\ffmpeg\bin"
os.environ["PATH"] = FF_BIN + os.pathsep + os.environ.get("PATH", "")
os.environ['IMAGEIO_FFMPEG_EXE'] = os.path.join(FF_BIN, "ffmpeg.exe")

import whisper
import whisperx
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip

# File paths
IN_VIDEO   = Path("in.mp4")
AUDIO_WAV  = Path("in.wav")
OUT_VIDEO  = Path("out_with_subs.mp4")

# 1) Extract audio
subprocess.run([
    os.environ['IMAGEIO_FFMPEG_EXE'], "-y", "-i", str(IN_VIDEO),
    "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
    str(AUDIO_WAV)
], check=True)

# 2) Transcription and word-level alignment
w_model = whisper.load_model("small")
result  = w_model.transcribe(str(AUDIO_WAV), language="pl")
device  = "cpu"
align_model, metadata = whisperx.load_align_model(language_code="pl", device=device)
aligned = whisperx.align(result["segments"], align_model, metadata, str(AUDIO_WAV), device)
words   = aligned["word_segments"]

# 3) Load video
video = VideoFileClip(str(IN_VIDEO))
clips = [video]

# 4) Create animated text clips for each word
for w in words:
    txt = w['word'].strip()
    if not txt:
        continue
    start, end = w['start'], w['end']

    # create base TextClip
    txt_clip = TextClip(
        txt,
        fontsize=64,
        font='Roboto',
        color='white',
        method='caption',
        size=(int(video.w*0.8), None)
    )
    # add semi-transparent background box
    txt_clip = txt_clip.on_color(
        size=(txt_clip.w+20, txt_clip.h+10),
        color=(0, 0, 0),
        col_opacity=0.6
    )
    # set timing, position, and animations
    txt_clip = (
        txt_clip
        .set_start(start)
        .set_end(end)
        .set_position(('center', video.h - 200))
        .fadein(0.2)
        .fadeout(0.2)
    )

    clips.append(txt_clip)

# 5) Composite and write
final = CompositeVideoClip(clips)
final.write_videofile(
    str(OUT_VIDEO),
    codec='libx264',
    audio_codec='aac'
)
