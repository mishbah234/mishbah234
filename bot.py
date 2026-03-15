import os
import re
import uuid
import glob
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp

# ──────────────────────────── config ────────────────────────────
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
API_ID = int(os.environ.get("API_ID", "24223583"))
API_HASH = os.environ.get("API_HASH", "8601a6f42f20a392f241bd33b8bf6b10")

if not BOT_TOKEN:
    print("❌ ERROR: TELEGRAM_BOT_TOKEN is missing!")
    exit(1)

# Pyrogram uses MTProto protocol — supports up to 2GB file uploads!
bot = Client(
    "video_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True,  # Don't create a session file on disk
)

# 2 GB limit (Telegram's absolute maximum for bots via MTProto)
MAX_FILE_SIZE_BYTES = 2_000_000_000

# ──────────────────────────── helpers ────────────────────────────
def _safe_filename(title):
    name = re.sub(r'[^\w\s\-]', '', title).strip()
    return name[:120] or "video"


def _find_downloaded_file(task_id):
    """Find the actual file yt-dlp downloaded (it may change the extension)."""
    matches = glob.glob(f"download_{task_id}_*")
    if matches:
        return matches[0]
    return None


# ──────────────────────────── bot handlers ────────────────────────────

@bot.on_message(filters.command(["start", "help"]))
async def send_welcome(client: Client, message: Message):
    welcome_text = (
        "👋 **Welcome to the Video Downloader Bot!**\n\n"
        "Send me a link to a **YouTube** or **Instagram** video, "
        "and I will download it for you.\n\n"
        "📦 Supports files up to **2 GB**!"
    )
    await message.reply_text(welcome_text)


@bot.on_message(filters.text & filters.private)
async def handle_message(client: Client, message: Message):
    url = message.text.strip()

    # Basic URL check
    if not url.startswith("http://") and not url.startswith("https://"):
        await message.reply_text("⚠️ Please send a valid URL starting with http:// or https://")
        return

    # Acknowledge the request
    status_msg = await message.reply_text("⏳ **Extracting video info...**")

    task_id = uuid.uuid4().hex[:8]
    output_template = f"download_{task_id}_%(title)s.%(ext)s"

    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "extractor_args": {
            "youtube": {
                "player_client": ["android_vr", "ios", "tv", "web"],
                "player_skip": ["webpage", "configs"]
            }
        }
    }

    # Use cookies if available
    if os.path.exists("cookies.txt"):
        ydl_opts["cookiefile"] = "cookies.txt"

    downloaded_file = None
    try:
        # Step 1: Download
        await status_msg.edit_text("⏳ **Downloading video... Please wait...**")

        # Run yt-dlp in a thread so we don't block asyncio
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: _download_video(ydl_opts, url))

        # Find the file yt-dlp actually saved
        downloaded_file = _find_downloaded_file(task_id)

        if not downloaded_file or not os.path.exists(downloaded_file):
            raise Exception("File failed to download.")

        file_size = os.path.getsize(downloaded_file)
        title = info.get("title", "video")

        if file_size > MAX_FILE_SIZE_BYTES:
            os.remove(downloaded_file)
            await status_msg.edit_text(
                "❌ **Error:** This video is over 2 GB, which is Telegram's absolute maximum."
            )
            return

        # Step 2: Upload to Telegram via MTProto (supports up to 2GB!)
        size_mb = round(file_size / (1024 * 1024), 1)
        await status_msg.edit_text(f"📤 **Uploading to Telegram... ({size_mb} MB)**")

        # Pyrogram's send_video handles large files natively via MTProto
        await message.reply_video(
            video=downloaded_file,
            caption=f"🎬 **{title}**\n📦 {size_mb} MB",
            supports_streaming=True,
        )

        # Delete status message
        await status_msg.delete()

    except Exception as e:
        error_text = f"❌ **Failed to download.**\n\n`{str(e)[:500]}`\n\n*(Make sure the link is public and valid)*"
        await status_msg.edit_text(error_text)

    finally:
        # Cleanup
        try:
            if downloaded_file and os.path.exists(downloaded_file):
                os.remove(downloaded_file)
        except Exception:
            pass


def _download_video(ydl_opts, url):
    """Blocking function to download a video. Runs in executor."""
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=True)


# ──────────────────────────── Render web server dummy ────────────────────────────
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Bot is running in the background!"

def run_bot():
    print("\n🤖 Telegram Video Downloader Bot is starting (Pyrogram MTProto - 2GB support)...")
    bot.run()

# Start the bot in a background thread when Gunicorn loads
bot_thread = threading.Thread(target=run_bot)
bot_thread.daemon = True
bot_thread.start()

if __name__ == "__main__":
    # Local testing
    app.run(host="0.0.0.0", port=5000)
