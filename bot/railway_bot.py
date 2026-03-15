"""
AlufProxy Bot - VPS Version
Полная версия с удобной админкой и поддержкой
"""

import sys
sys.path.insert(0, '/root/AlufProxy/AlufProxy/bot')

from config import BOT_TOKEN, ADMIN_IDS, SERVER_DOMAIN, SERVER_PORT, TRIAL_DAYS, SUPPORT_ENABLED
from database import Database
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio
import logging
from datetime import datetime, timedelta
import hashlib
import secrets
import base64
import uuid

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()
db = Database()

# === КЛАВИАТУРЫ ===

def get_start_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔑 Получить ключ", callback_data="get_key")
    builder.button(text="📋 Мои ключи", callback_data="my_keys")
    builder.button(text="📞 Поддержка", callback_data="support_start")
    builder.button(text="❓ Помощь", callback_data="help")
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup()

def get_main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔑 Получить новый ключ", callback_data="get_key")
    builder.button(text="📋 Мои ключи", callback_data="my_keys")
    builder.button(text="📞 Поддержка", callback_data="support_start")
    builder.button(text="❓ Помощь", callback_data="help")
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup()

def get_key_actions_keyboard(key_id: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Скопировать ключ", callback_data="copy_key")
    builder.button(text="❌ Деактивировать", callback_data=f"deactivate_key:{key_id}")
    builder.button(text="🔙 Назад", callback_data="back")
    builder.adjust(1, 1, 1)
    return builder.as_markup()

def get_admin_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="👥 Пользователи", callback_data="admin_users")
    builder.button(text="📞 Поддержка ({})", callback_data="admin_support")
    builder.button(text="🔙 В меню", callback_data="back")
    builder.adjust(2, 2)
    return builder.as_markup()

def get_support_admin_keyboard():
    builder = InlineKeyboardBuilder()
    tickets = db.get_open_tickets()
    for ticket in tickets[:10]:
        user = db.get_user(ticket['user_id'])
        username = user.get('username', 'N/A') if user else 'N/A'
        builder.button(
            text=f"#{ticket['id']} @{username}",
            callback_data=f"ticket_view:{ticket['id']}"
        )
    builder.button(text="🔙 Назад", callback_data="admin_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_ticket_keyboard(ticket_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✍️ Ответить", callback_data=f"ticket_reply:{ticket_id}")
    builder.button(text="✅ Закрыть", callback_data=f"ticket_close:{ticket_id}")
    builder.button(text="🔙 Назад", callback_data="admin_support")
    builder.adjust(2, 1)
    return builder.as_markup()

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def generate_uuid() -> str:
    return str(uuid.uuid4())

def generate_reality_keys() -> tuple:
    private_key_bytes = secrets.token_bytes(32)
    private_key = base64.b64encode(private_key_bytes).decode('utf-8')
    public_key_bytes = hashlib.sha256(private_key_bytes).digest()
    public_key = base64.b64encode(public_key_bytes).decode('utf-8')
    return private_key, public_key

def generate_short_id() -> str:
    return secrets.token_hex(8)

def generate_vless_key(uuid_key: str, domain: str, port: int, 
                       public_key: str, short_id: str, sni: str = "gosuslugi.ru") -> str:
    from urllib.parse import urlencode
    params = {
        'encryption': 'none',
        'security': 'reality',
        'sni': sni,
        'fp': 'chrome',
        'pbk': public_key,
        'sid': short_id,
        'type': 'tcp',
        'headerType': 'none'
    }
    query = urlencode(params)
    label = f"AlufProxy-{uuid_key[:8]}"
    return f"vless://{uuid_key}@{domain}:{port}?{query}#{label}"

