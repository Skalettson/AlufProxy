# ⚡ Быстрый старт Telegram-бота

## 1. Установка зависимостей

```bash
cd bot/
pip install -r requirements.txt
```

## 2. Настройка

```bash
# Копируем .env.example
cp .env.example .env

# Редактируем .env
nano .env
```

**Обязательные переменные:**
- `BOT_TOKEN` — токен от @BotFather
- `SERVER_DOMAIN` — домен вашего VPS (например, `proxy.example.com`)
- `ADMIN_IDS` — ваш Telegram ID (узнать через @userinfobot)

## 3. Локальный запуск (тестирование)

```bash
# Запуск в режиме polling
python bot.py
```

**Проверка:**
1. Откройте бота в Telegram
2. Нажмите `/start`
3. Должно появиться приветствие

## 4. Деплой на Vercel

```bash
# Установка Vercel CLI
npm install -g vercel

# Вход
vercel login

# Деплой
vercel --prod
```

**После деплоя:**
1. Скопируйте URL проекта (например, `https://alufproxy-bot.vercel.app`)
2. Установите webhook:
   ```bash
   curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://<YOUR-PROJECT>.vercel.app/api/webhook"
   ```

## 5. Проверка работы

### Тестирование основного функционала:

1. **/start** — приветствие
2. **🔑 Получить ключ** — генерация VLESS ключа
3. **📋 Мои ключи** — просмотр ключей
4. **📞 Поддержка** — создание обращения
5. **❓ Помощь** — инструкция

### Тестирование поддержки:

**Пользователь:**
1. Нажимает "📞 Поддержка"
2. Пишет сообщение
3. Получает подтверждение

**Админ:**
1. Получает уведомление о новом обращении
2. Нажимает "✍️ Ответить"
3. Пишет ответ
4. Сообщение отправляется пользователю

## 6. Админ-команды

```
/admin — Админ-панель
/add_time <user_id> <days> — Продлить подписку
/ban <user_id> — Забанить
/unban <user_id> — Разбанить
/cancel — Выйти из режима ответа
```

---

## 📁 Структура

```
bot/
├── api/index.py        # Vercel функция
├── handlers/
│   ├── start.py        # /start, /help
│   ├── get_key.py      # Ключи
│   └── support.py      # Поддержка
├── keyboards/inline.py # Кнопки
├── utils/key_generator.py
├── config.py
├── database.py
├── bot.py              # Локальный запуск
├── requirements.txt
└── vercel.json
```

---

## ⚠️ Важно

- **.env** не коммитить в Git (добавлен в .gitignore)
- **data/bot.db** создаётся автоматически
- Для работы поддержки установите `SUPPORT_ENABLED=true`
