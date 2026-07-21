"""
Crypto Video Generator
======================
Generates short crypto-themed videos with voiceover and subtitles.

Pipeline:
  topic → script → TTS audio → stock footage → final video

Requirements:
  pip install edge-tts moviepy requests pillow openai
  ffmpeg must be installed: brew install ffmpeg

APIs needed (free):
  - Pexels API key: https://www.pexels.com/api/
  - OpenAI API key (optional, uses templates if not set): https://platform.openai.com
"""

import os
import sys
import asyncio
import textwrap
import requests
import subprocess
from pathlib import Path
from datetime import datetime

# Optional OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PEXELS_API_KEY = "YOUR_PEXELS_KEY"      # get free at pexels.com/api
OPENAI_API_KEY = ""                      # optional, leave empty to use templates

OUTPUT_DIR  = Path("output")
ASSETS_DIR  = Path("assets")
VIDEO_W     = 1080
VIDEO_H     = 1920   # vertical (TikTok/Reels format)
FPS         = 30
VOICE       = "en-US-GuyNeural"         # edge-tts voice

OUTPUT_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Script generation
# ---------------------------------------------------------------------------

TEMPLATES = {
    "bitcoin": """
Bitcoin is the world's first decentralized cryptocurrency, created in 2009.
Unlike traditional money, no bank or government controls it.
There will only ever be 21 million Bitcoin in existence — making it scarce by design.
Today, Bitcoin is held by millions of people worldwide as a store of value.
Many call it digital gold. And the adoption is only growing.
""",
    "ethereum": """
Ethereum is more than just a cryptocurrency — it's a programmable blockchain.
Developers use it to build decentralized apps, NFT platforms, and DeFi protocols.
The native token, ETH, powers every transaction on the network.
After the Merge in 2022, Ethereum became 99% more energy efficient.
It remains the most active developer ecosystem in all of crypto.
""",
    "base": """
Base is a fast, cheap Ethereum Layer 2 network built by Coinbase.
It lets you use all your favorite crypto apps with nearly zero fees.
Hundreds of thousands of wallets are active on Base every single day.
From DeFi to NFTs to airdrops — Base is where the action is.
If you're not on Base yet, you're missing out on the fastest growing L2.
""",
    "defi": """
DeFi stands for Decentralized Finance — banking without banks.
You can lend, borrow, earn yield, and trade crypto without any middlemen.
All you need is a wallet and an internet connection.
DeFi protocols handle billions of dollars in transactions every day.
The financial system is being rebuilt on-chain, and it's happening right now.
""",
    "airdrop": """
Crypto airdrops are free token distributions to early users of a protocol.
Projects reward people who use their platform before the official token launch.
Some airdrops have been worth thousands — even tens of thousands of dollars.
To qualify, you need to interact with protocols: swap, bridge, provide liquidity.
The more active you are on-chain, the better your airdrop chances.
""",
    "default": """
Cryptocurrency is transforming the global financial system.
Blockchain technology enables trustless, permissionless transactions.
You no longer need a bank to send money across the world in seconds.
Crypto gives financial freedom to anyone with a smartphone.
The future of finance is decentralized — and it's already here.
"""
}


def generate_script(topic: str) -> str:
    """Generates a video script for the given crypto topic."""

    # Try OpenAI if configured
    if OPENAI_API_KEY and OPENAI_AVAILABLE:
        try:
            client = OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": (
                        "You write 30-second scripts for crypto educational short videos. "
                        "Write 5-6 punchy sentences. No hashtags, no emojis, no titles. "
                        "Plain spoken text only. Engaging and informative."
                    )
                }, {
                    "role": "user",
                    "content": f"Write a script about: {topic}"
                }],
                max_tokens=300
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"  OpenAI error: {e} — using template")

    # Fall back to templates
    key = topic.lower()
    for k in TEMPLATES:
        if k in key:
            return TEMPLATES[k].strip()
    return TEMPLATES["default"].strip()


# ---------------------------------------------------------------------------
# TTS (text-to-speech) — free via edge-tts
# ---------------------------------------------------------------------------

async def _tts_async(text: str, output_path: str, voice: str) -> None:
    """Runs edge-tts to generate audio file."""
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
    except ImportError:
        raise RuntimeError("edge-tts not installed. Run: pip install edge-tts")


def generate_audio(text: str, path: str, voice: str = VOICE) -> str:
    """Generates voiceover audio from text. Returns path to audio file."""
    print(f"  Generating voiceover...")
    asyncio.run(_tts_async(text, path, voice))
    return path


# ---------------------------------------------------------------------------
# Stock footage — Pexels API
# ---------------------------------------------------------------------------

def download_video(query: str, dest: str) -> str | None:
    """Downloads a stock video from Pexels matching the query."""
    if PEXELS_API_KEY == "YOUR_PEXELS_KEY":
        print("  ⚠️  No Pexels key set — skipping video download")
        return None

    headers = {"Authorization": PEXELS_API_KEY}
    url = "https://api.pexels.com/videos/search"
    params = {"query": query, "per_page": 5, "size": "medium", "orientation": "portrait"}

    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        videos = r.json().get("videos", [])

        if not videos:
            print(f"  No videos found for '{query}'")
            return None

        # Pick first video with a good resolution
        for video in videos:
            for vf in video.get("video_files", []):
                if vf.get("height", 0) >= 720:
                    video_url = vf["link"]
                    print(f"  Downloading footage: {video['url']}")
                    vr = requests.get(video_url, stream=True, timeout=30)
                    with open(dest, "wb") as f:
                        for chunk in vr.iter_content(chunk_size=8192):
                            f.write(chunk)
                    return dest

    except Exception as e:
        print(f"  Pexels error: {e}")

    return None


