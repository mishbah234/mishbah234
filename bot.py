import os
import re
import uuid
import glob
import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
import yt_dlp

# ──────────────────────────── config ────────────────────────────
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
API_ID = int(os.environ.get("API_ID", "24223583"))
API_HASH = os.environ.get("API_HASH", "8601a6f42f20a392f241bd33b8bf6b10")

if not BOT_TOKEN:
    print("❌ ERROR: TELEGRAM_BOT_TOKEN is missing!")
    exit(1)

bot = Client(
    "video_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True,
)

MAX_FILE_SIZE_BYTES = 2_000_000_000

# Store pending downloads: {user_id: {url, info, ...}}
pending_downloads = {}

# ──────────────────────────── helpers ────────────────────────────
def _safe_filename(title):
    name = re.sub(r'[^\w\s\-]', '', title).strip()
    return name[:120] or "video"


def _find_downloaded_file(task_id):
    matches = glob.glob(f"download_{task_id}_*")
    return matches[0] if matches else None


def _format_duration(seconds):
    if not seconds:
        return "Unknown"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    return f"{m}m {s}s"


def _format_size(bytes_count):
    if not bytes_count:
        return "Unknown"
    if bytes_count > 1_000_000_000:
        return f"{bytes_count / 1_000_000_000:.1f} GB"
    return f"{bytes_count / 1_000_000:.1f} MB"


def _progress_bar(current, total, length=12):
    filled = int(length * current / total) if total else 0
    bar = "█" * filled + "░" * (length - filled)
    pct = (current / total * 100) if total else 0
    return f"[{bar}] {pct:.0f}%"


# ──────────────────────────── /start ────────────────────────────

WELCOME_TEXT = """
🎬 **Video Downloader Bot** 🎬

━━━━━━━━━━━━━━━━━━━━━

🌟 **What I can do:**
├ 📥 Download YouTube videos
├ 📥 Download Instagram reels/posts
├ 🎵 Extract audio (MP3)
├ 📊 Choose quality (360p → 4K)
└ 📦 Files up to **2 GB**!

━━━━━━━━━━━━━━━━━━━━━

💡 **How to use:**
Just send me a video link!

━━━━━━━━━━━━━━━━━━━━━
"""

@bot.on_message(filters.command(["start", "help"]))
async def send_welcome(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Channel", url="https://t.me/mishbah234"),
         InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/mishbah234")],
        [InlineKeyboardButton("❓ How to use", callback_data="how_to_use")],
    ])
    await message.reply_text(WELCOME_TEXT, reply_markup=keyboard)


@bot.on_callback_query(filters.regex("how_to_use"))
async def how_to_use_callback(client: Client, callback: CallbackQuery):
    text = """
🔰 **How to Use This Bot** 🔰

1️⃣ Copy a video link from YouTube or Instagram
2️⃣ Paste it here in the chat
3️⃣ I'll show you the video info with quality options
4️⃣ Tap a quality button to start downloading
5️⃣ Sit back and watch the magic happen! ✨

⚡ **Supported Links:**
├ 🔴 YouTube videos & shorts
├ 📸 Instagram reels & posts
└ 🌐 Many other sites!
"""
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
    ]))
    await callback.answer()


@bot.on_callback_query(filters.regex("back_to_start"))
async def back_to_start(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Channel", url="https://t.me/mishbah234"),
         InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/mishbah234")],
        [InlineKeyboardButton("❓ How to use", callback_data="how_to_use")],
    ])
    await callback.message.edit_text(WELCOME_TEXT, reply_markup=keyboard)
    await callback.answer()


# ──────────────────────────── URL handler ────────────────────────────

