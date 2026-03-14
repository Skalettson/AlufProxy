from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_start_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для команды /start"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔑 Получить ключ", callback_data="get_key")
    builder.button(text="📋 Мои ключи", callback_data="my_keys")
    builder.button(text="❓ Помощь", callback_data="help")
    builder.adjust(1, 1, 1)
    return builder.as_markup()


def get_key_actions_keyboard(key_id: str) -> InlineKeyboardMarkup:
    """Клавиатура действий для ключа"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Скопировать ключ", callback_data=f"copy_key:{key_id}")
    builder.button(text="❌ Деактивировать", callback_data=f"deactivate_key:{key_id}")
    builder.button(text="🔙 Назад", callback_data="my_keys")
    builder.adjust(1, 1, 1)
    return builder.as_markup()


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔑 Получить новый ключ", callback_data="get_key")
    builder.button(text="📋 Мои ключи", callback_data="my_keys")
    builder.button(text="❓ Помощь", callback_data="help")
    builder.button(text="📊 Статус подписки", callback_data="subscription")
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup()


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Админ-панель"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="👥 Пользователи", callback_data="admin_users")
    builder.button(text="🔑 Ключи", callback_data="admin_keys")
    builder.button(text="📢 Рассылка", callback_data="admin_broadcast")
    builder.adjust(2, 2)
    return builder.as_markup()


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой 'Назад'"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="back")
    return builder.as_markup()


def get_confirm_keyboard(confirm_callback: str, cancel_callback: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=confirm_callback)
    builder.button(text="❌ Отмена", callback_data=cancel_callback)
    builder.adjust(2)
    return builder.as_markup()
