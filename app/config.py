import logging
import os
import sys
from dotenv import load_dotenv

# Настройка логирования в терминал (без эмодзи для совместимости с Windows)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger("vacancy_bot")
logger.setLevel(logging.INFO)

load_dotenv()

# Настройки из .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
KILO_AUTO_API_KEY = os.getenv("KILO_AUTO_API_KEY")
KILO_AUTO_API_URL = os.getenv("KILO_AUTO_API_URL")
KILO_AUTO_MODEL = os.getenv("KILO_AUTO_MODEL", "kilo-auto")
SUBSCRIPTION_POLL_SECONDS = int(os.getenv("SUBSCRIPTION_POLL_SECONDS", 900))
SJ_API_KEY = os.getenv("SJ_API_KEY")
HABR_API_URL = os.getenv("HABR_API_URL", "https://career.habr.com/api/v1/vacancies")
HABR_API_TOKEN = os.getenv("HABR_API_TOKEN")
AGGREGATOR_API_URL = os.getenv("AGGREGATOR_API_URL")
AGGREGATOR_API_TOKEN = os.getenv("AGGREGATOR_API_TOKEN")
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", 8080))
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", f"http://{WEB_HOST}:{WEB_PORT}")
LIST_PAGE_SIZE = int(os.getenv("LIST_PAGE_SIZE", 10))
LIST_MAX_AGE_HOURS = int(os.getenv("LIST_MAX_AGE_HOURS", 24))

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "vacancy_bot"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASS")
}

HH_API = "https://api.hh.ru/vacancies"
SJ_API = "https://api.superjob.ru/2.0/vacancies/"
HEADERS = {"User-Agent": "VacancyBotPro/1.0"}
SJ_HEADERS = {"User-Agent": "VacancyBotPro/1.0", "X-Api-App-Id": SJ_API_KEY} if SJ_API_KEY else HEADERS
