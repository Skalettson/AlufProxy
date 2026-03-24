"""
AlufProxy Bot - VPS Version
Полная версия с удобной админкой и поддержкой
"""

import sys
sys.path.insert(0, '/root/AlufProxy/AlufProxy/bot')

from config import (
    BOT_TOKEN, ADMIN_IDS, SERVER_DOMAIN, SERVER_PORT, TRIAL_DAYS,
    SUPPORT_ENABLED, KEY_UPDATE_API_URL, KEY_UPDATE_API_KEY,
    SUBSCRIPTION_PRICES, PAYMENT_DETAILS, VLESS_SNI
)
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
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = Database()

# === КЛАВИАТУРЫ ===

def get_start_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎁 Пробный период 7 дней", callback_data="trial_key")
    builder.button(text="💳 Купить подписку", callback_data="buy_subscription")
    builder.button(text="📞 Поддержка", callback_data="support_start")
    builder.button(text="❓ Помощь", callback_data="help")
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup()

def get_main_menu_keyboard(user_id: int = 0):
    """Главное меню с учётом статуса оплаты"""
    builder = InlineKeyboardBuilder()
    
    # Проверяем статус оплаты
    payment_status, _ = db.get_payment_status(user_id) if user_id else ('none', 0)
    sub_end = db.get_subscription_end(user_id) if user_id else None
    has_active_sub = sub_end and sub_end > datetime.now()
    
    if has_active_sub:
        builder.button(text="🔑 Получить ключ", callback_data="get_key")
        builder.button(text="💳 Продлить подписку", callback_data="buy_subscription")
    elif payment_status == 'pending':
        builder.button(text="⏳ Оплата в процессе", callback_data="payment_pending")
        builder.button(text="💳 Оплатить подписку", callback_data="buy_subscription")
    else:
        builder.button(text="💳 Купить подписку", callback_data="buy_subscription")
    
    builder.button(text="📋 Мои ключи", callback_data="my_keys")
    builder.button(text="📞 Поддержка", callback_data="support_start")
    builder.button(text="❓ Помощь", callback_data="help")
    builder.adjust(1, 1, 1, 1, 1)
    return builder.as_markup()

def get_subscription_period_keyboard():
    """Выбор срока подписки"""
    builder = InlineKeyboardBuilder()
    builder.button(text=f"1 месяц — {SUBSCRIPTION_PRICES[1]}₽", callback_data="sub_1")
    builder.button(text=f"3 месяца — {SUBSCRIPTION_PRICES[3]}₽", callback_data="sub_3")
    builder.button(text=f"6 месяцев — {SUBSCRIPTION_PRICES[6]}₽", callback_data="sub_6")
    builder.button(text=f"1 год — {SUBSCRIPTION_PRICES[12]}₽", callback_data="sub_12")
    builder.button(text="🔙 Назад", callback_data="back_to_menu")
    builder.adjust(1, 1, 1, 1, 1)
    return builder.as_markup()

def get_payment_keyboard(months: int, amount: int):
    """Кнопки после выбора тарифа"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Я оплатил", callback_data=f"payment_confirm:{months}:{amount}")
    builder.button(text="🔙 Назад", callback_data="buy_subscription")
    builder.adjust(1, 1)
    return builder.as_markup()

def get_admin_payment_keyboard(ticket_id: int, user_id: int):
    """Клавиатура для подтверждения оплаты админом"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить оплату", callback_data=f"payment_approve:{ticket_id}:{user_id}")
    builder.button(text="❌ Отклонить", callback_data=f"payment_decline:{ticket_id}:{user_id}")
    builder.adjust(1, 1)
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
    builder.button(text="💳 Заявки на оплату", callback_data="admin_payments")
    builder.button(text="📞 Поддержка", callback_data="admin_support")
    builder.button(text="🔑 Ключи", callback_data="admin_keys")
    builder.button(text="📨 Рассылка", callback_data="admin_broadcast")
    builder.adjust(2, 2, 2)
    return builder.as_markup()

def get_admin_users_keyboard():
    """Клавиатура для управления пользователями"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="admin_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_user_actions_keyboard(user_id: int):
    """Действия с пользователем"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⏳ Продлить (+7д)", callback_data=f"user_extend_7:{user_id}")
    builder.button(text="⏳ Продлить (+30д)", callback_data=f"user_extend_30:{user_id}")
    builder.button(text="🚫 Забанить", callback_data=f"user_ban:{user_id}")
    builder.button(text="✅ Разбанить", callback_data=f"user_unban:{user_id}")
    builder.button(text="🔑 Ключи", callback_data=f"user_keys:{user_id}")
    builder.button(text="🔙 Назад", callback_data="admin_users")
    builder.adjust(2, 2, 1)
    return builder.as_markup()

def get_admin_keys_keyboard(key_id: str):
    """Клавиатура для управления ключом"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Удалить", callback_data=f"key_delete:{key_id}")
    builder.button(text="🔙 Назад", callback_data="admin_keys")
    builder.adjust(1, 1)
    return builder.as_markup()

def get_admin_broadcast_keyboard():
    """Клавиатура для рассылки"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📨 Всем", callback_data="broadcast_all")
    builder.button(text="🎁 Пробный период", callback_data="broadcast_trial")
    builder.button(text="💳 Оплаченные", callback_data="broadcast_paid")
    builder.button(text="🔙 Назад", callback_data="admin_menu")
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

