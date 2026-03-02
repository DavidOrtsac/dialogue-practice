#!/usr/bin/env python3
"""
Dialogue Practice — AI-Powered Language Partner Simulator
==========================================================
Practice any dialogue script with AI voices. Your partner's lines
are spoken aloud by ElevenLabs, your lines are recorded, transcribed,
and scored for accuracy. Audio-first: hear everything, read nothing.

Audio is cached locally so repeat runs cost zero API calls.

Requires: macOS, internet (ElevenLabs TTS + Google Speech API)
"""

import subprocess
import sys
import os
import re
import time
import hashlib
import math
import struct
import select
import termios
import tty
import difflib
import requests
import pyaudio
import speech_recognition as sr
from pathlib import Path
from dotenv import load_dotenv

# ──────────────────────────────────────────────────────────────
# LOAD API KEY FROM .env
# ──────────────────────────────────────────────────────────────
load_dotenv(Path(__file__).parent / ".env")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    print("ERROR: Set ELEVENLABS_API_KEY in .env file")
    print("  1. Copy .env.example to .env")
    print("  2. Paste your ElevenLabs API key")
    sys.exit(1)

# ──────────────────────────────────────────────────────────────
# CONFIGURE YOUR DIALOGUE HERE
# ──────────────────────────────────────────────────────────────

# Speaker names (change to match your script)
YOUR_NAME    = "Speaker A"
PARTNER_NAME = "Speaker B"

# Partner's details (used to fill in bracketed fields in the dialogue)
# Edit these to match your actual script requirements.
PARTNER_INFO = {
    "birthday": "quinze mars deux mille trois",       # e.g. "quinze mars deux mille trois"
    "age": "vingt-deux",                               # e.g. "vingt-deux"
    "city_residence": "Paris",                         # Where they live
    "city_origin": "Lyon",                             # Where they're from
    "phone": "zéro six, douze, trente-quatre, cinquante-six, soixante-dix-huit",
    "email": "exemple arobase mail point com",
}

# ──────────────────────────────────────────────────────────────
# ELEVENLABS VOICE CONFIG
# ──────────────────────────────────────────────────────────────
# Pick any two voices from your ElevenLabs account.
# Default: George (warm storyteller) & Daniel (steady broadcaster)
# List your voices: curl -H "xi-api-key: YOUR_KEY" https://api.elevenlabs.io/v1/voices
VOICE_PARTNER = "JBFqnCBsd6RMkjVDRZzb"   # George — partner's voice
VOICE_YOU     = "onwK4e9ZLuTAKqWW03F9"   # Daniel — your voice (listen/correction mode)
MODEL_ID      = "eleven_multilingual_v2"

# Recording settings
PAUSE_THRESHOLD    = 2.0    # Seconds of silence to auto-submit
PHRASE_TIME_LIMIT  = 20     # Max seconds per recording
LISTEN_TIMEOUT     = 12     # Max wait for speech to begin
SAMPLE_RATE        = 16000  # Hz
CHUNK_SIZE         = 1024   # Frames per buffer
SAMPLE_WIDTH       = 2      # Bytes per sample (16-bit)

# Audio cache directory
CACHE_DIR = Path(__file__).parent / "audio_cache"

