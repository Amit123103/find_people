"""
ImageFinder Configuration
All settings — no API keys required.
"""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
STATIC_DIR = BASE_DIR / "static"

# Create upload directory
UPLOAD_DIR.mkdir(exist_ok=True)

# Upload settings
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"}

# Server settings
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# Search engine URLs
SEARCH_ENGINES = {
    "google_lens": "https://lens.google.com/uploadbyurl?url=",
    "yandex": "https://yandex.com/images/search?rpt=imageview&url=",
    "bing": "https://www.bing.com/images/search?view=detailv2&iss=sbi&form=SBIVSP&sbisrc=UrlPaste&q=imgurl:",
    "tineye": "https://tineye.com/search?url=",
}