def get_server_keys() -> tuple:
    """
    Получение ключей сервера через API
    Возвращает (public_key, short_id)
    """
    try:
        response = requests.get(f"{KEY_UPDATE_API_URL}/api/server_keys", timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                return result.get('public_key', ''), result.get('short_id', '')
        logger.error(f"Не удалось получить ключи сервера: HTTP {response.status_code}")
    except Exception as e:
        logger.error(f"Ошибка получения ключей: {e}")
    return '', ''


def generate_uuid() -> str:
    return str(uuid.uuid4())


def generate_vless_key(uuid_key: str, domain: str, port: int,
                       public_key: str, short_id: str, sni: str = None) -> str:
    from urllib.parse import urlencode
    
    # Если SNI не указан, берём из конфига
    if sni is None:
        sni = VLESS_SNI
    
    params = {
        'encryption': 'none',
        'security': 'reality',
        'sni': sni,
        'fp': 'chrome',
        'pbk': public_key,
        'sid': short_id,
        'type': 'tcp',
        'headerType': 'none',
        'flow': 'xtls-rprx-vision'
    }
    query = urlencode(params)
    label = f"AlufProxy-{uuid_key[:8]}"
    return f"vless://{uuid_key}@{domain}:{port}?{query}#{label}"

# === АДМИН КОМАНДЫ ===

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    await message.answer(
        "👨‍💼 **Админ-панель AlufProxy**\n\nВыберите раздел:",
        parse_mode=None,
        reply_markup=get_admin_keyboard()
    )
    logger.info(f"Admin panel opened by {message.from_user.id}")

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    stats = db.get_advanced_stats()
    
    await message.answer(
        f"📊 Статистика AlufProxy\n\n"
        f"👥 Пользователи:\n"
        f"• Всего: {stats['total_users']}\n"
        f"• Активных: {stats['active_users']}\n"
        f"• Забанено: {stats['banned_users']}\n\n"
        f"💳 Подписки:\n"
        f"• Пробные: {stats['trial_users']}\n"
        f"• Оплаченные: {stats['paid_users']}\n"
        f"• Ожидают оплаты: {stats['pending_payment']}\n\n"
        f"🔑 Ключи:\n"
        f"• Всего: {stats['total_keys']}\n"
        f"• Активных: {stats['active_keys']}\n\n"
        f"📞 Заявки:\n"
        f"• Поддержка: {stats['open_tickets']}\n"
        f"• На оплату: {stats['payment_tickets']}"
    )
    logger.info(f"Stats requested by {message.from_user.id}")

@dp.message(Command("users"))
async def cmd_users(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    users = db.get_users_paginated(limit=20)
    
    users_text = "👥 Пользователи (последние 20):\n\n"
    for user in users:
        user_id = user['id']
        username = user.get('username', 'N/A')
        registered = datetime.fromisoformat(user['registered_at'])
        is_banned = user.get('is_banned', 0)
        sub_end_str = user.get('subscription_end', 'N/A')
        payment_status = user.get('payment_status', 'none')
        
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
        payment_emoji = {"trial": "🎁", "paid": "💳", "pending": "⏳", "none": ""}.get(payment_status, "")
        
        users_text += f"{ban_status} {payment_emoji} `{user_id}` | @{username}\n"
        users_text += f"   Рег: {registered.strftime('%d.%m.%Y')} | Подписка: {sub_status}\n\n"
    
    await message.answer(users_text)
    logger.info(f"Users list requested by {message.from_user.id}")

@dp.message(Command("payments"))
async def cmd_payments(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    tickets = db.get_payment_tickets()
    
    if not tickets:
        await message.answer("✅ Нет активных заявок на оплату")
        return
    
    for ticket in tickets:
        username = ticket.get('username', 'N/A')
        user_id = ticket['user_id']
        ticket_id = ticket['id']
        
        await message.answer(
            f"💳 Заявка на оплату #{ticket_id}\n\n"
            f"👤 Пользователь: @{username} ({user_id})\n\n"
            f"Нажмите кнопку для подтверждения.",
            reply_markup=get_admin_payment_keyboard(ticket_id, user_id)
        )
    
    logger.info(f"Payment tickets requested by {message.from_user.id}")

@dp.message(Command("keys"))
async def cmd_keys(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    keys = db.get_all_keys(limit=50)
    
    if not keys:
        await message.answer("✅ Нет ключей")
        return
    
    # Отправляем каждый ключ с кнопкой удаления
    for key in keys:
        username = key.get('username', 'N/A')
        key_id = key['id']
        key_short = key_id[:8]
        created = key['created_at'][:10]
        expires = key['expires_at'][:10]
        is_active = "✅" if key['is_active'] else "❌"
        user_id = key.get('user_id', 'N/A')
        
        await message.answer(
            f"🔑 Ключ\n\n"
            f"`{key_short}...`\n\n"
            f"👤 Пользователь: @{username} ({user_id})\n"
            f"📅 Создан: {created}\n"
            f"⏳ Истекает: {expires}\n"
            f"Статус: {is_active}",
            reply_markup=get_admin_keys_keyboard(key_id)
        )
    
    logger.info(f"Keys list requested by {message.from_user.id}")

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    await message.answer(
        "📨 Рассылка\n\n"
        "Выберите аудиторию:",
        reply_markup=get_admin_broadcast_keyboard()
    )
    logger.info(f"Broadcast panel opened by {message.from_user.id}")

@dp.message(Command("support"))
async def cmd_support_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    await message.answer(
        "📞 Открытые обращения:\n\nВыберите обращение:",
        reply_markup=get_support_admin_keyboard()
    )
    logger.info(f"Support panel opened by {message.from_user.id}")

# === ОБРАБОТЧИКИ ОПЛАТЫ ===

@dp.callback_query(F.data == "buy_subscription")
async def callback_buy_subscription(callback: CallbackQuery):
    """Показ выбора срока подписки"""
    await callback.message.answer(
        "💳 **Выберите срок подписки**\n\n"
        "📋 Доступные тарифы:\n"
        f"• 1 месяц — {SUBSCRIPTION_PRICES[1]}₽\n"
        f"• 3 месяца — {SUBSCRIPTION_PRICES[3]}₽ (экономия {3*SUBSCRIPTION_PRICES[1] - SUBSCRIPTION_PRICES[3]}₽)\n"
        f"• 6 месяцев — {SUBSCRIPTION_PRICES[6]}₽ (экономия {6*SUBSCRIPTION_PRICES[1] - SUBSCRIPTION_PRICES[6]}₽)\n"
        f"• 1 год — {SUBSCRIPTION_PRICES[12]}₽ (экономия {12*SUBSCRIPTION_PRICES[1] - SUBSCRIPTION_PRICES[12]}₽)\n\n"
        "После выбора вы получите реквизиты для оплаты.",
        parse_mode=None,
        reply_markup=get_subscription_period_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("sub_"))
async def callback_select_period(callback: CallbackQuery):
    """Выбор периода и показ реквизитов"""
    months = int(callback.data.split("_")[1])
    amount = SUBSCRIPTION_PRICES.get(months, 0)

    if months == 12:
        period_text = "1 год"
    else:
        period_text = f"{months} мес."

    await callback.message.answer(
        f"💳 Оплата подписки AlufProxy\n\n"
        f"📅 Срок: {period_text}\n"
        f"💰 Сумма: {amount}₽\n\n"
        f"💳 Реквизиты для оплаты:\n\n"
        f"🔹 СБП по номеру карты:\n"
        f"`{PAYMENT_DETAILS['sbp_card']}`\n\n"
        f"🔹 Перевод по номеру счёта:\n"
        f"`{PAYMENT_DETAILS['account_number']}`\n\n"
        f"✍️ Назначение платежа: {PAYMENT_DETAILS['description']}\n\n"
        f"⚠️ Важно:\n"
        f"1. После оплаты нажмите кнопку «Я оплатил»\n"
        f"2. Администратор проверит платёж в течение 15 минут\n"
        f"3. После подтверждения вы получите ключ доступа\n\n"
        f"📞 Если есть вопросы: @a_skale",
        parse_mode=None,
        reply_markup=get_payment_keyboard(months, amount)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("payment_confirm:"))
async def callback_payment_confirm(callback: CallbackQuery):
    """Подтверждение оплаты пользователем"""
    user_id = callback.from_user.id
    username = callback.from_user.username or "Unknown"
    
    parts = callback.data.split(":")
    months = int(parts[1])
    amount = int(parts[2])
    
    # Создаём заявку на оплату
    ticket_id = db.create_payment_ticket(user_id, username, months, amount)
    
    if ticket_id:
        # Устанавливаем статус оплаты
        db.set_payment_status(user_id, 'pending', ticket_id)
        
        # Уведомляем пользователя
        await callback.message.answer(
            "✅ **Заявка создана!**\n\n"
            f"📋 Номер заявки: #{ticket_id}\n"
            f"💰 Сумма: {amount}₽\n"
            f"📅 Срок: {months} мес.\n\n"
            "⏳ Администратор проверит ваш платёж в ближайшее время.\n"
            "🔔 Вы получите уведомление когда подписка будет активирована.",
            parse_mode=None
        )
        
        # Уведомляем админов
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"💳 **Новая заявка на оплату**\n\n"
                    f"👤 Пользователь: @{username} ({user_id})\n"
                    f"📋 Заявка: #{ticket_id}\n"
                    f"💰 Сумма: {amount}₽\n"
                    f"📅 Срок: {months} мес.\n\n"
                    "Нажмите кнопку для подтверждения.",
                    parse_mode=None,
                    reply_markup=get_admin_payment_keyboard(ticket_id, user_id)
                )
            except Exception as e:
                logger.error(f"Не удалось уведомить админа {admin_id}: {e}")
        
        logger.info(f"Создана заявка на оплату: user={user_id}, months={months}, amount={amount}")
    else:
        await callback.message.answer("❌ Ошибка создания заявки. Попробуйте позже.")
    
    await callback.answer()

@dp.callback_query(F.data.startswith("payment_approve:"))
async def callback_payment_approve(callback: CallbackQuery):
    """Подтверждение оплаты админом"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return

    parts = callback.data.split(":")
    ticket_id = int(parts[1])
    user_id = int(parts[2])

    # Получаем информацию о заявке
    tickets = db.get_payment_tickets()
    ticket = next((t for t in tickets if t['id'] == ticket_id), None)

    if not ticket:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    # Извлекаем данные из сообщения заявки
    # Формат сообщения: "Оплата подписки на {months} мес. ({amount} руб.)"
    message_text = ticket.get('message', 'Оплата подписки на 1 мес. (189 руб.)')
    import re
    months_match = re.search(r'на (\d+) мес', message_text)
    months = int(months_match.group(1)) if months_match else 1

    # Активируем подписку
    db.extend_subscription(user_id, months * 30)  # Конвертируем месяцы в дни
    db.set_payment_status(user_id, 'paid', 0)
    db.close_ticket(ticket_id, 'approved')

    # Удаляем старые ключи пользователя
    old_keys = db.get_user_keys(user_id)
    for old_key in old_keys:
        old_key_id = old_key['id']
        # Удаляем из БД
        db.delete_key(old_key_id)
        # Удаляем из XRay через API
        try:
            requests.post(
                f"{KEY_UPDATE_API_URL}/api/remove_client",
                json={"uuid": old_key_id},
                headers={"X-API-Key": KEY_UPDATE_API_KEY},
                timeout=30
            )
            logger.info(f"✅ Старый ключ удалён из XRay: {old_key_id[:8]}...")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось удалить старый ключ из XRay: {e}")

    logger.info(f"🗑️ Удалено старых ключей: {len(old_keys)}")

    # Генерируем ключ (используем проверенный метод из callback_get_key)
    await callback.answer("⏳ Генерирую ключ...")

    # Получаем ключи сервера
    public_key, short_id = get_server_keys()

    if not public_key or not short_id:
        logger.error("❌ Не удалось получить ключи сервера!")
        await callback.message.answer(
            "❌ Ошибка получения ключей сервера.\n"
            "Обратитесь к администратору."
        )
        return

    # Генерируем UUID и ключ
    uuid_key = generate_uuid()
    vless_key = generate_vless_key(
        uuid_key=uuid_key,
        domain=SERVER_DOMAIN,
        port=SERVER_PORT,
        public_key=public_key,
        short_id=short_id
        # SNI берётся из конфига по умолчанию
    )

    # Добавляем клиента в XRay через API
    try:
        response = requests.post(
            f"{KEY_UPDATE_API_URL}/api/add_client",
            json={"uuid": uuid_key, "email": f"user-{user_id}"},
            headers={"X-API-Key": KEY_UPDATE_API_KEY},
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                logger.info(f"✅ Клиент добавлен в XRay: {uuid_key[:8]}...")
            else:
                logger.warning(f"⚠️ Не удалось добавить клиента: {result.get('message')}")
        else:
            logger.warning(f"⚠️ Ошибка API: HTTP {response.status_code}")
    except Exception as e:
        logger.error(f"⚠️ Ошибка добавления клиента: {e}")

    # Добавляем ключ в БД
    expires_at = datetime.now() + timedelta(days=months * 30)
    db.add_key(uuid_key, user_id, vless_key, expires_at)

    # Отправляем ключ пользователю
    try:
        await bot.send_message(
            user_id,
            f"✅ **Оплата подтверждена!**\n\n"
            f"🎉 Ваша подписка активирована.\n"
            f"📅 Срок действия: {months} мес.\n\n"
            f"🔑 **Ваш VLESS ключ:**\n"
            f"```\n{vless_key}\n```\n\n"
            f"📅 Действует до: {expires_at.strftime('%d.%m.%Y')}\n"
            f"⏳ Осталось дней: {months * 30}\n\n"
            f"⚠️ Не делитесь ключом! Он персональный.",
            parse_mode=None
        )
    except Exception as e:
        logger.error(f"Не удалось отправить ключ пользователю {user_id}: {e}")

    # Обновляем сообщение админа
    await callback.message.edit_text(
        f"✅ **Оплата подтверждена**\n\n"
        f"👤 Пользователь: @{ticket.get('username', 'N/A')} ({user_id})\n"
        f"📋 Заявка: #{ticket_id}\n"
        f"💰 Сумма: {amount}₽\n"
        f"📅 Срок: {months} мес.\n\n"
        f"🔑 Ключ: `{uuid_key[:8]}...`\n\n"
        "Подписка активирована, ключ отправлен пользователю.",
        parse_mode=None
    )

    logger.info(f"Оплата подтверждена: ticket={ticket_id}, user={user_id}, months={months}")
    await callback.answer("✅ Оплата подтверждена")

@dp.callback_query(F.data.startswith("payment_decline:"))
async def callback_payment_decline(callback: CallbackQuery):
    """Отклонение оплаты админом"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return

    parts = callback.data.split(":")
    ticket_id = int(parts[1])
    user_id = int(parts[2])

    # Получаем информацию о заявке
    tickets = db.get_payment_tickets()
    ticket = next((t for t in tickets if t['id'] == ticket_id), None)

    if not ticket:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    db.set_payment_status(user_id, 'none', 0)
    db.close_ticket(ticket_id, 'declined')

    # Уведомляем пользователя
    try:
        await bot.send_message(
            user_id,
            "❌ Оплата отклонена\n\n"
            f"Заявка #{ticket_id}\n\n"
            "Свяжитесь с администратором для уточнения: @a_skale",
            parse_mode=None
        )
    except Exception as e:
        logger.error(f"Не удалось уведомить пользователя {user_id}: {e}")

    await callback.message.edit_text(
        f"❌ Оплата отклонена\n\n"
        f"👤 Пользователь: @{ticket.get('username', 'N/A')} ({user_id})\n"
        f"📋 Заявка: #{ticket_id}",
        parse_mode=None
    )

    logger.info(f"Оплата отклонена: ticket={ticket_id}, user={user_id}")
    await callback.answer("❌ Оплата отклонена")

@dp.callback_query(F.data == "payment_pending")
async def callback_payment_pending(callback: CallbackQuery):
    """Статус оплаты в процессе"""
    await callback.answer(
        "⏳ Ваша заявка в процессе обработки.\n"
        "Администратор проверит платёж в ближайшее время.",
        show_alert=True
    )

@dp.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    user_id = callback.from_user.id
    await callback.message.edit_text(
        f"🏠 Главное меню AlufProxy\n\nВыберите действие:",
        reply_markup=get_main_menu_keyboard(user_id)
    )
    await callback.answer()

@dp.callback_query(F.data == "trial_key")
async def callback_trial_key(callback: CallbackQuery):
    """Выдача пробного ключа на 7 дней"""
    user_id = callback.from_user.id
    
    # Проверяем есть ли уже активный ключ
    active_keys = db.get_active_keys(user_id)
    if active_keys:
        now = datetime.now()
        valid_keys = [k for k in active_keys if datetime.fromisoformat(k['expires_at']) > now]
        if valid_keys:
            await callback.answer("❌ У вас уже есть активный ключ", show_alert=True)
            return
    
    # Проверяем не использовал ли уже пробный период
    payment_status, _ = db.get_payment_status(user_id)
    if payment_status != 'none':
        await callback.answer("❌ Пробный период доступен только один раз", show_alert=True)
        return
    
    await callback.answer("⏳ Генерирую пробный ключ...")
    
    # Выдаём пробный период
    expires_at = datetime.now() + timedelta(days=TRIAL_DAYS)
    db.extend_subscription(user_id, TRIAL_DAYS)
    db.set_payment_status(user_id, 'trial')
    
    # Генерируем ключ
    public_key, short_id = get_server_keys()
    uuid_key = generate_uuid()

    vless_key = generate_vless_key(
        uuid_key=uuid_key,
        domain=SERVER_DOMAIN,
        port=SERVER_PORT,
        public_key=public_key,
        short_id=short_id
        # SNI берётся из конфига по умолчанию
    )
    
    # Добавляем в XRay
    try:
        requests.post(
            f"{KEY_UPDATE_API_URL}/api/add_client",
            json={"uuid": uuid_key, "email": f"user-{user_id}"},
            headers={"X-API-Key": KEY_UPDATE_API_KEY},
            timeout=30
        )
    except Exception as e:
        logger.error(f"Ошибка добавления клиента: {e}")
    
    db.add_key(uuid_key, user_id, vless_key, expires_at)
    
    await callback.message.answer(
        f"🎁 **Пробный ключ активирован!**\n\n"
        f"🔑 Ваш VLESS ключ:\n"
        f"```\n{vless_key}\n```\n\n"
        f"📅 Действует до: {expires_at.strftime('%d.%m.%Y')}\n"
        f"⏳ Осталось дней: {TRIAL_DAYS}\n\n"
        f"⚠️ После истечения пробного периода вы сможете приобрести подписку.",
        parse_mode=None,
        reply_markup=get_key_actions_keyboard(uuid_key)
    )
    
    logger.info(f"Пробный ключ выдан: user={user_id}")

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
        f"Нажми кнопку ниже!",
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
        "   • v2RayTun, V2BOX (iOS), Streisand\n"
        "   • Hiddify (все платформы)\n\n"
        "4. Если не работает:\n"
        "   • Проверь дату окончания подписки\n"
        "   • Попробуй получить новый ключ\n"
        "   • Обратись в поддержку\n\n"
        "📧 Поддержка: @a_skale"
    )
    await message.answer(help_text, parse_mode=None)
    logger.info(f"Help от {message.from_user.id}")

@dp.message(Command("my_keys"))
async def cmd_my_keys(message: Message):
    user_id = message.from_user.id
    keys = db.get_active_keys(user_id)

    if not keys:
        await message.answer(
            "📋 Ваши ключи\n\n"
            "❌ У вас пока нет активных ключей.\n"
            "Нажмите '🔑 Получить новый ключ', чтобы создать.",
            reply_markup=get_main_menu_keyboard(user_id),
            parse_mode=None
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

    await message.answer(keys_text, reply_markup=get_main_menu_keyboard(user_id), parse_mode=None)
    logger.info(f"Просмотр ключей {user_id}")

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
@dp.message(Command("addtime"))
async def cmd_add_time(message: Message):
    """Продление подписки пользователю"""
    if message.from_user.id not in ADMIN_IDS:
        return

    args = message.text.split()
    if len(args) != 3:
        await message.answer("Используйте: /add_time <user_id> <days>", parse_mode=None)
        return

    try:
        user_id = int(args[1])
        days = int(args[2])
        
        if db.extend_subscription(user_id, days):
            user = db.get_user(user_id)
            username = user.get('username', 'N/A') if user else 'N/A'
            await message.answer(
                f"✅ Подписка пользователя @{username} ({user_id}) продлена на {days} дн.\n\n"
                f"Теперь действительна до: {db.get_subscription_end(user_id).strftime('%d.%m.%Y')}",
                parse_mode=None
            )
            logger.info(f"Подписка продлена: user_id={user_id}, days={days}")
        else:
            await message.answer(f"❌ Пользователь {user_id} не найден", parse_mode=None)
    except ValueError:
        await message.answer("❌ user_id и days должны быть числами", parse_mode=None)

@dp.message(Command("check"))
@dp.message(Command("checkuser"))
async def cmd_check_user(message: Message):
    """Проверка статуса пользователя"""
    if message.from_user.id not in ADMIN_IDS:
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("Используйте: /check <user_id>", parse_mode=None)
        return

    try:
        user_id = int(args[1])
        user = db.get_user(user_id)
        
        if not user:
            await message.answer(f"❌ Пользователь {user_id} не найден", parse_mode=None)
            return
        
        username = user.get('username', 'N/A')
        sub_end = db.get_subscription_end(user_id)
        is_banned = user.get('is_banned', 0)
        
        if sub_end:
            if sub_end > datetime.now():
                days_left = (sub_end - datetime.now()).days
                status = f"✅ Активна ещё {days_left} дн. (до {sub_end.strftime('%d.%m.%Y')})"
            else:
                status = f"❌ Истекла {sub_end.strftime('%d.%m.%Y')}"
        else:
            status = "❌ Нет подписки"
        
        ban_status = "🚫 Забанен" if is_banned else "✅ Активен"
        
        await message.answer(
            f"👤 Пользователь: @{username} ({user_id})\n\n"
            f"Статус: {ban_status}\n"
            f"Подписка: {status}\n\n"
            f"Команды:\n"
            f"/add_time {user_id} 30 — продлить на 30 дней\n"
            f"/ban {user_id} — забанить\n"
            f"/unban {user_id} — разбанить",
            parse_mode=None
        )
    except ValueError:
        await message.answer("❌ user_id должен быть числом", parse_mode=None)

@dp.message(Command("ban"))
@dp.message(Command("banuser"))
async def cmd_ban(message: Message):
    """Бан пользователя"""
    if message.from_user.id not in ADMIN_IDS:
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("Используйте: /ban <user_id>", parse_mode=None)
        return

    try:
        user_id = int(args[1])
        if db.ban_user(user_id):
            await message.answer(f"✅ Пользователь {user_id} забанен", parse_mode=None)
        else:
            await message.answer(f"❌ Пользователь {user_id} не найден", parse_mode=None)
    except ValueError:
        await message.answer("❌ user_id должен быть числом", parse_mode=None)

@dp.message(Command("unban"))
@dp.message(Command("unbanuser"))
async def cmd_unban(message: Message):
    """Разбан пользователя"""
    if message.from_user.id not in ADMIN_IDS:
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("Используйте: /unban <user_id>", parse_mode=None)
        return

    try:
        user_id = int(args[1])
        if db.unban_user(user_id):
            await message.answer(f"✅ Пользователь {user_id} разбанен", parse_mode=None)
        else:
            await message.answer(f"❌ Пользователь {user_id} не найден", parse_mode=None)
    except ValueError:
        await message.answer("❌ user_id должен быть числом", parse_mode=None)

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

    # Проверяем есть ли уже активный ключ
    active_keys = db.get_active_keys(user_id)
    if active_keys:
        # Проверяем не истёк ли ключ
        now = datetime.now()
        valid_keys = [k for k in active_keys if datetime.fromisoformat(k['expires_at']) > now]
        
        if valid_keys:
            key = valid_keys[0]
            expires_at = datetime.fromisoformat(key['expires_at'])
            days_left = (expires_at - now).days
            
            await callback.answer("❌ У вас уже есть активный ключ", show_alert=True)
            await callback.message.answer(
                f"⚠️ У вас уже есть активный ключ!\n\n"
                f"🔑 Ключ: `{key['id'][:8]}...`\n"
                f"📅 Действует до: {expires_at.strftime('%d.%m.%Y')}\n"
                f"⏳ Осталось дней: {days_left}\n\n"
                f"Вы можете получить новый ключ после истечения срока действия текущего.\n\n"
                f"Если ключ не работает — деактивируйте его и получите новый.",
                parse_mode=None
            )
            logger.info(f"Пользователь {user_id} попытался получить второй ключ (активен до {expires_at})")
            return

    await callback.answer("⏳ Генерирую ключ...")

    # Получаем ключи сервера (они общие для всех пользователей)
    public_key, short_id = get_server_keys()

    if not public_key or not short_id:
        logger.error("❌ Не удалось получить ключи сервера!")
        await callback.message.answer(
            "❌ Ошибка получения ключей сервера.\n"
            "Обратитесь к администратору."
        )
        return

    # Генерируем уникальный UUID для пользователя
    uuid_key = generate_uuid()

    vless_key = generate_vless_key(
        uuid_key=uuid_key,
        domain=SERVER_DOMAIN,
        port=SERVER_PORT,
        public_key=public_key,
        short_id=short_id
        # SNI берётся из конфига по умолчанию
    )

    # Добавляем клиента в XRay через API
    try:
        response = requests.post(
            f"{KEY_UPDATE_API_URL}/api/add_client",
            json={"uuid": uuid_key, "email": f"user-{user_id}"},
            headers={"X-API-Key": KEY_UPDATE_API_KEY},
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                logger.info(f"✅ Клиент добавлен в XRay: {uuid_key[:8]}...")
            else:
                logger.warning(f"⚠️ Не удалось добавить клиента: {result.get('message')}")
        else:
            logger.warning(f"⚠️ Ошибка API: HTTP {response.status_code}")
    except Exception as e:
        logger.error(f"⚠️ Ошибка добавления клиента: {e}")

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
        parse_mode=None,
        reply_markup=get_key_actions_keyboard(uuid_key)
    )
    logger.info(f"Ключ сгенерирован для {user_id}: pbk={public_key[:16]}..., sid={short_id}")

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
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    stats = db.get_advanced_stats()
    
    await callback.message.answer(
        f"📊 Статистика AlufProxy\n\n"
        f"👥 Пользователи:\n"
        f"• Всего: {stats['total_users']}\n"
        f"• Активных: {stats['active_users']}\n"
        f"• Забанено: {stats['banned_users']}\n\n"
        f"💳 Подписки:\n"
        f"• Пробные: {stats['trial_users']}\n"
        f"• Оплаченные: {stats['paid_users']}\n"
        f"• Ожидают оплаты: {stats['pending_payment']}\n\n"
        f"🔑 Ключи:\n"
        f"• Всего: {stats['total_keys']}\n"
        f"• Активных: {stats['active_keys']}\n\n"
        f"📞 Заявки:\n"
        f"• Поддержка: {stats['open_tickets']}\n"
        f"• На оплату: {stats['payment_tickets']}\n\n"
        f"🏆 Топ пользователей:\n"
    )
    
    top_text = ""
    for i, u in enumerate(stats['top_users'], 1):
        username = u.get('username', 'N/A')
        key_count = u.get('key_count', 0)
        top_text += f"{i}. @{username} — {key_count} ключей\n"
    
    await callback.message.answer(top_text)
    await callback.answer()

@dp.callback_query(F.data == "admin_users")
async def callback_admin_users(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    users = db.get_users_paginated(limit=20)
    
    users_text = "👥 Пользователи (последние 20):\n\n"
    for user in users:
        user_id = user['id']
        username = user.get('username', 'N/A')
        registered = datetime.fromisoformat(user['registered_at'])
        is_banned = user.get('is_banned', 0)
        sub_end_str = user.get('subscription_end', 'N/A')
        payment_status = user.get('payment_status', 'none')
        
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
        payment_emoji = {"trial": "🎁", "paid": "💳", "pending": "⏳", "none": ""}.get(payment_status, "")
        
        users_text += f"{ban_status} {payment_emoji} `{user_id}` | @{username}\n"
        users_text += f"   Рег: {registered.strftime('%d.%m.%Y')} | Подписка: {sub_status}\n\n"
    
    await callback.message.answer(
        users_text,
        reply_markup=get_admin_users_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("user_"))
async def callback_user_action(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    parts = callback.data.split(":")
    action = parts[0]
    user_id = int(parts[1])
    
    if action == "user_extend_7":
        success, result = db.extend_subscription_by_id(user_id, 7)
        msg = "✅ Продлено на 7 дней" if success else f"❌ Ошибка: {result}"
    elif action == "user_extend_30":
        success, result = db.extend_subscription_by_id(user_id, 30)
        msg = "✅ Продлено на 30 дней" if success else f"❌ Ошибка: {result}"
    elif action == "user_ban":
        db.ban_user(user_id)
        msg = f"🚫 Пользователь {user_id} забанен"
    elif action == "user_unban":
        db.unban_user(user_id)
        msg = f"✅ Пользователь {user_id} разбанен"
    elif action == "user_keys":
        keys = db.get_user_keys(user_id)
        if keys:
            await callback.answer(f"🔑 Ключи пользователя {user_id}: {len(keys)} шт.", show_alert=True)
            # Показываем каждый ключ с кнопкой удаления
            for key in keys:
                key_id = key['id']
                key_short = key_id[:8]
                created = key['created_at'][:10]
                expires = key['expires_at'][:10]
                is_active = "✅" if key['is_active'] else "❌"
                
                await callback.message.answer(
                    f"🔑 **Ключ**\n\n"
                    f"`{key_short}...`\n\n"
                    f"📅 Создан: {created}\n"
                    f"⏳ Истекает: {expires}\n"
                    f"Статус: {is_active}",
                    parse_mode=None,
                    reply_markup=get_admin_keys_keyboard(key_id)
                )
            return
        else:
            msg = f"❌ У пользователя {user_id} нет ключей"
    else:
        msg = "❌ Неизвестное действие"
    
    await callback.answer(msg, show_alert=True)

@dp.callback_query(F.data == "admin_payments")
async def callback_admin_payments(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    tickets = db.get_payment_tickets()
    
    if not tickets:
        await callback.message.answer("✅ Нет активных заявок на оплату")
        await callback.answer()
        return
    
    for ticket in tickets:
        username = ticket.get('username', 'N/A')
        user_id = ticket['user_id']
        ticket_id = ticket['id']
        
        await callback.message.answer(
            f"💳 Заявка на оплату #{ticket_id}\n\n"
            f"👤 Пользователь: @{username} ({user_id})\n\n"
            f"Нажмите кнопку для подтверждения.",
            reply_markup=get_admin_payment_keyboard(ticket_id, user_id)
        )
    
    await callback.answer()

@dp.callback_query(F.data == "admin_keys")
async def callback_admin_keys(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    keys = db.get_all_keys(limit=50)
    
    if not keys:
        await callback.message.answer("✅ Нет ключей")
        await callback.answer()
        return
    
    # Отправляем каждый ключ с кнопкой удаления
    for key in keys:
        username = key.get('username', 'N/A')
        key_id = key['id']
        key_short = key_id[:8]
        created = key['created_at'][:10]
        expires = key['expires_at'][:10]
        is_active = "✅" if key['is_active'] else "❌"
        user_id = key.get('user_id', 'N/A')
        
        await callback.message.answer(
            f"🔑 Ключ\n\n"
            f"`{key_short}...`\n\n"
            f"👤 Пользователь: @{username} ({user_id})\n"
            f"📅 Создан: {created}\n"
            f"⏳ Истекает: {expires}\n"
            f"Статус: {is_active}",
            parse_mode=None,
            reply_markup=get_admin_keys_keyboard(key_id)
        )
    
    await callback.answer()

@dp.callback_query(F.data.startswith("key_delete:"))
async def callback_key_delete(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    key_id = callback.data.split(":")[1]
    
    # Получаем информацию о ключе перед удалением
    keys = db.get_all_keys(limit=100)
    key = next((k for k in keys if k['id'] == key_id), None)
    
    if not key:
        await callback.answer("❌ Ключ не найден", show_alert=True)
        return
    
    username = key.get('username', 'N/A')
    user_id = key.get('user_id', 'N/A')
    
    # Удаляем ключ из БД
    db.delete_key(key_id)
    
    # TODO: Удаляем клиента из XRay через API
    # try:
    #     requests.post(
    #         f"{KEY_UPDATE_API_URL}/api/remove_client",
    #         json={"uuid": key_id},
    #         headers={"X-API-Key": KEY_UPDATE_API_KEY},
    #         timeout=30
    #     )
    # except Exception as e:
    #     logger.error(f"Ошибка удаления клиента из XRay: {e}")
    
    # Удаляем сообщение с кнопкой
    try:
        await callback.message.delete()
    except:
        pass
    
    await callback.answer(f"✅ Ключ {key_id[:8]}... удалён", show_alert=True)
    
    # Логируем
    logger.info(f"Ключ удалён админом: key={key_id[:8]}..., user=@{username} ({user_id})")

@dp.callback_query(F.data == "admin_broadcast")
async def callback_admin_broadcast(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    await callback.message.answer(
        "📨 Рассылка\n\n"
        "Выберите аудиторию:",
        reply_markup=get_admin_broadcast_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("broadcast_"))
async def callback_broadcast_start(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    audience = callback.data.split("_")[1]
    
    # Устанавливаем контекст
    if not hasattr(bot, '_broadcast_context'):
        bot._broadcast_context = {}
    bot._broadcast_context[callback.from_user.id] = audience
    
    await callback.message.answer(
        f"📨 **Рассылка: {audience}**\n\n"
        "Напишите текст сообщения для рассылки:",
        parse_mode=None
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_menu")
async def callback_admin_menu(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    await callback.message.edit_text(
        "👨‍💼 Админ-панель AlufProxy\n\nВыберите раздел:",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()

@dp.message(lambda message: message.from_user.id in ADMIN_IDS)
async def admin_broadcast_handler(message: Message):
    """Обработчик сообщений от админов для рассылки"""
    if not hasattr(bot, '_broadcast_context'):
        return
    
    audience = bot._broadcast_context.get(message.from_user.id)
    if not audience:
        return
    
    # Получаем пользователей для рассылки
    if audience == "all":
        users = db.get_all_users()
    elif audience == "trial":
        users = [u for u in db.get_all_users() if u.get('payment_status') == 'trial']
    elif audience == "paid":
        users = [u for u in db.get_all_users() if u.get('payment_status') == 'paid']
    else:
        await message.answer("❌ Неизвестная аудитория")
        return
    
    # Рассылаем
    sent_count = 0
    failed_count = 0
    
    for user in users:
        try:
            await bot.send_message(
                user['id'],
                f"📨 **Сообщение от администратора**\n\n"
                f"{message.text}\n\n"
                f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                parse_mode=None
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Не удалось отправить пользователю {user['id']}: {e}")
            failed_count += 1
    
    await message.answer(
        f"✅ **Рассылка завершена**\n\n"
        f"📨 Отправлено: {sent_count}\n"
        f"❌ Не доставлено: {failed_count}\n"
        f"👥 Аудитория: {audience}"
    )
    
    # Очищаем контекст
    del bot._broadcast_context[message.from_user.id]

@dp.callback_query(F.data == "admin_support")
async def callback_admin_support(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
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