# ──────────────────────────────────────────────────────────────
# THE DIALOGUE SCRIPT
# ──────────────────────────────────────────────────────────────
# Format: (speaker_name, french_text)
# Use YOUR_NAME for your lines, PARTNER_NAME for your partner's.
#
# *** REPLACE THIS ENTIRE LIST WITH YOUR OWN DIALOGUE ***
#
DIALOGUE = [
    (YOUR_NAME,    "Bonjour! Comment allez-vous?"),
    (PARTNER_NAME, "Bonjour! Très bien, et vous?"),
    (YOUR_NAME,    "Bien, merci. Comment vous vous appelez?"),
    (PARTNER_NAME, "Je m'appelle Marie."),
    (YOUR_NAME,    "Comment ça s'écrit?"),
    (PARTNER_NAME, "Ça s'écrit, M. A. R. I. E."),
    (YOUR_NAME,    "Quelle est votre date de naissance?"),
    (PARTNER_NAME, f"Je suis née le {PARTNER_INFO['birthday']}."),
    (YOUR_NAME,    "Vous avez quel âge?"),
    (PARTNER_NAME, f"J'ai {PARTNER_INFO['age']} ans."),
    (YOUR_NAME,    "Vous habitez où?"),
    (PARTNER_NAME, f"J'habite à {PARTNER_INFO['city_residence']}."),
    (YOUR_NAME,    "Vous venez d'où?"),
    (PARTNER_NAME, f"Je viens de {PARTNER_INFO['city_origin']}."),
    (YOUR_NAME,    "Quel est votre numéro de portable?"),
    (PARTNER_NAME, f"C'est le {PARTNER_INFO['phone']}."),
    (YOUR_NAME,    "Quel est votre email?"),
    (PARTNER_NAME, f"C'est {PARTNER_INFO['email']}."),
    (YOUR_NAME,    "Vous parlez quelles langues, le japonais et le coréen?"),
    (PARTNER_NAME, "Non, je parle anglais et un peu français. Je ne parle pas japonais. Je ne parle pas coréen."),
    (YOUR_NAME,    "Merci! Au revoir, à bientôt!"),
    (PARTNER_NAME, "Merci! Au revoir, à bientôt!"),
]