# === ОБРАБОТЧИКИ ===

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    first_name = message.from_user.first_name or "User"
    
    db.add_user(user_id, username, first_name)
    
    if db.is_user_banned(user_id):
        await message.answer(
            "❌ Вы заблокированы в системе.\n"
            "Обратитесь к администратору для разблокировки."
        )
        return
    
    db.set_support_mode(user_id, False)
    sub_end = db.get_subscription_end(user_id)
    
    if sub_end:
        if sub_end > datetime.now():
            days_left = (sub_end - datetime.now()).days
            status = f"✅ Подписка активна ещё {days_left} дн."
        else:
            status = "❌ Подписка истекла"
    else:
        status = f"🎁 Пробный период: {TRIAL_DAYS} дн."
    
    await message.answer(
        f"👋 Привет, {first_name}!\n\n"
        f"🚀 AlufProxy — твой надёжный прокси для обхода блокировок.\n\n"
        f"📡 Твой статус:\n"
        f"{status}\n\n"
        f"🔹 VLESS Reality — максимальная защита\n"
        f"🔹 Обход DPI — трафик как обычный HTTPS\n"
        f"🔹 Быстрое подключение — работает с Windows, Linux, macOS\n\n"
        f"Нажми кнопку ниже, чтобы получить ключ подключения!",
        reply_markup=get_start_keyboard()
    )
    logger.info(f"Start от {user_id}")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "📖 Инструкция по использованию AlufProxy\n\n"
        "1. Получение ключа:\n"
        "   Нажми /start или кнопку '🔑 Получить ключ'\n\n"
        "2. Настройка ПК-клиента:\n"
        "   • Скачай AlufProxy Client для Windows\n"
        "   • Вставь полученный ключ в поле подключения\n"
        "   • Нажми 'Подключиться'\n\n"
        "3. Использование с другими клиентами:\n"
        "   Ключ совместим с:\n"
        "   • v2rayNG (Android)\n"
        "   • Shadowrocket (iOS)\n"
        "   • NekoBox (Android)\n"
        "   • Hiddify (все платформы)\n\n"
        "4. Если не работает:\n"
        "   • Проверь дату окончания подписки\n"
        "   • Попробуй получить новый ключ\n"
        "   • Обратись в поддержку\n\n"
        "📧 Поддержка: @a_skale"
    )
    await message.answer(help_text, parse_mode=None)
    logger.info(f"Help от {message.from_user.id}")

@dp.message(Command("support"))
async def cmd_support(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    
    if not SUPPORT_ENABLED:
        await message.answer("❌ Поддержка временно недоступна.")
        return
    
    ticket = db.get_user_open_ticket(user_id)
    
    if ticket:
        await message.answer(
            f"📞 У вас уже есть открытое обращение #{ticket['id']}\n\n"
            "Напишите ваше сообщение, и оно будет доставлено администратору."
        )
        db.set_support_mode(user_id, True)
    else:
        await message.answer(
            "📞 Поддержка AlufProxy\n\n"
            "Опишите вашу проблему, и администратор свяжется с вами.\n\n"
            "✍️ Напишите сообщение прямо сейчас."
        )
        db.set_support_mode(user_id, True)
    logger.info(f"Support от {user_id}")

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    stats = db.get_stats()
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="📊 Статистика", callback_data="admin_stats")
    keyboard.button(text="👥 Пользователи", callback_data="admin_users")
    keyboard.button(text=f"📞 Поддержка ({stats['open_tickets']})", callback_data="admin_support")
    keyboard.adjust(1, 1, 1)
    
    await message.answer(
        f"🛠 Админ-панель AlufProxy\n\n"
        f"📊 Статистика:\n"
        f"• Пользователей: {stats['total_users']}\n"
        f"• Активных: {stats['active_users']}\n"
        f"• Забанено: {stats['banned_users']}\n"
        f"• Ключей: {stats['total_keys']}\n"
        f"• Обращений: {stats['open_tickets']}\n\n"
        f"Выберите раздел:",
        reply_markup=keyboard.as_markup()
    )
    logger.info(f"Admin от {message.from_user.id}")

