#!/usr/bin/env python3
import os
import subprocess
import random
import re
from pathlib import Path

import whisper
import pysubs2

# ------------------------------------------------------------------
# Upewnij się, że FFmpeg jest w ścieżce PATH
# Zmień tę ścieżkę, jeśli FFmpeg jest zainstalowany gdzie indziej
dl = r"C:\ffmpeg\bin"
if Path(dl).exists():
    os.environ["PATH"] = dl + os.pathsep + os.environ.get("PATH", "")
    FFMPEG = Path(dl) / "ffmpeg.exe"
else:
    # Jeśli nie ma w podanej ścieżce, spróbuj użyć ffmpeg z systemowej ścieżki PATH
    FFMPEG = "ffmpeg" 
# ------------------------------------------------------------------

# Ścieżki projektu
dir_proj = Path(__file__).parent
IN_VIDEO  = dir_proj / "in.mp4"
WAV_FILE  = dir_proj / "in.wav"
ASS_FILE  = dir_proj / "out_karaoke_tiktok.ass"
OUT_VIDEO = dir_proj / "out_with_karaoke_tiktok.mp4"

# Rozszerzona lista polskich wulgaryzmów do cenzury
CURSE_WORDS = [
    "kurwa", "kurwy", "kurw", "chuj", "chuje", "chujek", "chujnia",
    "pizda", "pizdy", "pizdzie", "skurwysyn", "skurwysyna", "skurwiel",
    "jebany", "jebac", "jebać", "jebią", "japierdole", "pierdol", "pierdolę",
    "ciota", "cipa", "cipie", "dupku", "dupa", "dupka", "dupy",
    "pedał", "pizdunska", "masturbuj", "suka", "szmata", "gówno", "gowno"
]

# Neonowe kolory w stylu TikToka w formacie &HBBGGRR&
TIKTOK_COLORS = [
    "&H00FF00FF&",  # magenta
    "&H00FFFF00&",  # cyan
    "&H0000FFFF&",  # yellow
    "&H0080FF00&",  # lime
    "&H00FF8000&"   # orange
]

# Rozszerzona lista emoji
EMOJIS = [
    "🔥","💥","✨","🎉","😎","🚀","💯","👀","🥳",
    "😂","😍","🤣","😁","🙌","👌","🤩","🌟","🎊"
]

# Funkcja pomocnicza: cenzurowanie tekstu
def censor_text(text: str) -> str:
    """Zamienia wulgaryzmy w tekście na gwiazdki."""
    pattern = re.compile(r"\b(" + "|".join(CURSE_WORDS) + r")\b", re.IGNORECASE)
    return pattern.sub(lambda m: "*" * len(m.group()), text)

# 1) Ekstrakcja audio do formatu WAV
def extract_audio():
    """Wyodrębnia ścieżkę audio z wideo i zapisuje jako plik WAV."""
    if not IN_VIDEO.exists():
        print(f"❌ Błąd: Plik wideo wejściowego nie został znaleziony w {IN_VIDEO}")
        return False
    print("🔊 Rozpoczynam ekstrakcję audio...")
    subprocess.run([
        str(FFMPEG), "-y", "-i", str(IN_VIDEO),
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", str(WAV_FILE)
    ], check=True, capture_output=True, text=True)
    print("[OK] Audio zostało wyodrębnione do pliku WAV.")
    return True

# 2) Transkrypcja audio przy użyciu Whisper
def transcribe_segments():
    """Transkrybuje plik audio i zwraca segmenty z tekstem i znacznikami czasu."""
    if not WAV_FILE.exists():
        print(f"❌ Błąd: Plik WAV nie został znaleziony w {WAV_FILE}")
        return None
    print("✍️ Rozpoczynam transkrypcję (to może potrwać)...")
    model = whisper.load_model("small")
    result = model.transcribe(str(WAV_FILE), language="pl", fp16=False)
    print("[OK] Transkrypcja Whisper zakończona.")
    return result["segments"]

