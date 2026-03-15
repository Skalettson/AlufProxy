"""
AlufProxy Telegram Bot
Хостинг: Vercel Serverless Functions
"""

import os
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
import json

from config import (
    BOT_TOKEN, ADMIN_IDS, DATABASE_PATH, 
    SERVER_DOMAIN, SERVER_PORT, SUPPORT_ENABLED
)
from database import Database
from handlers.start import create_handlers as create_start_handlers
from handlers.get_key import create_get_key_handlers
from handlers.support import create_support_handlers, create_admin_support_handlers
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

# Инициализация базы данных
db = Database(DATABASE_PATH)

# Регистрируем обработчики
dp.include_router(create_start_handlers(db))
dp.include_router(create_get_key_handlers(db, SERVER_DOMAIN, SERVER_PORT))
dp.include_router(create_support_handlers(db))
dp.include_router(create_admin_support_handlers(db))


# Обработчик для режима поддержки админа
@dp.message(F.text)
async def handle_admin_reply(message: Message):
    """Обработка ответов админа на обращения"""
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        return
    
    # Проверяем, есть ли контекст ответа
    if hasattr(bot, '_reply_context') and user_id in bot._reply_context:
        ticket_id = bot._reply_context[user_id]
        ticket = db.get_ticket(ticket_id)
        
        if ticket and message.text:
            # Добавляем сообщение от админа
            db.add_support_message(ticket_id, user_id, message.text, is_from_admin=True)
            
            # Отправляем пользователю
            try:
                await message.bot.send_message(
                    ticket['user_id'],
                    f"📬 **Ответ от поддержки (обращение #{ticket_id})**\n\n"
                    f"{message.text}",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Не удалось отправить ответ пользователю: {e}")
            
            await message.answer(
                f"✅ Сообщение отправлено пользователю @{ticket.get('username', 'N/A')}\n\n"
                "Продолжайте писать для отправки дополнительных сообщений.\n"
                "Или напишите /cancel для выхода из режима ответа."
            )
            return
        
        del bot._reply_context[user_id]


@dp.message(Command("cancel"))
async def cmd_cancel(message: Message):
    """Выход из режима ответа"""
    user_id = message.from_user.id
    
    if hasattr(bot, '_reply_context') and user_id in bot._reply_context:
        del bot._reply_context[user_id]
        await message.answer("✅ Выход из режима ответа")


@dp.message()
async def echo_handler(message: Message):
    """Эхо-обработчик для неизвестных команд"""
    user_id = message.from_user.id
    
    # Если пользователь в режиме поддержки - игнорируем (уже обработано)
    if db.is_in_support_mode(user_id):
        return
    
    await message.answer(
        "🤔 Не понимаю эту команду.\n\n"
        "Используйте /start для начала работы или /help для справки.",
        reply_markup=get_main_menu_keyboard()
    )


async def on_startup(bot: Bot):
    """Хук при запуске бота"""
    logger.info("Бот запущен!")


async def on_shutdown(bot: Bot):
    """Хук при остановке бота"""
    logger.info("Бот остановлен!")


# Для локального запуска (polling)
async def main():
    """Запуск бота в режиме polling (локально)"""
    await bot.delete_webhook()
    await dp.start_polling(bot)


# Точка входа для Vercel
async def webhook_handler(request):
    """Обработка webhook запроса от Telegram"""
    try:
        body = await request.json()
        update = asyncio.create_task(dp.feed_webhook_update(bot, body, bot))
        await update
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}


# Экспорт для Vercel
if os.getenv("VERCEL"):
    import asyncio
    from aiohttp import web
    
    def create_app():
        """Создание веб-приложения для Vercel"""
        app = web.Application()
        
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)
        
        from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
        SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/api/webhook")
        setup_application(app, dp, bot=bot)
        
        return app
