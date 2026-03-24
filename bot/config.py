import os
import random
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
KEY_UPDATE_API_URL = os.getenv("KEY_UPDATE_API_URL", "http://127.0.0.1:8081")
KEY_UPDATE_API_KEY = os.getenv("KEY_UPDATE_API_KEY", "AlufProxy:L3iKh38iFLD1GdCOJaaTmUlx4YNRwqjYKu8znbGFaDEOtpPgdGN7mfeFScRldKXfbxDIKAc1GuJ0mpVLUreowyZZ4LTLv8Nc74ZDzdJ9gRnVj0HwYkdG9Hy92HkllDry05zRtVjaQrSxYKJfMgsVyy65o7OyKkuHGKU8OA8v1dCS4Olz2CjcQngDj7lawB0KpJbb4nzDczPzughV3qC7M7z69uutQ2jTcLMOMkRCxCIAPynZD2BywVneUTwut1QZ")

# VLESS настройки (для генерации ключей)
SERVER_DOMAIN = os.getenv("SERVER_DOMAIN", "alufproxy.ddns.net")
SERVER_PORT = int(os.getenv("SERVER_PORT", "443"))
VLESS_PORT = int(os.getenv("VLESS_PORT", "443"))

# SNI домены для Reality (пул из 100+ доменов)
# Актуально на 16.03.2026
SNI_DOMAINS = {
    # Приоритет 5⭐ - Технологические гиганты
    "priority_5": [
        "www.microsoft.com",
        "microsoft.com",
        "www.apple.com",
        "apple.com",
        "gateway.icloud.com",
        "itunes.apple.com",
        "swcdn.apple.com",
        "www.nvidia.com",
        "www.cisco.com",
        "www.amd.com",
        "www.intel.com",
        "www.ibm.com",
        "www.oracle.com",
        "www.adobe.com",
        "www.sap.com",
    ],
    # Приоритет 4⭐ - Европейские, азиатские, стриминговые
    "priority_4": [
        "www.bbc.co.uk",
        "www.theguardian.com",
        "www.spiegel.de",
        "www.lemonde.fr",
        "www.nhk.or.jp",
        "www.netflix.com",
        "www.spotify.com",
        "www.telegram.org",
        "www.whatsapp.com",
        "www.linkedin.com",
    ],
    # Приоритет 3⭐ - РФ домены, e-commerce, финансовые
    "priority_3": [
        "www.gosuslugi.ru",
        "gosuslugi.ru",
        "www.sberbank.ru",
        "sberbank.ru",
        "www.vtb.ru",
        "vtb.ru",
        "www.tinkoff.ru",
        "www.yandex.ru",
        "yandex.ru",
        "www.mail.ru",
        "www.vk.com",
        "www.wildberries.ru",
        "www.ozon.ru",
        "www.amazon.com",
        "www.visa.com",
        "www.mastercard.com",
    ],
}

# Домены для быстрой проверки
QUICK_CHECK_DOMAINS = [
    "www.microsoft.com",
    "www.apple.com",
    "gateway.icloud.com",
    "www.nvidia.com",
    "www.netflix.com",
    "www.gosuslugi.ru",
    "www.sberbank.ru",
    "www.yandex.ru",
    "www.wikipedia.org",
    "www.telegram.org",
]

# Получение случайного SNI из пула
def get_random_sni(priority: str = "priority_5") -> str:
    """
    Получить случайный SNI домен из пула.
    
    Args:
        priority: Приоритет ("priority_5", "priority_4", "priority_3")
        
    Returns:
        Случайный домен
    """
    domains = SNI_DOMAINS.get(priority, SNI_DOMAINS["priority_5"])
    return random.choice(domains)


# Получение всех доменов плоским списком
def get_all_sni_domains() -> list:
    """
    Получить все SNI домены плоским списком.
    
    Returns:
        Список всех доменов
    """
    domains = []
    for domain_list in SNI_DOMAINS.values():
        domains.extend(domain_list)
    return domains


# Текущий SNI (выбирается случайно при старте)
VLESS_SNI = os.getenv("VLESS_SNI", get_random_sni("priority_5"))
FALLBACK_DOMAIN = os.getenv("FALLBACK_DOMAIN", get_random_sni("priority_5"))

# Тарифы
TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "7"))
DEFAULT_SUBSCRIPTION_DAYS = int(os.getenv("DEFAULT_SUBSCRIPTION_DAYS", "30"))

# Цены на подписку (рубли)
SUBSCRIPTION_PRICES = {
    1: 189,      # 1 месяц
    3: 519,      # 3 месяца
    6: 1029,     # 6 месяцев
    12: 2049     # 1 год (12 месяцев)
}

# Реквизиты для оплаты
PAYMENT_DETAILS = {
    "sbp_card": "5536 9141 7637 4159",
    "account_number": "40817810400023681780",
    "description": "Оплата подписки AlufProxy"
}

# Поддержка
SUPPORT_ENABLED = os.getenv("SUPPORT_ENABLED", "true").lower() == "true"

# Vercel
VERCEL_URL = os.getenv("VERCEL_URL", "")
