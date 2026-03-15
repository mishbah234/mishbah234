"""
YouTube Video Downloader — Flask Web App (PythonAnywhere-compatible)
=====================================================================
Streams video directly to the user's browser — NO files saved on server.

Architecture:
    1. /api/extract  → extracts video info (title, thumbnail) using yt-dlp
    2. /api/stream/… → pipes yt-dlp output directly to the browser download

Deployment on PythonAnywhere:
    1. Upload this project folder
    2. pip install --user flask yt-dlp
    3. Create Web App → Manual config → Python 3.x
    4. WSGI: from app import app as application
    5. Static files:  /static/ → /home/<user>/youtube-downloader-main/static

Local:
    pip install -r requirements.txt
    python app.py → http://127.0.0.1:5000
"""

import os
import sys
import uuid
import subprocess
import re
from flask import Flask, render_template, request, jsonify, Response, stream_with_context

app = Flask(__name__)

# ──────────────────────────── config ────────────────────────────

QUALITY_MAP = {
    "2160": {"label": "4K  (2160p)", "height": 2160},
    "1440": {"label": "2K  (1440p)", "height": 1440},
    "1080": {"label": "FHD (1080p)", "height": 1080},
    "720":  {"label": "HD  (720p)",  "height": 720},
    "best": {"label": "Best available", "height": None},
}

# Lightweight store for extracted video info  { task_id: { url, title, format, ... } }
extractions = {}


def _safe_filename(title):
    """Sanitise a video title for use as a download filename."""
    name = re.sub(r'[^\w\s\-]', '', title).strip()
    return name[:120] or "video"


def _build_format(quality):
    """Build a yt-dlp format string for the requested quality."""
    chosen = QUALITY_MAP.get(quality, QUALITY_MAP["best"])
    height = chosen["height"]
    if height:
        return (
            f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={height}]+bestaudio/"
            f"best[height<={height}]/"
            f"best"
        )
    return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"


# ──────────────────────────── routes ────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", qualities=QUALITY_MAP)


@app.route("/api/extract", methods=["POST"])
def api_extract():
    """Extract direct download URL using yt-dlp. No server processing."""
    import yt_dlp

    data = request.get_json(force=True)
    video_url = data.get("url", "").strip()
    quality = data.get("quality", "best")

    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    # For direct links, we must ensure it has BOTH video and audio together
    # because browsers can't merge separate streams on the fly.
    chosen = QUALITY_MAP.get(quality, QUALITY_MAP["best"])
    height = chosen["height"]
    
    if height:
        fmt = f"best[height<={height}][ext=mp4]/best[ext=mp4]/best"
    else:
        fmt = "best[ext=mp4]/best"

    ydl_opts = {
        "format": fmt,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "cookiefile": "cookies.txt",  
        # IN 2024, YOUTUBE BLOCKS THE DEFAULT WEB AND ANDROID CLIENTS ON CLOUD IPS.
        # We must spoof older clients or TV clients that don't enforce the 'po_token' bot checks yet.
        "extractor_args": {
            "youtube": {
                "player_client": ["android_vr", "ios", "tv", "web"], 
                "player_skip": ["webpage", "configs"]
            }
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            # The direct URL to Google's video servers
            direct_url = info.get("url")
            if not direct_url:
                raise Exception("Could not extract a direct download URL.")

            title = info.get("title", "video")
            # We add a filename parameter to the URL to try and force a nice download name if possible
            safe_title = _safe_filename(title)
            if "?" in direct_url:
                direct_url += f"&title={safe_title}"
            else:
                direct_url += f"?title={safe_title}"

            return jsonify({
                "direct_url": direct_url,
                "title": title,
                "duration": info.get("duration"),
                "thumbnail": info.get("thumbnail"),
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 400


# ──────────────────────────── main ────────────────────────────

if __name__ == "__main__":
    print("\n🎥  YouTube Downloader Web App")
    print("   → Open http://127.0.0.1:5000\n")
    app.run(debug=True, threaded=True, port=5000)
