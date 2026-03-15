"""
YouTube Video Downloader - 4K / 2K Quality
==========================================
Download YouTube videos in the highest available quality (up to 4K).
Requires: yt-dlp, ffmpeg (for merging video+audio streams)

Usage:
    python youtube_downloader.py
"""

import subprocess
import sys
import os

# ──────────────────────────── helpers ────────────────────────────

def ensure_yt_dlp():
    """Install yt-dlp if it isn't already available."""
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        print("📦 Installing yt-dlp …")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])


def check_ffmpeg():
    """Warn if ffmpeg is not on PATH (needed to merge video+audio)."""
    from shutil import which
    if which("ffmpeg") is None:
        print("\n⚠️  ffmpeg was NOT found on your PATH.")
        print("   4K/2K downloads need ffmpeg to merge separate video & audio streams.")
        print("   ➜  Install it from https://ffmpeg.org/download.html")
        print("   ➜  Or run:  winget install ffmpeg\n")
        return False
    return True


# ──────────────────────────── core ────────────────────────────

QUALITY_MAP = {
    "1": {"label": "4K  (2160p)", "height": 2160},
    "2": {"label": "2K  (1440p)", "height": 1440},
    "3": {"label": "FHD (1080p)", "height": 1080},
    "4": {"label": "HD  (720p)",  "height": 720},
    "5": {"label": "Best available", "height": None},
}


def list_formats(url):
    """Show every format the video offers (optional)."""
    import yt_dlp
    ydl_opts = {"listformats": True, "quiet": False}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def download_video(url, quality_choice, output_dir):
    """Download a YouTube video at the chosen quality with robust retry/resume."""
    import yt_dlp

    chosen = QUALITY_MAP[quality_choice]
    height = chosen["height"]

    # Build the format selector
    if height:
        fmt = (
            f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={height}]+bestaudio/"
            f"best[height<={height}]/"
            f"best"
        )
    else:
        fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"

    ydl_opts = {
        "format": fmt,
        "merge_output_format": "mp4",
        "outtmpl": os.path.join(output_dir, "%(title)s [%(resolution)s].%(ext)s"),
        "noplaylist": True,
        "consoletitle": True,

        # ── Retry & timeout settings (fixes timeout errors) ──
        "retries": 30,                 # retry each download up to 30 times
        "fragment_retries": 30,        # retry each fragment up to 30 times
        "retry_sleep_functions": {     # wait between retries (backs off)
            "http": lambda n: min(2 ** n, 60),
            "fragment": lambda n: min(2 ** n, 60),
        },
        "socket_timeout": 120,         # 120-second socket timeout (vs default ~20s)
        "continuedl": True,            # resume partially downloaded files
        "noprogress": False,

        # ── Use DASH fragments for large files (more reliable) ──
        "buffersize": 1024 * 64,       # 64 KB buffer
        "http_chunk_size": 10485760,   # download in 10 MB chunks

        # ── Metadata ──
        "writethumbnail": False,
        "postprocessors": [
            {"key": "FFmpegMetadata"},
        ],
    }

    print(f"\n🎬 Downloading in {chosen['label']} quality …")
    print(f"   ⏳ Large files (4K/2K) may take a while. The download will auto-resume if interrupted.\n")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            print(f"\n✅ Saved to: {filename}")
            return filename
    except Exception as e:
        error_msg = str(e)
        if "timed out" in error_msg.lower():
            print("\n⚠️  Download timed out. This is usually a network issue.")
            print("   💡 Tips:")
            print("      1. Run the script again — it will RESUME where it left off")
            print("      2. Try a lower quality (1080p) if timeouts persist")
            print("      3. Check your internet connection / VPN")
        else:
            print(f"\n❌ Download error: {error_msg}")
        raise


# ──────────────────────────── main ────────────────────────────

def main():
    print("=" * 55)
    print("   🎥  YouTube Video Downloader  (4K / 2K support)")
    print("=" * 55)

    # 1 — dependencies
    ensure_yt_dlp()
    has_ffmpeg = check_ffmpeg()

    # 2 — get URL
    url = input("\n🔗 Paste the YouTube video URL: ").strip()
    if not url:
        print("❌ No URL provided. Exiting.")
        return

    # 3 — choose quality
    print("\n📐 Choose download quality:")
    for key, val in QUALITY_MAP.items():
        marker = ""
        if key in ("1", "2") and not has_ffmpeg:
            marker = "  (⚠️ needs ffmpeg)"
        print(f"   [{key}] {val['label']}{marker}")

    choice = input("\nEnter choice (1-5) [default 1]: ").strip() or "1"
    if choice not in QUALITY_MAP:
        print("❌ Invalid choice. Exiting.")
        return

    # 4 — output directory
    default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    out = input(f"\n📂 Save to [{default_dir}]: ").strip() or default_dir
    os.makedirs(out, exist_ok=True)

    # 5 — optional: list formats first?
    show = input("\n📋 List available formats first? (y/N): ").strip().lower()
    if show == "y":
        list_formats(url)
        proceed = input("\nContinue with download? (Y/n): ").strip().lower()
        if proceed == "n":
            print("Bye! 👋")
            return

    # 6 — download
    download_video(url, choice, out)
    print("\n🎉 Done! Enjoy your video.\n")


if __name__ == "__main__":
    main()
