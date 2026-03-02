# Dialogue Practice

AI-powered language partner simulator for memorizing and rehearsing dialogue scripts. Your partner's lines are spoken aloud by ElevenLabs AI voices, your lines are recorded, transcribed via Google Speech API, and scored for accuracy.

Audio-first — you hear everything, you read nothing. Forces you to actually memorize.

All generated audio is cached locally as mp3 files. First run hits the API once per line; every run after that costs zero.

## Modes

| Mode | What happens |
|------|-------------|
| **Listen** | Both roles played by AI voices. Just listen and absorb the flow. |
| **Practice** | Partner speaks, you respond from memory. Scored per line. Wrong answers get the correct version read back to you before moving on. |
| **Drill** | Hear each of your lines spoken once, repeat it back. Pronunciation training. |
| **Full run** | Listen once, then immediately enter Practice mode. |

Press **Enter** or **Space** during recording to force-submit instead of waiting for silence detection.

## Setup

**Requirements:** macOS, Python 3.8+, Homebrew, internet, a microphone, and an [ElevenLabs](https://elevenlabs.io) API key (free tier gives 10,000 characters/month).

Make sure **Text-to-Speech** permission is enabled on your ElevenLabs API key.

```bash
brew install portaudio

git clone https://github.com/DavidOrtsac/dialogue-practice.git
cd dialogue-practice

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env → paste your ElevenLabs API key
```

## Configure your dialogue

Edit the top of `practice.py`:

1. **`YOUR_NAME` / `PARTNER_NAME`** — match the speaker names in your script
2. **`PARTNER_INFO`** — fill in any details referenced by the dialogue (birthday, city, phone, etc.)
3. **`DIALOGUE`** list — replace entirely with your own script. Format: `(SPEAKER_NAME, "French text")`

### For non-French languages

The speech recognition language is set to `fr-FR` inside `record_and_transcribe()`. Change it to match your target language (e.g. `es-ES` for Spanish, `de-DE` for German, `it-IT` for Italian). [Full list of supported language codes.](https://cloud.google.com/speech-to-text/docs/speech-to-text-supported-languages)

### Changing voices

List available ElevenLabs voices:

```bash
curl -s -H "xi-api-key: YOUR_KEY" https://api.elevenlabs.io/v1/voices | python3 -m json.tool
```

Update `VOICE_PARTNER` and `VOICE_YOU` in `practice.py` with the voice IDs you want. The default model (`eleven_multilingual_v2`) supports 29 languages natively.

## Run

```bash
source .venv/bin/activate
python3 practice.py
```

First run pre-generates all audio clips via the ElevenLabs API (~2 minutes depending on dialogue length). Every subsequent run loads from cache instantly.

## The prompt

This was built with one prompt to [Claude Code](https://claude.ai/download). Swap in your own script and language:

> I have a [French] dialogue script that I need to properly practice with a teammate. Build a Terminal app that uses ElevenLabs API (the key is in .env) with eleven_multilingual_v2 for natural French TTS. Play my partner's lines as audio. I should NOT see any text, as it would make this activity too simple. In a session, record my voice everytime I must speak a line, transcribe it with Google Speech API, and score accuracy. Cache all audio locally as mp3s so repeat runs are free. Include Listen, Practice, and Drill modes. Use two distinct voices, one for me and one for my partner. If I get a line excellently or adequately, proceed to my partner's line, and vice versa. If I get a line wrong, read the correct version back as audio, before proceeding. Let me press Enter/Spacebar to force-submit my voice responses instead of waiting for silence detection, as silence detection would be a bit too iffy to implement. Here is the script I need to practice:
>
> [PASTE YOUR DIALOGUE SCRIPT]
>
> My name is [INSERT YOUR NAME FROM THE SCRIPT HERE]

## How it works

- **TTS**: ElevenLabs `eleven_multilingual_v2` with two distinct voices (default: George + Daniel)
- **STT**: Google Web Speech API via the `SpeechRecognition` library (free, no API key needed)
- **Recording**: Custom PyAudio loop with energy-based silence detection + instant keypress submit
- **Caching**: MD5 hash of `voiceId:text` → deterministic mp3 filename in `audio_cache/`
- **Scoring**: `difflib.SequenceMatcher` — 80%+ = Excellent, 55%+ = Close, below = Not quite (correct version read back)

## License

MIT