@bot.on_message(filters.text & filters.private)
async def handle_message(client: Client, message: Message):
    url = message.text.strip()

    if not url.startswith("http://") and not url.startswith("https://"):
        await message.reply_text("⚠️ That doesn't look like a valid URL.\n\nSend me a YouTube or Instagram link!")
        return

    # Show animated extracting message
    status_msg = await message.reply_text("🔍 **Analyzing link...**")

    # Animate the dots
    animations = [
        "🔍 **Analyzing link.**",
        "🔍 **Analyzing link..**",
        "🔍 **Analyzing link...**",
        "🎯 **Fetching video info...**",
    ]
    for anim in animations:
        try:
            await status_msg.edit_text(anim)
            await asyncio.sleep(0.4)
        except Exception:
            pass

    # Extract info (no download yet)
    ydl_opts = {
        "format": "best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android_vr", "ios", "tv", "web"],
                "player_skip": ["webpage", "configs"]
            }
        }
    }
    if os.path.exists("cookies.txt"):
        ydl_opts["cookiefile"] = "cookies.txt"

    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: _extract_info(ydl_opts, url))

        title = info.get("title", "Unknown")
        duration = _format_duration(info.get("duration"))
        thumbnail = info.get("thumbnail", "")
        uploader = info.get("uploader", "Unknown")
        view_count = info.get("view_count")
        views_str = f"{view_count:,}" if view_count else "N/A"

        # Store for later use
        user_id = message.from_user.id
        pending_downloads[user_id] = {"url": url, "title": title}

        # Build a beautiful info card
        info_text = f"""
✅ **Video Found!**

━━━━━━━━━━━━━━━━━━━━━

🎬 **Title:** {title}
👤 **Channel:** {uploader}
⏱ **Duration:** {duration}
👁 **Views:** {views_str}

━━━━━━━━━━━━━━━━━━━━━

🎯 **Select quality below:**
"""

        # Quality selection buttons
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📱 360p", callback_data=f"dl_360_{user_id}"),
                InlineKeyboardButton("💻 480p", callback_data=f"dl_480_{user_id}"),
            ],
            [
                InlineKeyboardButton("📺 720p HD", callback_data=f"dl_720_{user_id}"),
                InlineKeyboardButton("🖥 1080p FHD", callback_data=f"dl_1080_{user_id}"),
            ],
            [
                InlineKeyboardButton("🎵 Audio Only (MP3)", callback_data=f"dl_audio_{user_id}"),
            ],
            [
                InlineKeyboardButton("🏆 Best Quality", callback_data=f"dl_best_{user_id}"),
            ],
            [
                InlineKeyboardButton("❌ Cancel", callback_data=f"dl_cancel_{user_id}"),
            ],
        ])

        await status_msg.edit_text(info_text, reply_markup=keyboard)

    except Exception as e:
        await status_msg.edit_text(
            f"❌ **Failed to extract video info**\n\n`{str(e)[:300]}`\n\n💡 Make sure the link is valid and public."
        )


def _extract_info(ydl_opts, url):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


# ──────────────────────────── Quality button callbacks ────────────────────────────