# ---------------------------------------------------------------------------
# Video assembly — ffmpeg
# ---------------------------------------------------------------------------

def check_ffmpeg() -> bool:
    """Checks if ffmpeg is available."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def create_subtitle_file(script: str, audio_path: str, srt_path: str) -> str:
    """Creates a simple SRT subtitle file from the script."""
    sentences = [s.strip() for s in script.replace("\n", " ").split(".") if s.strip()]

    # Estimate duration per sentence (rough: ~130 words/min)
    words_per_sec = 2.5
    lines = []
    t = 0.0
    for i, sentence in enumerate(sentences, 1):
        words = len(sentence.split())
        duration = max(2.0, words / words_per_sec)
        start = _fmt_time(t)
        end   = _fmt_time(t + duration)
        # Wrap long lines
        wrapped = "\n".join(textwrap.wrap(sentence + ".", 40))
        lines.append(f"{i}\n{start} --> {end}\n{wrapped}\n")
        t += duration

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return srt_path


def _fmt_time(seconds: float) -> str:
    """Formats seconds to SRT timestamp format."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def assemble_video(
    audio_path: str,
    video_path: str | None,
    srt_path: str,
    output_path: str,
    topic: str
) -> str:
    """Assembles final video using ffmpeg."""

    if not check_ffmpeg():
        print("\n  ❌ ffmpeg not found. Install with: brew install ffmpeg")
        print(f"  Audio saved at: {audio_path}")
        return audio_path

    # Get audio duration
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True
    )
    duration = float(probe.stdout.strip()) if probe.stdout.strip() else 30.0

    if video_path and os.path.exists(video_path):
        # Combine stock footage + audio + subtitles
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", video_path,
            "-i", audio_path,
            "-vf", (
                f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=increase,"
                f"crop={VIDEO_W}:{VIDEO_H},"
                f"subtitles={srt_path}:force_style='FontSize=20,PrimaryColour=&HFFFFFF,"
                f"OutlineColour=&H000000,Outline=2,Alignment=2'"
            ),
            "-af", "volume=1.5",
            "-t", str(duration),
            "-c:v", "libx264", "-c:a", "aac",
            "-shortest", output_path
        ]
    else:
        # No footage — create black background with text + audio
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=black:s={VIDEO_W}x{VIDEO_H}:r={FPS}",
            "-i", audio_path,
            "-vf", (
                f"drawtext=text='{topic.upper()}':fontcolor=white:fontsize=60:"
                f"x=(w-text_w)/2:y=(h-text_h)/2,"
                f"subtitles={srt_path}:force_style='FontSize=22,PrimaryColour=&HFFFFFF,"
                f"OutlineColour=&H000000,Outline=2,Alignment=2'"
            ),
            "-t", str(duration),
            "-c:v", "libx264", "-c:a", "aac",
            "-shortest", output_path
        ]

    print(f"  Assembling video...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ffmpeg error:\n{result.stderr[-500:]}")
        return audio_path

    return output_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate_video(topic: str) -> None:
    """Full pipeline: topic → finished video."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = topic.lower().replace(" ", "_")[:20]
    prefix = OUTPUT_DIR / f"{slug}_{ts}"

    audio_path  = str(prefix) + "_audio.mp3"
    video_path  = str(prefix) + "_footage.mp4"
    srt_path    = str(prefix) + "_subs.srt"
    output_path = str(prefix) + "_final.mp4"

    print(f"\n{'='*50}")
    print(f"  🎬 CRYPTO VIDEO GENERATOR")
    print(f"{'='*50}")
    print(f"  Topic: {topic}")
    print()

    # 1. Script
    print("  [1/4] Generating script...")
    script = generate_script(topic)
    print(f"\n  Script preview:\n  {script[:120]}...\n")

    # 2. Audio
    print("  [2/4] Generating voiceover...")
    generate_audio(script, audio_path)
    print(f"  ✅ Audio: {audio_path}")

    # 3. Footage
    print(f"  [3/4] Fetching stock footage for '{topic}'...")
    footage = download_video(topic + " cryptocurrency", video_path)

    # 4. Subtitles + assemble
    print("  [4/4] Assembling video...")
    create_subtitle_file(script, audio_path, srt_path)
    final = assemble_video(audio_path, footage, srt_path, output_path, topic)

    print(f"\n{'='*50}")
    if final.endswith(".mp4"):
        print(f"  ✅ Done! Video saved:")
        print(f"     {final}")
    else:
        print(f"  ⚠️  ffmpeg missing — audio only saved:")
        print(f"     {final}")
        print(f"  Install ffmpeg: brew install ffmpeg")
    print(f"{'='*50}\n")


def main() -> None:
    """Entry point."""
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    else:
        print("\nAvailable topics: bitcoin, ethereum, base, defi, airdrop")
        topic = input("Enter topic (or custom text): ").strip()
        if not topic:
            topic = "bitcoin"

    generate_video(topic)


if __name__ == "__main__":
    main()
