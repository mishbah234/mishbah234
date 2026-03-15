# ──────────────────────────────────────────────────────────────
# PythonAnywhere WSGI Configuration
# ──────────────────────────────────────────────────────────────
# Copy the contents below into your WSGI configuration file on
# PythonAnywhere (Web tab → WSGI configuration file → edit).
#
# Replace /home/YOUR_USERNAME with your actual PythonAnywhere
# home directory path.
# ──────────────────────────────────────────────────────────────

import sys
import os

# ── Update this path to match your project location ──
project_home = '/home/YOUR_USERNAME/youtube-downloader-main'

if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.chdir(project_home)

from app import app as application  # noqa: E402
