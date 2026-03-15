import os
import re
import uuid
import telebot
import yt_dlp

# ──────────────────────────── config ────────────────────────────
# Get the token from Environment Variables (set in Render.com Dashboard)
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ ERROR: TELEGRAM_BOT_TOKEN is missing! Please set it in your environment variables.")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# Telegram maximum upload size for bots is 50MB
MAX_FILE_SIZE_BYTES = 49_000_000  # 49 MB just to be safe

# ──────────────────────────── helpers ────────────────────────────
def _safe_filename(title):
    name = re.sub(r'[^\w\s\-]', '', title).strip()
    return name[:120] or "video"

# ──────────────────────────── bot logic ────────────────────────────

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 Welcome to the Video Downloader Bot!\n\n"
        "Send me a link to a **YouTube** or **Instagram** video, and I will download it for you.\n\n"
        "*(Note: Telegram limits bots to 50MB files, so long or 4K videos might be sent in lower quality to fit the limit!)*"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    
    # Very basic URL check
    if not url.startswith("http://") and not url.startswith("https://"):
        bot.reply_to(message, "⚠️ Please send a valid URL starting with http:// or https://")
        return

    # Acknowledge the request
    status_msg = bot.reply_to(message, "⏳ *Extracting video info...*", parse_mode="Markdown")
    
    # Create a unique filename for this download
    task_id = uuid.uuid4().hex[:8]
    output_template = f"download_{task_id}_%(title)s.%(ext)s"

    # Configure yt-dlp to download the best format under 50MB
    # We prioritize mp4, but fallback to anything under 50MB if needed.
    ydl_opts = {
        "format": "best[filesize<50M][ext=mp4]/best[filesize<50M]/worst",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "cookiefile": "cookies.txt",  # Still using cookies to bypass YouTube blocks if they exist
        "extractor_args": {
            "youtube": {
                "player_client": ["android_vr", "ios", "tv", "web"],
                "player_skip": ["webpage", "configs"]
            }
        }
    }

    downloaded_file = None
    try:
        # Step 1: Download the video
        bot.edit_message_text("⏳ *Downloading video... Please wait...*", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Find the actual exact filename that yt-dlp saved it as
            downloaded_file = ydl.prepare_filename(info)

        # Step 2: Check if file exists and is under the 50MB limit
        if not os.path.exists(downloaded_file):
            raise Exception("File failed to download.")
        
        file_size = os.path.getsize(downloaded_file)
        if file_size > MAX_FILE_SIZE_BYTES:
            os.remove(downloaded_file)
            bot.edit_message_text("❌ *Error:* This video is too large for Telegram (Over 50MB).", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")
            return

        # Step 3: Upload to Telegram
        bot.edit_message_text("📤 *Uploading to Telegram...*", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")
        
        with open(downloaded_file, 'rb') as video_data:
            bot.send_video(
                chat_id=message.chat.id,
                video=video_data,
                caption=info.get("title", "Here is your video!"),
                reply_to_message_id=message.message_id
            )
            
        # Delete the status message since we successfully sent the video
        bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)

    except Exception as e:
        error_text = f"❌ *Failed to download.*\n\n`{str(e)[:500]}`\n\n*(Make sure the link is public and valid)*"
        bot.edit_message_text(error_text, chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")
    
    finally:
        # Cleanup: ALWAYS try to delete the file from the server so we don't run out of disk space
        try:
            if downloaded_file and os.path.exists(downloaded_file):
                os.remove(downloaded_file)
        except Exception:
            pass

# ──────────────────────────── main ────────────────────────────
if __name__ == "__main__":
    print("\n🤖 Telegram Video Downloader Bot is running...")
    bot.infinity_polling()
