from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_start_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для команды /start"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔑 Получить ключ", callback_data="get_key")
    builder.button(text="📋 Мои ключи", callback_data="my_keys")
    builder.button(text="📞 Поддержка", callback_data="support_start")
    builder.button(text="❓ Помощь", callback_data="help")
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup()


def get_key_actions_keyboard(key_id: str) -> InlineKeyboardMarkup:
    """Клавиатура действий для ключа"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Скопировать ключ", callback_data="copy_key")
    builder.button(text="❌ Деактивировать", callback_data=f"deactivate_key:{key_id}")
    builder.button(text="🔙 Назад", callback_data="back")
    builder.adjust(1, 1, 1)
    return builder.as_markup()


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔑 Получить новый ключ", callback_data="get_key")
    builder.button(text="📋 Мои ключи", callback_data="my_keys")
    builder.button(text="📞 Поддержка", callback_data="support_start")
    builder.button(text="❓ Помощь", callback_data="help")
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup()


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Админ-панель"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="👥 Пользователи", callback_data="admin_users")
    builder.button(text="📞 Поддержка", callback_data="admin_support")
    builder.adjust(2, 1)
    return builder.as_markup()


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой 'Назад'"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="back")
    return builder.as_markup()


def get_support_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура поддержки"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✍️ Написать в поддержку", callback_data="support_write")
    builder.button(text="📋 Мои обращения", callback_data="support_tickets")
    builder.button(text="🔙 Назад", callback_data="back")
    builder.adjust(1, 1, 1)
    return builder.as_markup()


def get_support_admin_keyboard(tickets: list) -> InlineKeyboardMarkup:
    """Клавиатура админа для поддержки"""
    builder = InlineKeyboardBuilder()
    for ticket in tickets[:10]:
        builder.button(
            text=f"#{ticket['id']} · @{ticket.get('username', 'N/A')}",
            callback_data=f"ticket_view:{ticket['id']}"
        )
    builder.button(text="🔙 Назад", callback_data="back")
    builder.adjust(1)
    return builder.as_markup()


def get_ticket_keyboard(ticket_id: int, admin_mode: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для обращения"""
    builder = InlineKeyboardBuilder()
    if admin_mode:
        builder.button(text="✍️ Ответить", callback_data=f"ticket_reply:{ticket_id}")
        builder.button(text="✅ Закрыть", callback_data=f"ticket_close:{ticket_id}")
    else:
        builder.button(text="📝 Написать сообщение", callback_data=f"ticket_write:{ticket_id}")
    builder.button(text="🔙 Назад", callback_data="back")
    builder.adjust(1 if admin_mode else 1)
    return builder.as_markup()
