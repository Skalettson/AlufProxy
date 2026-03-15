from aiogram import Router, F, types
from aiogram.types import CallbackQuery, Message
from datetime import datetime, timedelta
import logging
import asyncio

from config import ADMIN_IDS, DEFAULT_SUBSCRIPTION_DAYS
from database import Database
from utils.key_generator import generate_full_config
from keyboards.inline import get_key_actions_keyboard, get_main_menu_keyboard, get_back_keyboard

logger = logging.getLogger(__name__)


def create_get_key_handlers(db: Database, server_domain: str, server_port: int):
    """Создание обработчиков для получения ключей"""
    router = Router()

    @router.callback_query(F.data == "get_key")
    async def callback_get_key(callback: CallbackQuery):
        """Обработчик запроса нового ключа"""
        user_id = callback.from_user.id
        
        # Проверяем пользователя
        user = db.get_user(user_id)
        if not user:
            await callback.answer("❌ Вы не зарегистрированы. Нажмите /start", show_alert=True)
            return
        
        if db.is_user_banned(user_id):
            await callback.answer("❌ Вы заблокированы", show_alert=True)
            return
        
        # Проверяем подписку
        sub_end = db.get_subscription_end(user_id)
        if not sub_end or sub_end <= datetime.now():
            await callback.answer(
                "❌ Ваша подписка истекла.\n"
                "Обратитесь к администратору для продления.",
                show_alert=True
            )
            return
        
        # Показываем индикатор загрузки
        await callback.answer("⏳ Генерирую ключ...", show_alert=False)
        
        # Генерируем конфигурацию
        config = generate_full_config(
            domain=SERVER_DOMAIN,
            port=SERVER_PORT,
            sni="vtb.ru"
        )
        
        # Вычисляем дату истечения
        expires_at = sub_end
        
        # Сохраняем ключ в БД
        db.add_key(config['uuid'], user_id, config['vless_key'], expires_at)
        
        # Формируем сообщение
        days_left = (expires_at - datetime.now()).days
        
        key_message = (
            f"✅ **Ключ успешно сгенерирован!**\n\n"
            f"🔑 **Ваш VLESS ключ:**\n"
            f"```\n{config['vless_key']}\n```\n\n"
            f"📅 **Действует до:** {expires_at.strftime('%d.%m.%Y')}\n"
            f"⏳ **Осталось дней:** {days_left}\n\n"
            f"📱 **Как использовать:**\n"
            f"1. Скопируйте ключ (нажмите на него)\n"
            f"2. Вставьте в AlufProxy Client или другой совместимый клиент\n"
            f"3. Подключайтесь!\n\n"
            f"⚠️ **Не делитесь ключом!** Он персональный."
        )
        
        # Отправляем ключ с кнопками
        await callback.message.answer(
            key_message,
            reply_markup=get_key_actions_keyboard(config['uuid']),
            parse_mode="Markdown"
        )
        
        await callback.answer()

    @router.callback_query(F.data.startswith("copy_key:"))
    async def callback_copy_key(callback: CallbackQuery):
        """Обработчик копирования ключа"""
        key_id = callback.data.split(":")[1]
        
        # Получаем ключ из БД
        keys = db.get_user_keys(callback.from_user.id)
        key_data = next((k for k in keys if k['id'] == key_id), None)
        
        if not key_data:
            await callback.answer("❌ Ключ не найден", show_alert=True)
            return
        
        # В Telegram нельзя программно скопировать текст
        # Поэтому просто показываем ключ
        await callback.answer(
            "📋 Нажмите на ключ выше, чтобы скопировать его",
            show_alert=True
        )

    @router.callback_query(F.data.startswith("deactivate_key:"))
    async def callback_deactivate_key(callback: CallbackQuery):
        """Обработчик деактивации ключа"""
        key_id = callback.data.split(":")[1]
        
        # Деактивируем ключ
        db.deactivate_key(key_id)
        
        await callback.answer("✅ Ключ деактивирован", show_alert=True)
        
        # Обновляем сообщение
        await callback.message.edit_text(
            "❌ Ключ деактивирован\n\n"
            "Вы можете получить новый ключ через меню."
        )

    @router.callback_query(F.data == "my_keys")
    async def callback_my_keys(callback: CallbackQuery):
        """Обработчик просмотра своих ключей"""
        user_id = callback.from_user.id
        
        # Получаем активные ключи
        keys = db.get_active_keys(user_id)
        
        if not keys:
            await callback.answer("У вас нет активных ключей", show_alert=True)
            await callback.message.answer(
                "📋 **Ваши ключи**\n\n"
                "❌ У вас пока нет активных ключей.\n"
                "Нажмите '🔑 Получить новый ключ', чтобы создать.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Формируем список ключей
        keys_text = "📋 **Ваши активные ключи:**\n\n"
        
        for key in keys[:5]:  # Показываем максимум 5 ключей
            key_id = key['id']
            created = datetime.fromisoformat(key['created_at'])
            expires = datetime.fromisoformat(key['expires_at'])
            days_left = (expires - datetime.now()).days
            
            if days_left > 0:
                status = f"✅ Активен ({days_left} дн.)"
            else:
                status = "⚠️ Истёк"
            
            keys_text += (
                f"🔹 `{key_id[:8]}...`\n"
                f"   Создан: {created.strftime('%d.%m.%Y')}\n"
                f"   Статус: {status}\n\n"
            )
        
        if len(keys) > 5:
            keys_text += f"... и ещё {len(keys) - 5} ключей\n"
        
        keys_text += "\nВыберите ключ для действий:"
        
        # Создаём клавиатуру с ключами
        builder = types.InlineKeyboardBuilder()
        for key in keys[:5]:
            builder.button(
                text=f"🔑 {key['id'][:8]}...",
                callback_data=f"key_detail:{key['id']}"
            )
        builder.button(text="🔙 В меню", callback_data="back")
        builder.adjust(1)
        
        await callback.message.answer(
            keys_text,
            reply_markup=builder.as_markup()
        )
        
        await callback.answer()

    @router.callback_query(F.data.startswith("key_detail:"))
    async def callback_key_detail(callback: CallbackQuery):
        """Обработчик деталей ключа"""
        key_id = callback.data.split(":")[1]
        
        # Получаем ключ
        keys = db.get_user_keys(callback.from_user.id)
        key_data = next((k for k in keys if k['id'] == key_id), None)
        
        if not key_data:
            await callback.answer("❌ Ключ не найден", show_alert=True)
            return
        
        created = datetime.fromisoformat(key_data['created_at'])
        expires = datetime.fromisoformat(key_data['expires_at'])
        days_left = (expires - datetime.now()).days
        
        detail_text = (
            f"🔑 **Детали ключа**\n\n"
            f"ID: `{key_id}`\n"
            f"Создан: {created.strftime('%d.%m.%Y %H:%M')}\n"
            f"Истекает: {expires.strftime('%d.%m.%Y %H:%M')}\n"
            f"Осталось дней: {days_left}\n"
            f"Статус: {'✅ Активен' if key_data['is_active'] else '❌ Неактивен'}\n\n"
            f"**Ключ подключения:**\n"
            f"```\n{key_data['key']}\n```"
        )
        
        await callback.message.answer(
            detail_text,
            reply_markup=get_key_actions_keyboard(key_id),
            parse_mode="Markdown"
        )
        
        await callback.answer()

    @router.callback_query(F.data == "back")
    async def callback_back(callback: CallbackQuery):
        """Возврат в главное меню"""
        await callback.message.edit_text(
            "🏠 **Главное меню AlufProxy**\n\n"
            "Выберите действие:",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()

    return router
