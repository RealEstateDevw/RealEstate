import logging

from starlette.templating import Jinja2Templates

# Логирование ошибок и действий
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


templates = Jinja2Templates(directory="frontend")