# ──────────────────────────────────────────────────────────────
# TERMINAL FORMATTING
# ──────────────────────────────────────────────────────────────
class F:
    GREEN   = "\033[92m"
    RED     = "\033[91m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    CYAN    = "\033[96m"
    MAGENTA = "\033[95m"
    DIM     = "\033[2m"
    BOLD    = "\033[1m"
    RESET   = "\033[0m"

def clr():
    os.system("clear")

# ──────────────────────────────────────────────────────────────
# ELEVENLABS TTS (with local caching)
# ──────────────────────────────────────────────────────────────
def _cache_key(voice_id, text):
    """Deterministic filename for a (voice, text) pair."""
    h = hashlib.md5(f"{voice_id}:{text}".encode()).hexdigest()[:12]
    return CACHE_DIR / f"{h}.mp3"

def tts_generate(text, voice_id):
    """Generate TTS audio via ElevenLabs API, return path to cached mp3."""
    mp3_path = _cache_key(voice_id, text)
    if mp3_path.exists():
        return mp3_path

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": MODEL_ID,
        "voice_settings": {
            "stability": 0.50,
            "similarity_boost": 0.75,
        },
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    if resp.status_code != 200:
        print(f"  {F.RED}ElevenLabs error {resp.status_code}: {resp.text[:200]}{F.RESET}")
        return None

    mp3_path.write_bytes(resp.content)
    return mp3_path

def play_audio(mp3_path):
    """Play an mp3 file using macOS afplay."""
    if mp3_path and mp3_path.exists():
        subprocess.run(["afplay", str(mp3_path)])

def speak(text, voice_id=VOICE_PARTNER):
    """Generate (or load cached) and play ElevenLabs TTS."""
    path = tts_generate(text, voice_id)
    play_audio(path)

def beep(name="Tink"):
    """Play a macOS system sound (non-blocking)."""
    path = f"/System/Library/Sounds/{name}.aiff"
    if os.path.exists(path):
        subprocess.Popen(["afplay", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def speak_english(text, rate=180):
    """Speak English via macOS say (for system prompts only)."""
    subprocess.run(["say", "-v", "Samantha", "-r", str(rate), text])

# ──────────────────────────────────────────────────────────────
# PRE-GENERATE ALL AUDIO (runs once, then cached)
# ──────────────────────────────────────────────────────────────
def pregenerate_audio():
    """Pre-generate all dialogue audio so playback is instant."""
    CACHE_DIR.mkdir(exist_ok=True)

    pairs = []
    for speaker, text in DIALOGUE:
        voice = VOICE_PARTNER if speaker == PARTNER_NAME else VOICE_YOU
        pairs.append((voice, text))

    to_generate = [(v, t) for v, t in pairs if not _cache_key(v, t).exists()]

    if not to_generate:
        return True

    total = len(to_generate)
    print(f"\n  {F.BOLD}Generating {total} audio clips via ElevenLabs...{F.RESET}")
    print(f"  {F.DIM}(This only happens once — audio is cached for future runs){F.RESET}\n")

    for idx, (voice_id, text) in enumerate(to_generate):
        label = PARTNER_NAME if voice_id == VOICE_PARTNER else YOUR_NAME
        short = text[:50] + ("..." if len(text) > 50 else "")
        print(f"  {F.DIM}[{idx+1}/{total}] {label}: {short}{F.RESET}")

        path = tts_generate(text, voice_id)
        if path is None:
            print(f"  {F.RED}Failed to generate audio. Check API key.{F.RESET}")
            return False

    print(f"\n  {F.GREEN}All audio cached! Future runs will be instant.{F.RESET}\n")
    return True

# ──────────────────────────────────────────────────────────────
# TEXT COMPARISON
# ──────────────────────────────────────────────────────────────
def normalize(text):
    t = text.lower().strip()
    t = re.sub(r"[^\w\sàâäéèêëïîôùûüÿçœæ']", "", t)
    t = re.sub(r"\s+", " ", t)
    return t

def similarity(expected, got):
    return difflib.SequenceMatcher(None, normalize(expected), normalize(got)).ratio()

# ──────────────────────────────────────────────────────────────
# SPEECH RECOGNITION (custom PyAudio loop + keypress submit)
# ──────────────────────────────────────────────────────────────
def _rms(data):
    """Compute RMS energy of a raw audio chunk (16-bit LE mono)."""
    count = len(data) // SAMPLE_WIDTH
    if count == 0:
        return 0.0
    shorts = struct.unpack(f"<{count}h", data)
    return math.sqrt(sum(s * s for s in shorts) / count)

def init_recognizer():
    """Calibrate energy threshold from 2 seconds of ambient noise."""
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print(f"  {F.DIM}Calibrating microphone — stay quiet for 2 seconds...{F.RESET}")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=2)
    print(f"  {F.GREEN}Microphone ready.{F.RESET}")
    print(f"  {F.DIM}(Press Enter or Space to submit early during recording){F.RESET}\n")

    return recognizer

def record_and_transcribe(recognizer):
    """Record audio with silence auto-detect + Enter/Space to force-submit."""
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK_SIZE,
    )

    frames = []
    silent_chunks = 0
    speaking = False
    threshold = recognizer.energy_threshold
    pause_limit = int(PAUSE_THRESHOLD * SAMPLE_RATE / CHUNK_SIZE)
    timeout_limit = int(LISTEN_TIMEOUT * SAMPLE_RATE / CHUNK_SIZE)
    max_limit = int(PHRASE_TIME_LIMIT * SAMPLE_RATE / CHUNK_SIZE)
    total = 0
    key_submitted = False

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setcbreak(fd)

    try:
        while total < max_limit:
            data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            frames.append(data)
            total += 1

            if select.select([sys.stdin], [], [], 0)[0]:
                key = sys.stdin.read(1)
                if key in ("\n", "\r", " "):
                    key_submitted = True
                    break

            energy = _rms(data)

            if energy > threshold:
                speaking = True
                silent_chunks = 0
            elif speaking:
                silent_chunks += 1
                if silent_chunks >= pause_limit:
                    break
            else:
                if total >= timeout_limit:
                    break
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        stream.stop_stream()
        stream.close()
        p.terminate()

    if not frames or (not speaking and not key_submitted):
        return None

    raw = b"".join(frames)
    audio = sr.AudioData(raw, SAMPLE_RATE, SAMPLE_WIDTH)

    try:
        return recognizer.recognize_google(audio, language="fr-FR")
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        print(f"  {F.RED}Speech API error: {e}{F.RESET}")
        return None

# ──────────────────────────────────────────────────────────────
# LISTEN MODE
# ──────────────────────────────────────────────────────────────
def listen_mode():
    clr()
    print(f"\n  {F.BOLD}{F.BLUE}LISTEN MODE{F.RESET}")
    print(f"  {F.DIM}Both parts spoken aloud by AI voices.")
    print(f"  Just listen and absorb the flow.")
    print(f"  Press Ctrl+C to skip.{F.RESET}\n")

    beep("Hero")
    time.sleep(1.5)

    for i, (speaker, text) in enumerate(DIALOGUE):
        turn = f"({i+1}/{len(DIALOGUE)})"

        if speaker == PARTNER_NAME:
            print(f"  {F.BLUE}{PARTNER_NAME:8s} {F.DIM}{turn}{F.RESET}")
            speak(text, VOICE_PARTNER)
        else:
            print(f"  {F.CYAN}{YOUR_NAME:8s} {F.DIM}{turn}{F.RESET}")
            speak(text, VOICE_YOU)

        time.sleep(0.4)

    print(f"\n  {F.GREEN}End of dialogue.{F.RESET}\n")
    beep("Glass")

# ──────────────────────────────────────────────────────────────
# PRACTICE MODE
# ──────────────────────────────────────────────────────────────
def practice_mode():
    clr()
    print(f"\n  {F.BOLD}{F.CYAN}PRACTICE MODE{F.RESET}")
    print(f"  {F.DIM}{PARTNER_NAME} speaks their lines. You speak yours from memory.")
    print(f"  A chime means it's your turn. No text shown.")
    print(f"  Wrong answers get the correct version read back to you.")
    print(f"  Press Ctrl+C to quit anytime.{F.RESET}\n")

    recognizer = init_recognizer()

    beep("Hero")
    speak_english("Let's begin. You start the conversation.", rate=170)
    time.sleep(1)

    scores = []
    consecutive_fails = 0
    i = 0

    while i < len(DIALOGUE):
        speaker, text = DIALOGUE[i]

        if speaker == PARTNER_NAME:
            print(f"  {F.BLUE}{PARTNER_NAME}{F.RESET}")
            speak(text, VOICE_PARTNER)
            time.sleep(0.3)
            i += 1

        else:
            print(f"  {F.CYAN}You ... {F.DIM}(Enter to submit){F.RESET}", end="", flush=True)
            beep("Tink")

            transcribed = record_and_transcribe(recognizer)

            if transcribed is None:
                consecutive_fails += 1
                print(f"\r  {F.YELLOW}(didn't catch that){F.RESET}       ")

                if consecutive_fails >= 3:
                    print(f"  {F.DIM}Here's what you should say:{F.RESET}")
                    speak(text, VOICE_YOU)
                    scores.append(0.0)
                    consecutive_fails = 0
                    i += 1
                else:
                    beep("Basso")
                    speak_english("Try again.", rate=180)
                continue

            consecutive_fails = 0
            s = similarity(text, transcribed)
            scores.append(s)

            if s >= 0.80:
                print(f"\r  {F.GREEN}Excellent!{F.RESET}              ")
                beep("Glass")
            elif s >= 0.55:
                print(f"\r  {F.YELLOW}Close!{F.RESET}                  ")
                beep("Purr")
                time.sleep(0.3)
                speak(text, VOICE_YOU)
            else:
                print(f"\r  {F.RED}Not quite.{F.RESET}              ")
                beep("Basso")
                time.sleep(0.3)
                speak_english("Listen.", rate=180)
                time.sleep(0.2)
                speak(text, VOICE_YOU)

            time.sleep(0.3)
            i += 1

        print()

    if scores:
        avg = sum(scores) / len(scores)
        perfect = sum(1 for s in scores if s >= 0.80)
        total = len(scores)

        print(f"\n  {F.BOLD}{'─' * 42}")
        print(f"  FINAL SCORE: {avg:.0%}  ({perfect}/{total} lines nailed)")
        print(f"  {'─' * 42}{F.RESET}")

        if avg >= 0.85:
            print(f"  {F.GREEN}Formidable!{F.RESET}")
            speak("Formidable! Excellent travail!", VOICE_PARTNER)
        elif avg >= 0.65:
            print(f"  {F.YELLOW}Pas mal!{F.RESET}")
            speak("Pas mal! Continuez à pratiquer!", VOICE_PARTNER)
        else:
            print(f"  {F.RED}Courage!{F.RESET}")
            speak("Courage! La pratique fait le maître!", VOICE_PARTNER)
        print()

# ──────────────────────────────────────────────────────────────
# DRILL MODE — Hear your lines, repeat them back
# ──────────────────────────────────────────────────────────────
def drill_mode():
    clr()
    print(f"\n  {F.BOLD}{F.YELLOW}DRILL MODE{F.RESET}")
    print(f"  {F.DIM}Hear each of your lines, then repeat it back.")
    print(f"  Great for pronunciation practice.{F.RESET}\n")

    recognizer = init_recognizer()
    beep("Hero")
    time.sleep(1)

    your_lines = [(i, text) for i, (spk, text) in enumerate(DIALOGUE) if spk == YOUR_NAME]
    scores = []

    for idx, (line_num, text) in enumerate(your_lines):
        print(f"  {F.DIM}Line {idx+1}/{len(your_lines)}{F.RESET}")

        speak(text, VOICE_YOU)
        time.sleep(0.5)

        print(f"  {F.CYAN}Repeat ... {F.DIM}(Enter to submit){F.RESET}", end="", flush=True)
        beep("Tink")

        transcribed = record_and_transcribe(recognizer)

        if transcribed is None:
            print(f"\r  {F.YELLOW}(didn't catch that){F.RESET}       ")
            scores.append(0.0)
        else:
            s = similarity(text, transcribed)
            scores.append(s)
            if s >= 0.80:
                print(f"\r  {F.GREEN}Excellent!{F.RESET}              ")
                beep("Glass")
            elif s >= 0.55:
                print(f"\r  {F.YELLOW}Close!{F.RESET}                  ")
                beep("Purr")
            else:
                print(f"\r  {F.RED}Not quite.{F.RESET}              ")
                beep("Basso")
                time.sleep(0.2)
                speak(text, VOICE_YOU)

        time.sleep(0.5)
        print()

    if scores:
        avg = sum(scores) / len(scores)
        print(f"\n  {F.BOLD}Drill score: {avg:.0%}{F.RESET}\n")

# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────
def main():
    clr()
    print(f"""
  {F.BOLD}{F.CYAN}╔════════════════════════════════════════════╗
  ║  Dialogue Practice                         ║
  ║  AI-Powered Language Partner Simulator     ║
  ║  {F.MAGENTA}Powered by ElevenLabs AI Voices{F.CYAN}            ║
  ╚════════════════════════════════════════════╝{F.RESET}
""")

    print(f"  {F.DIM}Checking audio cache...{F.RESET}")
    if not pregenerate_audio():
        sys.exit(1)

    print(f"""
  {F.BOLD}Choose a mode:{F.RESET}

    {F.CYAN}[1]{F.RESET} Listen    — Hear the full dialogue (both AI voices)
    {F.CYAN}[2]{F.RESET} Practice  — Partner speaks, you respond from memory
    {F.CYAN}[3]{F.RESET} Drill     — Hear your lines, repeat them back
    {F.CYAN}[4]{F.RESET} Full run  — Listen once, then practice
    {F.CYAN}[q]{F.RESET} Quit
""")

    choice = input(f"  {F.BOLD}>{F.RESET} ").strip().lower()

    if choice == "1":
        listen_mode()
    elif choice == "2":
        practice_mode()
    elif choice == "3":
        drill_mode()
    elif choice == "4":
        listen_mode()
        input(f"\n  {F.CYAN}Press Enter when ready to practice...{F.RESET}")
        practice_mode()
    elif choice == "q":
        print(f"\n  {F.DIM}Au revoir!{F.RESET}\n")
    else:
        print(f"\n  {F.RED}Invalid choice. Run again.{F.RESET}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {F.DIM}Au revoir!{F.RESET}\n")
        sys.exit(0)
