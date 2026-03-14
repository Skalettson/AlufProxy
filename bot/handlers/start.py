from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from datetime import datetime
import logging

from config import BOT_TOKEN, TRIAL_DAYS, ADMIN_IDS
from database import Database
from keyboards.inline import get_start_keyboard, get_main_menu_keyboard, get_admin_keyboard

logger = logging.getLogger(__name__)

router = Router()


def create_handlers(db: Database):
    """Создание обработчиков с передачей БД"""
    
    @router.message(Command("start"))
    async def cmd_start(message: Message):
        """Обработчик команды /start"""
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"
        first_name = message.from_user.first_name or "User"
        
        # Добавляем пользователя в БД
        db.add_user(user_id, username, first_name)
        
        # Проверяем, забанен ли пользователь
        if db.is_user_banned(user_id):
            await message.answer(
                "❌ Вы заблокированы в системе.\n"
                "Обратитесь к администратору для разблокировки."
            )
            return
        
        # Получаем информацию о подписке
        sub_end = db.get_subscription_end(user_id)
        
        welcome_text = (
            f"👋 Привет, {first_name}!\n\n"
            f"🚀 **AlufProxy** — твой надёжный прокси для обхода блокировок.\n\n"
            f"📡 **Твой статус:**\n"
        )
        
        if sub_end:
            if sub_end > datetime.now():
                days_left = (sub_end - datetime.now()).days
                welcome_text += f"✅ Подписка активна ещё {days_left} дн.\n"
            else:
                welcome_text += "❌ Подписка истекла\n"
        else:
            welcome_text += f"🎁 Пробный период: {TRIAL_DAYS} дн.\n"
        
        welcome_text += (
            "\n🔹 **VLESS Reality** — максимальная защита\n"
            "🔹 **Обход DPI** — трафик как обычный HTTPS\n"
            "🔹 **Быстрое подключение** — работает с Windows, Linux, macOS\n\n"
            "Нажми кнопку ниже, чтобы получить ключ подключения!"
        )
        
        await message.answer(
            welcome_text,
            reply_markup=get_start_keyboard()
        )

    @router.message(Command("help"))
    async def cmd_help(message: Message):
        """Обработчик команды /help"""
        help_text = (
            "📖 **Инструкция по использованию AlufProxy**\n\n"
            "**1. Получение ключа:**\n"
            "Нажми /start или кнопку '🔑 Получить ключ'\n\n"
            "**2. Настройка ПК-клиента:**\n"
            "• Скачай AlufProxy Client для Windows\n"
            "• Вставь полученный ключ в поле подключения\n"
            "• Нажми 'Подключиться'\n\n"
            "**3. Использование с другими клиентами:**\n"
            "Ключ совместим с:\n"
            "• v2rayNG (Android)\n"
            "• Shadowrocket (iOS)\n"
            "• NekoBox (Android)\n"
            "• Hiddify (все платформы)\n\n"
            "**4. Если не работает:**\n"
            "• Проверь дату окончания подписки\n"
            "• Попробуй получить новый ключ\n"
            "• Обратись в поддержку\n\n"
            "📧 **Поддержка:** @aluf_support"
        )
        
        await message.answer(help_text)

    @router.message(Command("admin"))
    async def cmd_admin(message: Message):
        """Обработчик команды /admin"""
        if message.from_user.id not in ADMIN_IDS:
            return
        
        await message.answer(
            "🛠 **Админ-панель AlufProxy**\n\n"
            "Выберите действие:",
            reply_markup=get_admin_keyboard()
        )

    return router
