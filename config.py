import logging
import os
from pathlib import Path

from starlette.templating import Jinja2Templates

# Логирование ошибок и действий
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEMP_DIR = Path("static/media/temp_files")
TEMP_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory="frontend")

EMAIL_ADDRESS = os.environ.get("EMAIL_USER", "your_email@gmail.com")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASS", "your_app_password")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
