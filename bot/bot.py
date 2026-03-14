import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
import os

from config import BOT_TOKEN, ADMIN_IDS
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
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SERVER_DOMAIN = os.getenv("SERVER_DOMAIN", "proxy.example.com")
SERVER_PORT = int(os.getenv("SERVER_PORT", "443"))
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/bot.db")

# Создаём бота и диспетчер
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

# Инициализация базы данных
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


async def on_startup(bot: Bot):
    """Хук при запуске бота"""
    logger.info("Бот запущен!")
    await bot.set_webhook(f"https://{os.getenv('VERCEL_URL')}/webhook")


async def on_shutdown(bot: Bot):
    """Хук при остановке бота"""
    logger.info("Бот остановлен!")
    await bot.delete_webhook()


def create_app():
    """Создание веб-приложения для Vercel"""
    app = web.Application()
    
    # Регистрируем хуки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Настраиваем webhook
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
    
    return app


# Для локального запуска (polling)
async def main():
    """Запуск бота в режиме polling (локально)"""
    await bot.delete_webhook()
    await dp.start_polling(bot)


if __name__ == "__main__":
    # Проверяем, запущены ли на Vercel
    if os.getenv("VERCEL"):
        app = create_app()
        web.run_app(app, host="0.0.0.0", port=8000)
    else:
        # Локальный запуск
        logger.info("Запуск бота в режиме polling...")
        asyncio.run(main())
