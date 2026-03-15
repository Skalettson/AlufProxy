from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from datetime import datetime
import logging

from config import BOT_TOKEN, TRIAL_DAYS, ADMIN_IDS, SUPPORT_ENABLED
from database import Database
from keyboards.inline import get_start_keyboard, get_main_menu_keyboard, get_admin_keyboard, get_support_keyboard

logger = logging.getLogger(__name__)


def create_handlers(db: Database):
    """Создание обработчиков с передачей БД"""
    router = Router()
    
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
        
        # Выход из режима поддержки при старте
        db.set_support_mode(user_id, False)
        
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
            reply_markup=get_start_keyboard(),
            parse_mode="Markdown"
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
            "📧 **Поддержка:** @a_skale"
        )
        
        await message.answer(help_text, parse_mode="Markdown")

    @router.message(Command("support"))
    async def cmd_support(message: Message):
        """Обработчик команды /support"""
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"
        
        if not SUPPORT_ENABLED:
            await message.answer("❌ Поддержка временно недоступна.")
            return
        
        # Проверяем, есть ли открытое обращение
        ticket = db.get_user_open_ticket(user_id)
        
        if ticket:
            await message.answer(
                f"📞 **У вас уже есть открытое обращение #{ticket['id']}**\n\n"
                "Напишите ваше сообщение, и оно будет доставлено администратору.",
                parse_mode="Markdown"
            )
            # Включаем режим поддержки
            db.set_support_mode(user_id, True)
        else:
            await message.answer(
                "📞 **Поддержка AlufProxy**\n\n"
                "Опишите вашу проблему, и администратор свяжется с вами.\n\n"
                "✍️ Напишите сообщение прямо сейчас.",
                parse_mode="Markdown"
            )
            # Включаем режим поддержки
            db.set_support_mode(user_id, True)

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
