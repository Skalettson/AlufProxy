"""
AlufProxy Bot - Railway Version
Запускается через polling (нет проблем с webhook)
"""

import os
import sys
import asyncio
import logging

# Добавляем корень проекта в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    BOT_TOKEN, DATABASE_PATH, SERVER_DOMAIN, 
    SERVER_PORT, ADMIN_IDS, SUPPORT_ENABLED
)
from database import Database
from handlers.start import create_handlers as create_start_handlers
from handlers.get_key import create_get_key_handlers
from handlers.support import create_support_handlers, create_admin_support_handlers
from keyboards.inline import get_main_menu_keyboard

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

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
dp.include_router(create_support_handlers(db))
dp.include_router(create_admin_support_handlers(db))


# === ОБРАБОТЧИКИ ===

@dp.message(F.text)
async def handle_admin_reply(message: Message):
    """Обработка ответов админа на обращения"""
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        return
    
    if hasattr(bot, '_reply_context') and user_id in bot._reply_context:
        ticket_id = bot._reply_context[user_id]
        ticket = db.get_ticket(ticket_id)
        
        if ticket and message.text:
            db.add_support_message(ticket_id, user_id, message.text, is_from_admin=True)
            
            try:
                await message.bot.send_message(
                    ticket['user_id'],
                    f"📬 **Ответ от поддержки (обращение #{ticket_id})**\n\n{message.text}",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Не удалось отправить ответ: {e}")
            
            await message.answer(
                "✅ Сообщение отправлено пользователю\n\n"
                "Продолжайте писать для отправки дополнительных сообщений.\n"
                "Или напишите /cancel для выхода из режима ответа."
            )
            return
        
        if hasattr(bot, '_reply_context'):
            del bot._reply_context[user_id]


@dp.message(Command("cancel"))
async def cmd_cancel(message: Message):
    """Выход из режима ответа"""
    user_id = message.from_user.id
    
    if hasattr(bot, '_reply_context') and user_id in bot._reply_context:
        del bot._reply_context[user_id]
        await message.answer("✅ Выход из режима ответа")


@dp.message(Command("setup_webhook"))
async def cmd_setup_webhook(message: Message):
    """Ручная установка webhook (для админов)"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    await message.answer("⏳ Настройка webhook...")
    await message.answer("ℹ️ Бот работает в режиме polling. Webhook не требуется.")


@dp.message()
async def echo_handler(message: Message):
    """Эхо-обработчик"""
    user_id = message.from_user.id
    
    if db.is_in_support_mode(user_id):
        return
    
    await message.answer(
        "🤔 Не понимаю эту команду.\n\n"
        "Используйте /start для начала работы или /help для справки.",
        reply_markup=get_main_menu_keyboard()
    )


# === ЗАПУСК ===

async def on_startup():
    """При запуске"""
    logger.info("AlufProxy Bot запускается...")
    logger.info(f"Режим: Polling")
    logger.info(f"Поддержка: {'включена' if SUPPORT_ENABLED else 'выключена'}")


async def on_shutdown():
    """При остановке"""
    logger.info("AlufProxy Bot останавливается...")
    await bot.session.close()


async def main():
    """Основной цикл"""
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Запускаем polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    logger.info("Запуск бота через polling...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
