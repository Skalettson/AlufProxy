"""
AlufProxy Bot для Vercel Serverless Functions
Правильный формат: https://vercel.com/docs/functions/serverless-functions/runtimes/python
"""

import os
import sys
import json
import logging
from typing import Any, Dict

# Добавляем корень проекта в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BOT_TOKEN, DATABASE_PATH, SERVER_DOMAIN, SERVER_PORT, ADMIN_IDS, SUPPORT_ENABLED
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
from aiogram.types import Update

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
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
    success = await setup_webhook()
    
    if success:
        await message.answer("✅ Webhook успешно настроен!")
    else:
        await message.answer("❌ Не удалось настроить webhook.")


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


# === WEBHOOK SETUP ===

async def setup_webhook():
    """Автоматическая установка webhook"""
    try:
        vercel_url = os.getenv("VERCEL_URL")
        if not vercel_url:
            return False
        
        webhook_url = f"https://{vercel_url}/api/webhook"
        webhook_info = await bot.get_webhook_info()
        
        if webhook_info.url == webhook_url:
            return True
        
        await bot.set_webhook(webhook_url)
        logger.info(f"Webhook установлен: {webhook_url}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка настройки webhook: {e}")
        return False


# === Vercel Handler ===

def handler(event, context):
    """
    Vercel Serverless Function Handler
    
    Args:
        event: Dict с данными запроса
        context: Context object
    
    Returns:
        Dict с HTTP response
    """
    try:
        # Получаем метод и тело запроса
        method = event.get('method', 'GET')
        body = event.get('body', '{}')
        
        # Если body строка - парсим JSON
        if isinstance(body, str):
            body = json.loads(body)
        
        # GET - health check
        if method == 'GET':
            vercel_url = os.getenv("VERCEL_URL")
            
            # Автонастройка webhook
            if vercel_url and not hasattr(bot, '_webhook_setup'):
                bot._webhook_setup = True
                import asyncio
                asyncio.run(setup_webhook())
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'ok',
                    'bot': 'AlufProxy Bot',
                    'webhook': f'https://{vercel_url}/api/webhook' if vercel_url else 'N/A'
                })
            }
        
        # POST - обработка webhook от Telegram
        elif method == 'POST':
            # Создаём update
            update = Update(**body)
            
            # Обрабатываем
            import asyncio
            asyncio.run(dp.feed_update(bot, update))
            
            return {
                'statusCode': 200,
                'body': json.dumps({'status': 'ok'})
            }
        
        else:
            return {
                'statusCode': 405,
                'body': json.dumps({'error': 'Method not allowed'})
            }
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'status': 'error', 'message': str(e)})
        }
