"""Settings for the whole app. Flask loads every UPPERCASE name here into app.config."""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Set the SECRET_KEY environment variable on a real server; the fallback is for local demos only.
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
DATABASE = os.path.join(BASE_DIR, "database.db")

TAX_RATE = 0.15                  # 15% VAT, confirmed by the team

# Driver's licence uploads (FR-03). Kept outside static/ so they are not public.
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}

# Vehicle photos uploaded by an administrator (stored in static/, so they are public).
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

MAX_CONTENT_LENGTH = 5 * 1024 * 1024     # reject uploads over 5 MB