@bot.on_callback_query(filters.regex(r"^dl_"))
async def download_callback(client: Client, callback: CallbackQuery):
    data = callback.data
    parts = data.split("_")
    quality = parts[1]
    user_id = int(parts[2])

    # Check if this is the right user
    if callback.from_user.id != user_id:
        await callback.answer("⚠️ This button is not for you!", show_alert=True)
        return

    # Handle cancel
    if quality == "cancel":
        pending_downloads.pop(user_id, None)
        await callback.message.edit_text("❌ **Download cancelled.**")
        await callback.answer()
        return

    # Get stored data
    download_info = pending_downloads.pop(user_id, None)
    if not download_info:
        await callback.answer("⚠️ Session expired! Send the link again.", show_alert=True)
        return

    url = download_info["url"]
    title = download_info["title"]

    await callback.answer("🚀 Starting download...")

    # Build format string based on quality
    if quality == "audio":
        fmt = "bestaudio[ext=m4a]/bestaudio"
        is_audio = True
    elif quality == "best":
        fmt = "best[ext=mp4]/best"
        is_audio = False
    else:
        height = quality
        fmt = f"best[height<={height}][ext=mp4]/best[height<={height}]/best[ext=mp4]/best"
        is_audio = False

    # Show download animation
    await callback.message.edit_text(
        f"🚀 **Starting download...**\n\n"
        f"🎬 {title}\n"
        f"📊 Quality: **{quality.upper() if quality != 'audio' else '🎵 Audio MP3'}**\n\n"
        f"{_progress_bar(0, 100)}\n\n"
        f"⏳ Please wait..."
    )

    task_id = uuid.uuid4().hex[:8]
    output_template = f"download_{task_id}_%(title)s.%(ext)s"

    ydl_opts = {
        "format": fmt,
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4" if not is_audio else None,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}] if is_audio else [],
        "extractor_args": {
            "youtube": {
                "player_client": ["android_vr", "ios", "tv", "web"],
                "player_skip": ["webpage", "configs"]
            }
        }
    }
    if os.path.exists("cookies.txt"):
        ydl_opts["cookiefile"] = "cookies.txt"

    # Remove None values
    ydl_opts = {k: v for k, v in ydl_opts.items() if v is not None}

    downloaded_file = None
    try:
        # Animate download progress
        progress_steps = [
            ("⬇️ **Downloading from server...**", 20),
            ("⬇️ **Downloading...**", 40),
            ("⬇️ **Almost there...**", 60),
            ("🔄 **Processing video...**", 80),
        ]

        # Start actual download in background
        loop = asyncio.get_event_loop()
        download_task = loop.run_in_executor(None, lambda: _download_video(ydl_opts, url))

        # Animate while downloading
        for step_text, progress in progress_steps:
            try:
                await callback.message.edit_text(
                    f"{step_text}\n\n"
                    f"🎬 {title}\n\n"
                    f"{_progress_bar(progress, 100)}\n\n"
                    f"⏳ Please wait..."
                )
            except Exception:
                pass
            await asyncio.sleep(2)

        # Wait for download to finish
        info = await download_task

        # Find file
        downloaded_file = _find_downloaded_file(task_id)
        if not downloaded_file or not os.path.exists(downloaded_file):
            raise Exception("Download failed — file not found.")

        file_size = os.path.getsize(downloaded_file)

        if file_size > MAX_FILE_SIZE_BYTES:
            os.remove(downloaded_file)
            await callback.message.edit_text(
                "❌ **File too large!**\n\n"
                "Telegram's absolute limit is 2 GB.\n"
                "Try selecting a lower quality."
            )
            return

        size_str = _format_size(file_size)

        # Upload animation
        await callback.message.edit_text(
            f"📤 **Uploading to Telegram...**\n\n"
            f"🎬 {title}\n"
            f"📦 Size: **{size_str}**\n\n"
            f"{_progress_bar(90, 100)}\n\n"
            f"⏳ Almost done..."
        )

        # Upload
        if is_audio:
            await callback.message.reply_audio(
                audio=downloaded_file,
                caption=f"🎵 **{title}**\n📦 {size_str}",
            )
        else:
            await callback.message.reply_video(
                video=downloaded_file,
                caption=f"🎬 **{title}**\n📦 {size_str}",
                supports_streaming=True,
            )

        # Final success message
        await callback.message.edit_text(
            f"✅ **Download Complete!**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎬 **{title}**\n"
            f"📊 Quality: **{quality.upper() if quality != 'audio' else '🎵 MP3'}**\n"
            f"📦 Size: **{size_str}**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔗 Send another link to download more!"
        )

    except Exception as e:
        await callback.message.edit_text(
            f"❌ **Download Failed**\n\n"
            f"`{str(e)[:400]}`\n\n"
            f"💡 Try a different quality or check the link."
        )

    finally:
        try:
            if downloaded_file and os.path.exists(downloaded_file):
                os.remove(downloaded_file)
        except Exception:
            pass


def _download_video(ydl_opts, url):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=True)


# ──────────────────────────── Render web server dummy ────────────────────────────
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Bot is running!"

def run_bot():
    print("\n🤖 Telegram Video Downloader Bot is starting (2GB MTProto)...")
    bot.run()

bot_thread = threading.Thread(target=run_bot)
bot_thread.daemon = True
bot_thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
