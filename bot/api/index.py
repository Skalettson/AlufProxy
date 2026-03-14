# Vercel serverless function для webhook
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message
import os
import sys

# Добавляем родительскую директорию в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BOT_TOKEN, ADMIN_IDS, SERVER_DOMAIN, SERVER_PORT, DATABASE_PATH
from database import Database
from handlers.start import create_handlers as create_start_handlers
from handlers.get_key import create_get_key_handlers
from handlers.admin import create_admin_handlers
from keyboards.inline import get_main_menu_keyboard

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()
db = Database(DATABASE_PATH)

# Регистрируем обработчики
dp.include_router(create_start_handlers(db))
dp.include_router(create_get_key_handlers(db, SERVER_DOMAIN, SERVER_PORT))
dp.include_router(create_admin_handlers(db))


@dp.message()
async def echo_handler(message: Message):
    """Эхо-обработчик для неизвестных команд"""
    await message.answer(
        "🤔 Не понимаю эту команду.\n\n"
        "Используйте /start для начала работы или /help для справки.",
        reply_markup=get_main_menu_keyboard()
    )


async def main(request):
    """Обработка webhook запроса от Telegram"""
    try:
        body = await request.json()
        update = asyncio.create_task(dp.feed_webhook_update(bot, body, bot))
        await update
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}
