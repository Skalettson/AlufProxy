import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/bot.db")

# Server API (для генерации ключей)
SERVER_API_URL = os.getenv("SERVER_API_URL", "")
SERVER_API_KEY = os.getenv("SERVER_API_KEY", "")

# VLESS настройки
VLESS_PORT = int(os.getenv("VLESS_PORT", "443"))
VLESS_DOMAIN = os.getenv("VLESS_DOMAIN", "")
VLESS_SNI = os.getenv("VLESS_SNI", "gosuslugi.ru")
FALLBACK_DOMAIN = os.getenv("FALLBACK_DOMAIN", "gosuslugi.ru")

# Тарифы
TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "3"))
DEFAULT_SUBSCRIPTION_DAYS = int(os.getenv("DEFAULT_SUBSCRIPTION_DAYS", "30"))
