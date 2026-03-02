# Dialogue Practice 🎙️🇫🇷

**Your own personal Duolingo — built with one Claude Code prompt.**

A terminal-based dialogue practice app powered by **ElevenLabs AI voices**. Paste any dialogue script, and it becomes an interactive voice practice session with real-time speech recognition and scoring.

## What It Does

- **ElevenLabs AI voices** play your partner's lines in natural French (not robotic TTS)
- **Speech recognition** listens to you speak, transcribes, and scores accuracy
- **Audio caching** — generates all audio once, then every future run is instant (zero API calls)
- **Press Enter/Space** to force-submit your recording instead of waiting for silence detection

## Modes

| Mode | Description |
|------|-------------|
| **Listen** | Hear the full dialogue with both AI voices — just absorb the flow |
| **Practice** | Partner speaks their lines, you respond from memory (scored) |
| **Drill** | Hear your lines spoken once, repeat them back for pronunciation |
| **Full Run** | Listen once, then practice |

## Setup

### 1. Get an ElevenLabs API Key
- Sign up at [elevenlabs.io](https://elevenlabs.io) (free tier = 10,000 chars/month)
- Go to Profile → API Key → copy it

### 2. Clone and Configure
```bash
git clone https://github.com/DavidOrtsac/dialogue-practice.git
cd dialogue-practice

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up your API key
cp .env.example .env
# Edit .env and paste your ElevenLabs API key
```

### 3. Run
```bash
python3 practice.py
```

On first run, it pre-generates all audio clips (~25 clips for the default dialogue). Takes about 2 minutes. Every run after that is **instant**.

## The One-Shot Prompt

This entire app was built with a single prompt to Claude Code:

> I have a French dialogue script that I need to practice with a partner. I want you to build a terminal app that:
>
> 1. Uses ElevenLabs API (key in .env file) with `eleven_multilingual_v2` for natural French TTS
> 2. Plays my partner's lines as audio — I should NOT see any text of what to say
> 3. Records my voice when it's my turn, transcribes it with Google Speech API, and scores how close I got
> 4. Caches all generated audio as mp3 files locally so repeat runs cost zero API calls
> 5. Has 3 modes: Listen (hear full dialogue), Practice (partner speaks, I respond from memory), Drill (hear my lines, repeat them back)
> 6. Uses two distinct ElevenLabs voices so I can tell the speakers apart
> 7. If I get a line wrong, reads the correct version back to me (audio, not text)
> 8. Lets me press Enter or Space to force-submit my recording instead of waiting for silence detection
>
> Here is my dialogue script:
>
> [PASTE YOUR SCRIPT HERE — format each line as "Speaker: French text"]
>
> Make it work on macOS in one shot. Use Python with PyAudio, SpeechRecognition, and requests. Store the ElevenLabs API key in a .env file, never hardcode it.

Swap out the dialogue for any language — Spanish, German, Italian — and it works.

## How It Works

```
practice.py          → Main app (menu, modes, game loop)
audio_cache/         → Auto-generated mp3s (gitignored)
.env                 → Your ElevenLabs API key (gitignored)
```

- **TTS**: ElevenLabs `eleven_multilingual_v2` with two distinct voices
- **STT**: Google Speech Recognition API (free, no key needed)
- **Caching**: MD5 hash of `voiceId:text` → deterministic mp3 filename
- **Scoring**: `difflib.SequenceMatcher` fuzzy comparison (≥80% = Excellent, ≥55% = Close, <55% = Not quite)

## Requirements

- **macOS** (uses `afplay` for audio playback and `say` for English system prompts)
- **Python 3.8+**
- **Microphone** access
- **ElevenLabs API key** (free tier works)

## License

MIT