# 3) Generowanie napisów w formacie ASS
def generate_karaoke_ass(segments):
    """Tworzy plik napisów .ass w stylu karaoke z animacjami i emoji."""
    if not segments:
        print("⚠️ Brak segmentów do przetworzenia. Pomijam tworzenie napisów.")
        return False
        
    print("🎨 Generuję napisy w stylu karaoke...")
    subs = pysubs2.SSAFile()
    subs.info.update({"ScriptType": "v4.00+", "PlayResX": 1920, "PlayResY": 1080})

    # Podstawowy styl dla karaoke
    style = pysubs2.SSAStyle()
    style.name         = "Karaoke"
    style.fontname     = "Bebas Neue"
    style.fontsize     = 64
    style.primarycolor = pysubs2.Color(r=255, g=255, b=255) # Biały
    style.backcolor    = pysubs2.Color(r=0, g=0, b=0, a=128) # Półprzezroczyste czarne tło
    style.outline      = 2
    style.shadow       = 1
    style.alignment    = 5  # Wyśrodkowanie na dole
    subs.styles[style.name] = style

    # Styl dla emoji z wyłączonym konturem i cieniem
    emoji_style = pysubs2.SSAStyle()
    emoji_style.name = "Emoji"
    emoji_style.fontname = "Segoe UI Emoji"
    emoji_style.fontsize = 64
    emoji_style.primarycolor = pysubs2.Color(r=255, g=255, b=255)  # Biały jako fallback
    emoji_style.outline = 0  # WYŁĄCZENIE konturu
    emoji_style.shadow = 0   # WYŁĄCZENIE cienia
    emoji_style.borderstyle = 0  # Brak obramowania
    emoji_style.alignment = 5
    subs.styles[emoji_style.name] = emoji_style

    # Pozycja tekstu przesunięta wyżej
    cx = subs.info["PlayResX"] // 2
    cy = int(subs.info["PlayResY"] * 0.70) # 70% wysokości ekranu

    for seg in segments:
        text = censor_text(seg.get("text", "").strip())
        if not text:
            continue
            
        words = text.split()
        start_ms = int(seg["start"] * 1000)
        end_ms   = int(seg["end"] * 1000)
        duration = end_ms - start_ms
        if duration <= 0: continue
        
        total_chars = sum(len(w) for w in words)
        if total_chars == 0: continue

        color = random.choice(TIKTOK_COLORS)
        add_emoji = random.random() < 0.3
        emoji = random.choice(EMOJIS) if add_emoji else None

        # Budowanie linii karaoke bez efektu pulsowania
        line = f"{{\\an5\\pos({cx},{cy})\\c{color}}}"
        for w in words:
            word_dur = max(int((len(w) / total_chars) * duration), 50)
            k_dur = max(word_dur // 10, 1) # Czas trwania podświetlenia w centysekundach
            
            line += f"{{\\k{k_dur}}}{w} "
            
        subs.append(pysubs2.SSAEvent(start=start_ms, end=end_ms, style=style.name, text=line.strip()))

        # Dodawanie emoji jako osobne zdarzenie z oryginalnym stylem
        if emoji:
            # Używamy prostego tekstu emoji bez dodatkowych tagów kolorystycznych
            # co pozwala na wyświetlenie oryginalnych kolorów emoji
            emoji_text = f"{{\\an5\\pos({cx},{cy+80})}}{emoji}"
            subs.append(pysubs2.SSAEvent(start=start_ms, end=end_ms, style="Emoji", text=emoji_text))

    subs.save(str(ASS_FILE))
    print(f"[OK] Zapisano napisy ASS z {len(subs.events)} zdarzeniami.")
    return True

# 4) Wypalanie napisów w pliku wideo
def burn_karaoke():
    """Wypala napisy z pliku .ass na wideo przy użyciu FFmpeg."""
    if not ASS_FILE.exists():
        print(f"❌ Błąd: Plik z napisami nie został znaleziony w {ASS_FILE}")
        return
        
    print("🎬 Rozpoczynam wypalanie napisów na wideo...")
    # Użycie cwd=dir_proj sprawia, że FFmpeg poprawnie znajduje plik .ass
    subprocess.run([
        str(FFMPEG), "-y", "-i", str(IN_VIDEO),
        "-vf", f"ass={ASS_FILE.name}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "22",
        "-c:a", "copy", str(OUT_VIDEO)
    ], check=True, cwd=str(dir_proj), capture_output=True, text=True)
    print(f"✅ Gotowe! Wynikowy plik wideo: {OUT_VIDEO}")

# Główna funkcja wykonująca wszystkie kroki
if __name__ == "__main__":
    if extract_audio():
        segments = transcribe_segments()
        if generate_karaoke_ass(segments):
            burn_karaoke()