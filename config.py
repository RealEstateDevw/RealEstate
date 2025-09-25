import logging
from pathlib import Path
from starlette.templating import Jinja2Templates
from settings import settings

# Логирование ошибок и действий
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TEMP_DIR = Path("static/media/temp_files")
TEMP_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory="frontend")

# Email settings from environment
EMAIL_ADDRESS = settings.EMAIL_USER
EMAIL_PASSWORD = settings.EMAIL_PASS
SMTP_SERVER = settings.SMTP_SERVER
SMTP_PORT = settings.SMTP_PORT
