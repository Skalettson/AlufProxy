from aiogram import Router, F, types
from aiogram.types import CallbackQuery, Message
from datetime import datetime, timedelta
import logging
import asyncio

from config import ADMIN_IDS, DEFAULT_SUBSCRIPTION_DAYS, SUPPORT_ENABLED
from database import Database
from utils.key_generator import generate_uuid, generate_reality_keys, generate_short_id, generate_vless_key
from keyboards.inline import (
    get_key_actions_keyboard, 
    get_main_menu_keyboard, 
    get_back_keyboard,
    get_support_admin_keyboard,
    get_ticket_keyboard
)

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
        
        # Генерируем ключ
        uuid_key = generate_uuid()
        public_key, private_key = generate_reality_keys()
        short_id = generate_short_id()
        
        vless_key = generate_vless_key(
            uuid_key=uuid_key,
            server_domain=server_domain,
            server_port=server_port,
            sni="gosuslugi.ru",
            public_key=public_key,
            short_id=short_id
        )
        
        # Вычисляем дату истечения
        expires_at = sub_end
        
        # Сохраняем ключ в БД
        key_id = uuid_key
        db.add_key(key_id, user_id, vless_key, expires_at)
        
        # Формируем сообщение
        days_left = (expires_at - datetime.now()).days
        
        key_message = (
            "✅ **Ключ успешно сгенерирован!**\n\n"
            "🔑 **Ваш VLESS ключ:**\n"
            f"```\n{vless_key}\n```\n\n"
            "📅 **Действует до:** {:%d.%m.%Y}\n".format(expires_at) +
            f"⏳ **Осталось дней:** {days_left}\n\n"
            "📱 **Как использовать:**\n"
            "1. Скопируйте ключ (нажмите на него)\n"
            "2. Вставьте в AlufProxy Client или другой совместимый клиент\n"
            "3. Подключайтесь!\n\n"
            "⚠️ **Не делитесь ключом!** Он персональный."
        )
        
        # Отправляем ключ с кнопками
        await callback.message.answer(
            key_message,
            reply_markup=get_key_actions_keyboard(key_id),
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
        # Выход из режима поддержки
        db.set_support_mode(callback.from_user.id, False)
        
        await callback.message.edit_text(
            "🏠 **Главное меню AlufProxy**\n\n"
            "Выберите действие:",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()

    return router


def create_support_handlers(db: Database):
    """Создание обработчиков поддержки"""
    router = Router()
    
    @router.message()
    async def handle_support_message(message: Message):
        """Обработка сообщений в режиме поддержки"""
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"
        text = message.text
        
        # Игнорируем команды
        if text.startswith('/'):
            return
        
        # Проверяем, в режиме ли поддержки пользователь
        if not db.is_in_support_mode(user_id):
            return
        
        if not SUPPORT_ENABLED:
            await message.answer("❌ Поддержка временно недоступна.")
            db.set_support_mode(user_id, False)
            return
        
        # Проверяем, есть ли открытое обращение
        ticket = db.get_user_open_ticket(user_id)
        
        if not ticket:
            # Создаём новое обращение
            ticket_id = db.create_support_ticket(user_id, username)
            if ticket_id > 0:
                db.add_support_message(ticket_id, user_id, text)
                
                # Уведомляем админов
                for admin_id in ADMIN_IDS:
                    try:
                        await message.bot.send_message(
                            admin_id,
                            f"🔔 **Новое обращение #{ticket_id}**\n\n"
                            f"👤 Пользователь: @{username} (`{user_id}`)\n"
                            f"📝 Сообщение:\n{text}",
                            parse_mode="Markdown",
                            reply_markup=get_ticket_keyboard(ticket_id)
                        )
                    except Exception as e:
                        logger.error(f"Не удалось уведомить админа {admin_id}: {e}")
                
                await message.answer(
                    f"✅ **Обращение #{ticket_id} создано**\n\n"
                    "Администратор скоро ответит вам.\n"
                    "Продолжайте писать сюда, сообщения будут доставлены админу.",
                    parse_mode="Markdown"
                )
            else:
                await message.answer("❌ Не удалось создать обращение. Попробуйте позже.")
                db.set_support_mode(user_id, False)
        else:
            # Добавляем сообщение в существующее обращение
            ticket_id = ticket['id']
            db.add_support_message(ticket_id, user_id, text)
            
            await message.answer(
                "✅ Сообщение отправлено в поддержку.\n"
                "Ожидайте ответа администратора."
            )
    
    return router


def create_admin_support_handlers(db: Database):
    """Создание админ-обработчиков для поддержки"""
    router = Router()
    
    def is_admin(user_id: int) -> bool:
        return user_id in ADMIN_IDS
    
    @router.callback_query(F.data == "admin_support")
    async def callback_admin_support(callback: CallbackQuery):
        """Показ открытых обращений"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещён", show_alert=True)
            return
        
        tickets = db.get_open_tickets()
        
        if not tickets:
            await callback.answer("Нет открытых обращений", show_alert=True)
            return
        
        tickets_text = "📞 **Открытые обращения:**\n\n"
        
        for ticket in tickets[:10]:
            user = db.get_user(ticket['user_id'])
            username = user.get('username', 'N/A') if user else 'N/A'
            tickets_text += (
                f"#{ticket['id']} · @{username}\n"
                f"   Обновлено: {ticket['updated_at'][:16]}\n\n"
            )
        
        if len(tickets) > 10:
            tickets_text += f"... и ещё {len(tickets) - 10}\n"
        
        await callback.message.answer(
            tickets_text,
            reply_markup=get_support_admin_keyboard(tickets),
            parse_mode="Markdown"
        )
        
        await callback.answer()
    
    @router.callback_query(F.data.startswith("ticket_view:"))
    async def callback_ticket_view(callback: CallbackQuery):
        """Просмотр обращения"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещён", show_alert=True)
            return
        
        ticket_id = int(callback.data.split(":")[1])
        ticket = db.get_ticket(ticket_id)
        
        if not ticket:
            await callback.answer("Обращение не найдено", show_alert=True)
            return
        
        user = db.get_user(ticket['user_id'])
        username = user.get('username', 'N/A') if user else 'N/A'
        messages = db.get_ticket_messages(ticket_id)
        
        messages_text = "📞 **Обращение #{ticket_id}**\n\n".format(ticket_id=ticket_id)
        messages_text += f"👤 Пользователь: @{username} (`{ticket['user_id']}`)\n"
        messages_text += f"📅 Создано: {ticket['created_at'][:16]}\n\n"
        messages_text += "**Переписка:**\n"
        
        for msg in messages[-20:]:  # Последние 20 сообщений
            sender = "👨‍💼 Вы" if msg['is_from_admin'] else f"👤 @{username}"
            messages_text += f"\n{sender}:\n{msg['message']}"
        
        await callback.message.answer(
            messages_text,
            reply_markup=get_ticket_keyboard(ticket_id, admin_mode=True),
            parse_mode="Markdown"
        )
        
        await callback.answer()
    
    @router.callback_query(F.data.startswith("ticket_reply:"))
    async def callback_ticket_reply(callback: CallbackQuery):
        """Начало ответа на обращение"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещён", show_alert=True)
            return
        
        ticket_id = int(callback.data.split(":")[1])
        
        # Сохраняем в состоянии (для простоты - в БД)
        # В продакшене лучше использовать FSM
        await callback.message.answer(
            f"📝 **Ответ на обращение #{ticket_id}**\n\n"
            "Напишите ваше сообщение для пользователя:",
            parse_mode="Markdown"
        )
        
        # Устанавливаем флаг ожидания ответа
        # Для простоты используем временное хранилище
        from config import ADMIN_IDS
        if not hasattr(callback.bot, '_reply_context'):
            callback.bot._reply_context = {}
        callback.bot._reply_context[callback.from_user.id] = ticket_id
        
        await callback.answer()
    
    @router.callback_query(F.data.startswith("ticket_close:"))
    async def callback_ticket_close(callback: CallbackQuery):
        """Закрытие обращения"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещён", show_alert=True)
            return
        
        ticket_id = int(callback.data.split(":")[1])
        ticket = db.get_ticket(ticket_id)
        
        if not ticket:
            await callback.answer("Обращение не найдено", show_alert=True)
            return
        
        db.close_ticket(ticket_id)
        
        # Уведомляем пользователя
        try:
            await callback.bot.send_message(
                ticket['user_id'],
                f"✅ Ваше обращение #{ticket_id} закрыто.\n\n"
                "Если у вас остались вопросы, создайте новое обращение через /support"
            )
        except Exception:
            pass
        
        await callback.message.edit_text(
            f"✅ Обращение #{ticket_id} закрыто"
        )
        
        await callback.answer(f"Обращение #{ticket_id} закрыто")
    
    return router