@dp.message(Command("add_time"))
async def cmd_add_time(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    args = message.text.split()
    if len(args) != 3:
        await message.answer("Используйте: /add_time <user_id> <days>")
        return
    
    try:
        user_id = int(args[1])
        days = int(args[2])
        if db.extend_subscription(user_id, days):
            await message.answer(f"✅ Подписка пользователя {user_id} продлена на {days} дн.")
        else:
            await message.answer(f"❌ Пользователь {user_id} не найден")
    except ValueError:
        await message.answer("❌ user_id и days должны быть числами")

@dp.message(Command("ban"))
async def cmd_ban(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Используйте: /ban <user_id>")
        return
    
    try:
        user_id = int(args[1])
        if db.ban_user(user_id):
            await message.answer(f"✅ Пользователь {user_id} забанен")
        else:
            await message.answer(f"❌ Пользователь {user_id} не найден")
    except ValueError:
        await message.answer("❌ user_id должен быть числом")

@dp.message(Command("unban"))
async def cmd_unban(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Используйте: /unban <user_id>")
        return
    
    try:
        user_id = int(args[1])
        if db.unban_user(user_id):
            await message.answer(f"✅ Пользователь {user_id} разбанен")
        else:
            await message.answer(f"❌ Пользователь {user_id} не найден")
    except ValueError:
        await message.answer("❌ user_id должен быть числом")

@dp.message(Command("cancel"))
async def cmd_cancel(message: Message):
    user_id = message.from_user.id
    if hasattr(bot, '_reply_context') and user_id in bot._reply_context:
        del bot._reply_context[user_id]
    db.set_support_mode(user_id, False)
    await message.answer("✅ Выход из режима поддержки")

# === CALLBACK QUERY ===

@dp.callback_query(F.data == "get_key")
async def callback_get_key(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    user = db.get_user(user_id)
    if not user:
        await callback.answer("❌ Вы не зарегистрированы. Нажмите /start", show_alert=True)
        return
    
    if db.is_user_banned(user_id):
        await callback.answer("❌ Вы заблокированы", show_alert=True)
        return
    
    sub_end = db.get_subscription_end(user_id)
    if not sub_end or sub_end <= datetime.now():
        await callback.answer("❌ Ваша подписка истекла", show_alert=True)
        return
    
    await callback.answer("⏳ Генерирую ключ...")
    
    uuid_key = generate_uuid()
    public_key, private_key = generate_reality_keys()
    short_id = generate_short_id()
    
    vless_key = generate_vless_key(
        uuid_key=uuid_key,
        domain=SERVER_DOMAIN,
        port=SERVER_PORT,
        public_key=public_key,
        short_id=short_id,
        sni="gosuslugi.ru"
    )
    
    expires_at = sub_end
    db.add_key(uuid_key, user_id, vless_key, expires_at)
    
    days_left = (expires_at - datetime.now()).days
    
    await callback.message.answer(
        f"✅ Ключ успешно сгенерирован!\n\n"
        f"🔑 Ваш VLESS ключ:\n"
        f"```\n{vless_key}\n```\n\n"
        f"📅 Действует до: {expires_at.strftime('%d.%m.%Y')}\n"
        f"⏳ Осталось дней: {days_left}\n\n"
        f"⚠️ Не делитесь ключом! Он персональный.",
        parse_mode="Markdown",
        reply_markup=get_key_actions_keyboard(uuid_key)
    )
    logger.info(f"Ключ сгенерирован для {user_id}")

@dp.callback_query(F.data == "copy_key")
async def callback_copy_key(callback: CallbackQuery):
    await callback.answer("📋 Нажмите на ключ выше, чтобы скопировать", show_alert=True)

@dp.callback_query(F.data.startswith("deactivate_key:"))
async def callback_deactivate_key(callback: CallbackQuery):
    key_id = callback.data.split(":")[1]
    db.deactivate_key(key_id)
    await callback.answer("✅ Ключ деактивирован", show_alert=True)
    await callback.message.edit_text("❌ Ключ деактивирован\n\nВы можете получить новый ключ через меню.")

@dp.callback_query(F.data == "my_keys")
async def callback_my_keys(callback: CallbackQuery):
    user_id = callback.from_user.id
    keys = db.get_active_keys(user_id)
    
    if not keys:
        await callback.answer("У вас нет активных ключей", show_alert=True)
        await callback.message.answer(
            "📋 Ваши ключи\n\n"
            "❌ У вас пока нет активных ключей.\n"
            "Нажмите '🔑 Получить новый ключ', чтобы создать.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    keys_text = "📋 Ваши активные ключи:\n\n"
    for key in keys[:5]:
        key_id = key['id']
        created = datetime.fromisoformat(key['created_at'])
        expires = datetime.fromisoformat(key['expires_at'])
        days_left = (expires - datetime.now()).days
        status = f"✅ Активен ({days_left} дн.)" if days_left > 0 else "⚠️ Истёк"
        keys_text += f"🔹 {key_id[:8]}...\n   Создан: {created.strftime('%d.%m.%Y')}\n   Статус: {status}\n\n"
    
    if len(keys) > 5:
        keys_text += f"... и ещё {len(keys) - 5} ключей\n"
    
    await callback.message.answer(keys_text, reply_markup=get_main_menu_keyboard())
    logger.info(f"Просмотр ключей {user_id}")

@dp.callback_query(F.data == "support_start")
async def callback_support(callback: CallbackQuery):
    await callback.message.answer(
        "📞 Поддержка AlufProxy\n\n"
        "Напишите /support для создания обращения."
    )
    await callback.answer()

@dp.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    await callback.message.answer(
        "📖 Инструкция:\n\n"
        "1. Нажмите '🔑 Получить ключ'\n"
        "2. Скопируйте ключ\n"
        "3. Вставьте в клиент\n"
        "4. Подключайтесь!\n\n"
        "Подробно: /help"
    )
    await callback.answer()

@dp.callback_query(F.data == "back")
async def callback_back(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏠 Главное меню AlufProxy\n\nВыберите действие:",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_menu")
async def callback_admin_menu(callback: CallbackQuery):
    stats = db.get_stats()
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="📊 Статистика", callback_data="admin_stats")
    keyboard.button(text="👥 Пользователи", callback_data="admin_users")
    keyboard.button(text=f"📞 Поддержка ({stats['open_tickets']})", callback_data="admin_support")
    keyboard.adjust(1, 1, 1)
    
    await callback.message.edit_text(
        f"🛠 Админ-панель AlufProxy\n\n"
        f"📊 Статистика:\n"
        f"• Пользователей: {stats['total_users']}\n"
        f"• Активных: {stats['active_users']}\n"
        f"• Забанено: {stats['banned_users']}\n"
        f"• Ключей: {stats['total_keys']}\n"
        f"• Обращений: {stats['open_tickets']}\n\n"
        f"Выберите раздел:",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery):
    stats = db.get_stats()
    
    await callback.message.answer(
        f"📊 Статистика AlufProxy:\n\n"
        f"• Пользователей: {stats['total_users']}\n"
        f"• Активных: {stats['active_users']}\n"
        f"• Забанено: {stats['banned_users']}\n"
        f"• Ключей: {stats['total_keys']}\n"
        f"• Активных ключей: {stats['active_keys']}\n"
        f"• Обращений: {stats['open_tickets']}"
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_users")
async def callback_admin_users(callback: CallbackQuery):
    users = db.get_all_users()[:20]
    
    users_text = "👥 Пользователи (последние 20):\n\n"
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
        users_text += f"{ban_status} {user_id} | @{username}\n   Рег: {registered.strftime('%d.%m.%Y')} | Подписка: {sub_status}\n\n"
    
    await callback.message.answer(users_text)
    await callback.answer()

@dp.callback_query(F.data == "admin_support")
async def callback_admin_support(callback: CallbackQuery):
    await callback.message.edit_text(
        "📞 Открытые обращения:\n\nВыберите обращение:",
        reply_markup=get_support_admin_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("ticket_view:"))
async def callback_ticket_view(callback: CallbackQuery):
    ticket_id = int(callback.data.split(":")[1])
    ticket = db.get_ticket(ticket_id)
    
    if not ticket:
        await callback.answer("Обращение не найдено", show_alert=True)
        return
    
    user = db.get_user(ticket['user_id'])
    username = user.get('username', 'N/A') if user else 'N/A'
    messages = db.get_ticket_messages(ticket_id)
    
    messages_text = f"📞 Обращение #{ticket_id}\n\n"
    messages_text += f"👤 Пользователь: @{username} ({ticket['user_id']})\n"
    messages_text += f"📅 Создано: {ticket['created_at'][:16]}\n\n"
    messages_text += "Переписка:\n"
    
    for msg in messages[-20:]:
        sender = "👨‍💼 Вы" if msg['is_from_admin'] else f"👤 @{username}"
        messages_text += f"\n{sender}:\n{msg['message'][:200]}"
    
    await callback.message.answer(
        messages_text,
        reply_markup=get_ticket_keyboard(ticket_id)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("ticket_reply:"))
async def callback_ticket_reply(callback: CallbackQuery):
    ticket_id = int(callback.data.split(":")[1])
    
    # Устанавливаем контекст ответа
    if not hasattr(bot, '_reply_context'):
        bot._reply_context = {}
    bot._reply_context[callback.from_user.id] = ('ticket', ticket_id)
    
    await callback.message.answer(
        f"📝 Ответ на обращение #{ticket_id}\n\n"
        "Напишите ваше сообщение для пользователя:"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("ticket_close:"))
async def callback_ticket_close(callback: CallbackQuery):
    ticket_id = int(callback.data.split(":")[1])
    ticket = db.get_ticket(ticket_id)
    
    if not ticket:
        await callback.answer("Обращение не найдено", show_alert=True)
        return
    
    db.close_ticket(ticket_id)
    
    try:
        await bot.send_message(
            ticket['user_id'],
            f"✅ Ваше обращение #{ticket_id} закрыто.\n\n"
            "Если у вас остались вопросы, создайте новое обращение через /support"
        )
    except:
        pass
    
    await callback.message.edit_text(f"✅ Обращение #{ticket_id} закрыто")
    await callback.answer(f"Обращение #{ticket_id} закрыто")

# === ОБРАБОТКА СООБЩЕНИЙ ===

@dp.message(F.text)
async def handle_messages(message: Message):
    user_id = message.from_user.id
    text = message.text
    
    # Проверка режима ответа админа
    if hasattr(bot, '_reply_context') and user_id in bot._reply_context:
        context = bot._reply_context[user_id]
        
        if isinstance(context, tuple) and context[0] == 'ticket':
            ticket_id = context[1]
            ticket = db.get_ticket(ticket_id)
            
            if ticket and text:
                db.add_support_message(ticket_id, user_id, text, is_from_admin=True)
                
                try:
                    await bot.send_message(
                        ticket['user_id'],
                        f"📬 Ответ от поддержки (обращение #{ticket_id})\n\n{text}"
                    )
                    await message.answer("✅ Сообщение отправлено пользователю")
                except Exception as e:
                    logger.error(f"Ошибка отправки: {e}")
                    await message.answer("❌ Ошибка отправки")
                
                del bot._reply_context[user_id]
                return
    
    # Проверка режима поддержки пользователя
    if db.is_in_support_mode(user_id):
        if not SUPPORT_ENABLED:
            await message.answer("❌ Поддержка временно недоступна.")
            db.set_support_mode(user_id, False)
            return
        
        ticket = db.get_user_open_ticket(user_id)
        
        if not ticket:
            ticket_id = db.create_support_ticket(user_id, message.from_user.username or "Unknown")
            if ticket_id > 0:
                db.add_support_message(ticket_id, user_id, text)
                
                for admin_id in ADMIN_IDS:
                    try:
                        keyboard = InlineKeyboardBuilder()
                        keyboard.button(text="✍️ Ответить", callback_data=f"ticket_reply:{ticket_id}")
                        keyboard.button(text="✅ Закрыть", callback_data=f"ticket_close:{ticket_id}")
                        keyboard.adjust(2)
                        
                        await bot.send_message(
                            admin_id,
                            f"🔔 Новое обращение #{ticket_id}\n\n"
                            f"👤 Пользователь: @{message.from_user.username or 'Unknown'} ({user_id})\n"
                            f"📝 Сообщение:\n{text}",
                            reply_markup=keyboard.as_markup()
                        )
                    except Exception as e:
                        logger.error(f"Не удалось уведомить админа {admin_id}: {e}")
                
                await message.answer(
                    f"✅ Обращение #{ticket_id} создано\n\n"
                    "Администратор скоро ответит вам.\n"
                    "Продолжайте писать сюда, сообщения будут доставлены админу."
                )
            else:
                await message.answer("❌ Не удалось создать обращение.")
                db.set_support_mode(user_id, False)
        else:
            ticket_id = ticket['id']
            db.add_support_message(ticket_id, user_id, text)
            await message.answer("✅ Сообщение отправлено в поддержку.\nОжидайте ответа.")
        
        logger.info(f"Сообщение поддержки от {user_id}")
        return
    
    # Неизвестная команда
    await message.answer(
        "🤔 Не понимаю эту команду.\n\n"
        "Используйте /start или /help",
        reply_markup=get_main_menu_keyboard()
    )

# === ЗАПУСК ===

async def main():
    logger.info("=" * 50)
    logger.info("AlufProxy Bot запускается...")
    logger.info(f"Режим: Polling")
    logger.info(f"Поддержка: {'включена' if SUPPORT_ENABLED else 'выключена'}")
    logger.info(f"Сервер: {SERVER_DOMAIN}:{SERVER_PORT}")
    logger.info("=" * 50)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
