# Dialogue Practice

AI-powered language partner simulator. Practice any dialogue script with natural AI voices — your partner's lines are spoken aloud, your lines are recorded, transcribed, and scored.

**Audio-first**: you hear everything, you read nothing. Like having a real practice partner.

## How it works

1. Paste your dialogue script into `practice.py` (the `DIALOGUE` list)
2. Your partner's lines are spoken by an ElevenLabs AI voice
3. When it's your turn, you speak from memory
4. Your speech is transcribed and compared to the expected line
5. If you get it wrong, the correct version is read back to you

All generated audio is cached locally as mp3 files — repeat runs cost zero API calls.

## Modes

| Mode | Description |
|------|-------------|
| **Listen** | Hear the full dialogue (both roles) to learn the flow |
| **Practice** | Partner speaks, you respond from memory and get scored |
| **Drill** | Hear each of your lines, then repeat it back |
| **Full run** | Listen once, then immediately practice |

Press **Enter** or **Space** during recording to force-submit instead of waiting for silence detection.

## Setup

### Prerequisites

- macOS (uses `afplay` and `say` for audio)
- Python 3.10+
- [Homebrew](https://brew.sh)
- An [ElevenLabs](https://elevenlabs.io) API key (free tier works)
  - Make sure **Text-to-Speech** permission is enabled on your key

### Install

```bash
# Install system dependency
brew install portaudio

# Clone and set up
git clone https://github.com/DavidOrtsac/dialogue-practice.git
cd dialogue-practice

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Add your API key
cp .env.example .env
# Edit .env and paste your ElevenLabs API key
```

### Configure your dialogue

Edit the top of `practice.py`:

1. Set `YOUR_NAME` and `PARTNER_NAME`
2. Fill in `PARTNER_INFO` with your partner's details
3. Replace the `DIALOGUE` list with your actual script

### Run

```bash
source .venv/bin/activate
python3 practice.py
```

## Changing voices

ElevenLabs provides many voices. List yours:

```bash
curl -s -H "xi-api-key: YOUR_KEY" https://api.elevenlabs.io/v1/voices | python3 -m json.tool
```

Then update `VOICE_PARTNER` and `VOICE_YOU` in `practice.py` with the voice IDs you want.

The default model (`eleven_multilingual_v2`) speaks 29 languages natively — this works for French, Spanish, German, Italian, Portuguese, and more.

## Caching

Audio files are cached in `audio_cache/` using an MD5 hash of `voice_id:text` as the filename. If you change your dialogue text or switch voices, new audio will be generated automatically. Old cached files can be safely deleted.

## Built with

- [ElevenLabs](https://elevenlabs.io) — AI text-to-speech
- [Google Speech Recognition](https://cloud.google.com/speech-to-text) — speech-to-text (via SpeechRecognition library, no API key needed)
- [PyAudio](https://people.csail.mit.edu/hubert/pyaudio/) — microphone recording
- Python, a terminal, and vibes
