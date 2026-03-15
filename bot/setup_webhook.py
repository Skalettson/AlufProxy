"""
Скрипт для настройки webhook после деплоя на Vercel
Использование: python setup_webhook.py
"""

import os
import sys
from dotenv import load_dotenv
import asyncio
from aiogram import Bot

# Загружаем переменные окружения
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
VERCEL_URL = os.getenv("VERCEL_URL")

if not BOT_TOKEN:
    print("❌ Ошибка: BOT_TOKEN не найден в .env")
    sys.exit(1)

if not VERCEL_URL:
    print("❌ Ошибка: VERCEL_URL не найден")
    print("   Получите URL из Vercel Dashboard и установите:")
    print(f"   vercel env add VERCEL_URL {VERCEL_URL}")
    sys.exit(1)

WEBHOOK_PATH = "/api/webhook"
WEBHOOK_URL = f"https://{VERCEL_URL}{WEBHOOK_PATH}"


async def setup_webhook():
    """Настройка webhook"""
    bot = Bot(token=BOT_TOKEN)
    
    try:
        print(f"🔧 Настройка webhook...")
        print(f"   URL: {WEBHOOK_URL}")
        
        # Проверяем текущий webhook
        webhook_info = await bot.get_webhook_info()
        print(f"\n📋 Текущий webhook:")
        print(f"   URL: {webhook_info.url}")
        print(f"   Ожидающих обновлений: {webhook_info.pending_update_count}")
        
        if webhook_info.url == WEBHOOK_URL:
            print(f"\n✅ Webhook уже настроен правильно!")
            return True
        
        # Устанавливаем новый webhook
        print(f"\n⚙️  Установка нового webhook...")
        await bot.set_webhook(WEBHOOK_URL)
        
        # Проверяем
        webhook_info = await bot.get_webhook_info()
        
        if webhook_info.url == WEBHOOK_URL:
            print(f"\n✅ Webhook успешно настроен!")
            print(f"   URL: {webhook_info.url}")
            return True
        else:
            print(f"\n❌ Webhook не установлен")
            print(f"   Текущий URL: {webhook_info.url}")
            return False
            
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        return False
        
    finally:
        await bot.session.close()


async def delete_webhook():
    """Удаление webhook"""
    bot = Bot(token=BOT_TOKEN)
    
    try:
        print("🗑️  Удаление webhook...")
        await bot.delete_webhook()
        
        webhook_info = await bot.get_webhook_info()
        
        if not webhook_info.url:
            print("✅ Webhook успешно удалён!")
            return True
        else:
            print(f"⚠️  Webhook всё ещё установлен: {webhook_info.url}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
        
    finally:
        await bot.session.close()


async def check_bot():
    """Проверка бота"""
    bot = Bot(token=BOT_TOKEN)
    
    try:
        me = await bot.get_me()
        print(f"\n🤖 Информация о боте:")
        print(f"   ID: {me.id}")
        print(f"   Имя: {me.first_name}")
        print(f"   Username: @{me.username}")
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    finally:
        await bot.session.close()


def main():
    print("=" * 60)
    print("  AlufProxy Bot - Настройка Webhook")
    print("=" * 60)
    print()
    
    # Проверка токена
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не найден!")
        print("   Скопируйте .env.example в .env и заполните")
        return
    
    # Проверка бота
    print("1️⃣  Проверка бота...")
    asyncio.run(check_bot())
    print()
    
    # Меню
    print("2️⃣  Выберите действие:")
    print("   1. Настроить webhook")
    print("   2. Удалить webhook")
    print("   3. Проверить статус")
    print("   4. Выход")
    print()
    
    choice = input("   Введите номер (1-4): ").strip()
    
    if choice == "1":
        success = asyncio.run(setup_webhook())
    elif choice == "2":
        success = asyncio.run(delete_webhook())
    elif choice == "3":
        print("\n📋 Проверка webhook...")
        bot = Bot(token=BOT_TOKEN)
        try:
            webhook_info = asyncio.run(bot.get_webhook_info())
            print(f"   URL: {webhook_info.url or 'не установлен'}")
            print(f"   Ожидающих обновлений: {webhook_info.pending_update_count}")
        finally:
            asyncio.run(bot.session.close())
    elif choice == "4":
        print("\n👋 Выход")
        return
    else:
        print("\n❌ Неверный выбор")
        return
    
    print()
    print("=" * 60)
    
    if success:
        print("✅ Готово!")
        print("\n📝 Теперь откройте бота в Telegram и нажмите /start")
    else:
        print("❌ Не удалось выполнить операцию")


if __name__ == "__main__":
    main()
