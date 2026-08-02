# 🎬 Crypto Video Generator

Automatically generates short crypto videos with voiceover and subtitles.

## What it does

1. Generates a script on a topic (templates or OpenAI)
2. Converts text to speech via edge-tts (free, no API key needed)
3. Downloads stock footage from Pexels
4. Assembles the final MP4 with subtitles using ffmpeg

## Setup

```bash
# 1. Install ffmpeg
brew install ffmpeg

# 2. Install dependencies
cd crypto-video-gen
pip install -r requirements.txt

# 3. Get a free Pexels API key
# → https://www.pexels.com/api/
# Add to main.py: PEXELS_API_KEY = "your_key"

# 4. (Optional) OpenAI key for AI-generated scripts
# → https://platform.openai.com
# Add to main.py: OPENAI_API_KEY = "your_key"
```

## Usage

```bash
# By topic
python main.py bitcoin
python main.py ethereum
python main.py base
python main.py airdrop

# Interactive mode
python main.py
```

## Built-in topics (no OpenAI required)

- `bitcoin` — about Bitcoin
- `ethereum` — about Ethereum
- `base` — about Base Network
- `defi` — about DeFi
- `airdrop` — about airdrops
- any other topic → uses a base template

## Output

Files are saved to the `output/` folder:
- `*_audio.mp3` — voiceover
- `*_subs.srt` — subtitles
- `*_final.mp4` — final video (1080×1920, vertical)

## Stack

- **edge-tts** — TTS voice (Microsoft, free)
- **Pexels API** — stock footage (free)
- **ffmpeg** — video assembly
- **OpenAI** — AI script generation (optional)
