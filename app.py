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


import imageio_ffmpeg

@app.route("/api/extract", methods=["POST"])
def api_extract():
    """Extract video metadata without downloading. Returns a task_id."""
    import yt_dlp

    data = request.get_json(force=True)
    video_url = data.get("url", "").strip()
    quality = data.get("quality", "best")

    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    fmt = _build_format(quality)

    ydl_opts = {
        "format": fmt,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "cookiefile": "cookies.txt",  
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
            
            title = info.get("title", "video")
            task_id = uuid.uuid4().hex[:12]
            
            # Store everything we need to run the subprocess stream later
            extractions[task_id] = {
                "url": video_url,
                "format": fmt,
                "title": title,
                "duration": info.get("duration"),
                "thumbnail": info.get("thumbnail"),
            }

            return jsonify({
                "task_id": task_id,
                "title": title,
                "duration": info.get("duration"),
                "thumbnail": info.get("thumbnail"),
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 400


@app.route("/api/stream/<task_id>")
def api_stream(task_id):
    """Stream the video directly to the browser via yt-dlp subprocess in MKV format."""
    t = extractions.pop(task_id, None)
    if not t:
        return jsonify({"error": "Session expired or invalid file. Try again."}), 404

    url = t["url"]
    fmt = t["format"]
    title = _safe_filename(t["title"])

    # Path to the portable ffmpeg binary we installed via pip (imageio-ffmpeg)
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    # We must use MKV for streaming.
    # MP4 writes the 'moov' atom at the end of the file, which requires ffmpeg
    # to seek backwards in the file. You cannot seek backwards in a pipestream!
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-f", fmt,
        "--merge-output-format", "mkv",
        "--ffmpeg-location", ffmpeg_exe,
        "-o", "-",              # Output to stdout directly
        "--no-playlist",
        "--retries", "10",
        "--socket-timeout", "120",
        "--quiet",
        "--no-warnings",
        "--cookies", "cookies.txt",
        "--extractor-args", "youtube:player_client=android_vr,ios,tv,web;player_skip=webpage,configs",
        url,
    ]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    def generate():
        try:
            while True:
                chunk = process.stdout.read(65536)  # Read 64 KB at a time
                if not chunk:
                    break
                yield chunk
        finally:
            process.stdout.close()
            process.stderr.close()
            process.wait()

    return Response(
        stream_with_context(generate()),
        mimetype="video/x-matroska",
        headers={
            "Content-Disposition": f'attachment; filename="{title}.mkv"',
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # crucial for fast streaming on platforms like Render
        },
    )


# ──────────────────────────── main ────────────────────────────

if __name__ == "__main__":
    print("\n🎥  YouTube Downloader Web App")
    print("   → Open http://127.0.0.1:5000\n")
    app.run(debug=True, threaded=True, port=5000)
