from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from datetime import datetime
import logging

from config import ADMIN_IDS
from database import Database
from keyboards.inline import get_admin_keyboard, get_back_keyboard

logger = logging.getLogger(__name__)


def create_admin_handlers(db: Database):
    """Создание админ-обработчиков"""
    router = Router()

    def is_admin(user_id: int) -> bool:
        return user_id in ADMIN_IDS

    @router.callback_query(F.data == "admin_stats")
    async def callback_admin_stats(callback: CallbackQuery):
        """Показ статистики"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещён", show_alert=True)
            return
        
        stats = db.get_stats()
        
        stats_text = (
            "📊 **Статистика AlufProxy**\n\n"
            f"👥 **Пользователи:**\n"
            f"   Всего: {stats['total_users']}\n"
            f"   Активные: {stats['active_users']}\n"
            f"   Забанены: {stats['banned_users']}\n\n"
            f"🔑 **Ключи:**\n"
            f"   Всего: {stats['total_keys']}\n"
            f"   Активные: {stats['active_keys']}\n\n"
            f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        
        await callback.message.answer(
            stats_text,
            reply_markup=get_back_keyboard()
        )
        
        await callback.answer()

    @router.callback_query(F.data == "admin_users")
    async def callback_admin_users(callback: CallbackQuery):
        """Список пользователей"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещён", show_alert=True)
            return
        
        users = db.get_all_users()[:20]  # Первые 20
        
        users_text = "👥 **Пользователи (последние 20):**\n\n"
        
        for user in users:
            user_id = user['id']
            username = user.get('username', 'N/A')
            registered = datetime.fromisoformat(user['registered_at'])
            is_banned = user.get('is_banned', 0)
            sub_end_str = user.get('subscription_end', 'N/A')
            
            if sub_end_str and sub_end_str != 'N/A':
                try:
                    sub_end = datetime.fromisoformat(sub_end_str)
                    days_left = (sub_end - datetime.now()).days
                    sub_status = f"{days_left} дн." if days_left > 0 else "❌ Истек"
                except:
                    sub_status = "N/A"
            else:
                sub_status = "N/A"
            
            ban_status = "🚫" if is_banned else "✅"
            
            users_text += (
                f"{ban_status} `{user_id}` | @{username}\n"
                f"   Рег: {registered.strftime('%d.%m.%Y')}\n"
                f"   Подписка: {sub_status}\n\n"
            )
        
        await callback.message.answer(
            users_text,
            reply_markup=get_back_keyboard()
        )
        
        await callback.answer()

    @router.callback_query(F.data == "admin_keys")
    async def callback_admin_keys(callback: CallbackQuery):
        """Управление ключами"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещён", show_alert=True)
            return
        
        await callback.message.answer(
            "🔑 **Управление ключами**\n\n"
            "Функционал в разработке...\n\n"
            "Планируется:\n"
            "• Просмотр всех ключей\n"
            "• Деактивация ключей\n"
            "• Принудительное продление",
            reply_markup=get_back_keyboard()
        )
        
        await callback.answer()

    @router.callback_query(F.data == "admin_broadcast")
    async def callback_admin_broadcast(callback: CallbackQuery):
        """Рассылка сообщений"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещён", show_alert=True)
            return
        
        await callback.message.answer(
            "📢 **Рассылка сообщений**\n\n"
            "Функционал в разработке...\n\n"
            "Планируется:\n"
            "• Отправка сообщения всем пользователям\n"
            "• Отправка по ID пользователя",
            reply_markup=get_back_keyboard()
        )
        
        await callback.answer()

    @router.message(Command("add_time"))
    async def cmd_add_time(message: Message):
        """Добавление времени к подписке"""
        if not is_admin(message.from_user.id):
            return
        
        # Парсим команду: /add_time <user_id> <days>
        args = message.text.split()
        
        if len(args) != 3:
            await message.answer(
                "❌ Неверный формат команды.\n\n"
                "Используйте: `/add_time <user_id> <days>`\n"
                "Пример: `/add_time 123456789 30`"
            )
            return
        
        try:
            user_id = int(args[1])
            days = int(args[2])
        except ValueError:
            await message.answer("❌ user_id и days должны быть числами")
            return
        
        # Продлеваем подписку
        if db.extend_subscription(user_id, days):
            await message.answer(
                f"✅ Подписка пользователя `{user_id}` продлена на {days} дн."
            )
        else:
            await message.answer(f"❌ Не удалось продлить подписку. Пользователь `{user_id}` не найден.")

    @router.message(Command("ban"))
    async def cmd_ban(message: Message):
        """Бан пользователя"""
        if not is_admin(message.from_user.id):
            return
        
        args = message.text.split()
        
        if len(args) != 2:
            await message.answer(
                "❌ Неверный формат команды.\n\n"
                "Используйте: `/ban <user_id>`\n"
                "Пример: `/ban 123456789`"
            )
            return
        
        try:
            user_id = int(args[1])
        except ValueError:
            await message.answer("❌ user_id должен быть числом")
            return
        
        if db.ban_user(user_id):
            await message.answer(f"✅ Пользователь `{user_id}` забанен.")
        else:
            await message.answer(f"❌ Не удалось забанить пользователя `{user_id}`.")

    @router.message(Command("unban"))
    async def cmd_unban(message: Message):
        """Разбан пользователя"""
        if not is_admin(message.from_user.id):
            return
        
        args = message.text.split()
        
        if len(args) != 2:
            await message.answer(
                "❌ Неверный формат команды.\n\n"
                "Используйте: `/unban <user_id>`\n"
                "Пример: `/unban 123456789`"
            )
            return
        
        try:
            user_id = int(args[1])
        except ValueError:
            await message.answer("❌ user_id должен быть числом")
            return
        
        if db.unban_user(user_id):
            await message.answer(f"✅ Пользователь `{user_id}` разбанен.")
        else:
            await message.answer(f"❌ Не удалось разбанить пользователя `{user_id}`.")

    return router
