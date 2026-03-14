# Настройка Telegram-бота AlufProxy

## Требования

- Python 3.9+
- Токен Telegram-бота (от @BotFather)
- Vercel аккаунт (для деплоя)

## Шаг 1: Создание бота

1. Откройте Telegram, найдите [@BotFather](https://t.me/BotFather)
2. Отправьте команду `/newbot`
3. Введите имя бота (например, `AlufProxy Bot`)
4. Введите username бота (например, `AlufProxyBot`)
5. Сохраните полученный токен (выглядит как `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

## Шаг 2: Настройка проекта

```bash
cd bot/

# Копируем .env.example в .env
cp .env.example .env

# Редактируем .env
nano .env
```

### Переменные окружения (.env)

```bash
# Токен бота (от @BotFather)
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# Сервер (домен вашего VPS)
SERVER_DOMAIN=proxy.example.com
SERVER_PORT=443

# База данных
DATABASE_PATH=data/bot.db

# Admin IDs (ваш Telegram ID, можно узнать у @userinfobot)
ADMIN_IDS=123456789

# Тарифы
TRIAL_DAYS=3
DEFAULT_SUBSCRIPTION_DAYS=30

# VLESS Reality настройки
VLESS_SNI=gosuslugi.ru
FALLBACK_DOMAIN=gosuslugi.ru
```

## Шаг 3: Локальное тестирование

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск бота (режим polling)
python bot.py
```

### Проверка команд

Откройте бота в Telegram и проверьте команды:

- `/start` — Приветствие, регистрация
- `/help` — Инструкция
- `/get_key` — Получить ключ (через inline-кнопку)
- `/my_keys` — Мои ключи

## Шаг 4: Деплой на Vercel

### Вариант A: Через Vercel CLI

```bash
# Установка Vercel CLI
npm install -g vercel

# Вход в аккаунт
vercel login

# Деплой
cd bot/
vercel --prod
```

### Вариант B: Через GitHub + Vercel

1. Создайте репозиторий на GitHub
2. Запушьте код:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/your-username/alufproxy.git
   git push -u origin main
   ```

3. Подключите репозиторий на [vercel.com](https://vercel.com)
4. Настройте Environment Variables в Vercel Dashboard:
   - `BOT_TOKEN`
   - `SERVER_DOMAIN`
   - `ADMIN_IDS`
   - и другие из `.env`

5. Deploy!

## Шаг 5: Настройка webhook

После деплоя Vercel автоматически настроит webhook.

URL webhook будет: `https://your-project.vercel.app/webhook`

### Проверка webhook

```bash
# Узнать текущий webhook
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo"

# Установить webhook вручную (если нужно)
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=https://your-project.vercel.app/webhook"
```

## Шаг 6: Настройка команд бота

Отправьте @BotFather команду `/setcommands` и выберите бота.

Введите список команд:

```
start - Запустить бота
get_key - Получить ключ подключения
my_keys - Мои ключи
help - Инструкция
support - Поддержка
```

## 📊 Админ-панель

### Команды администратора

- `/admin` — Открыть админ-панель
- `/stats` — Статистика (через админ-панель)
- `/add_time <user_id> <days>` — Продлить подписку
- `/ban <user_id>` — Забанить пользователя
- `/unban <user_id>` — Разбанить пользователя

### Получение Telegram ID

1. Отправьте сообщение [@userinfobot](https://t.me/userinfobot)
2. Скопируйте свой ID
3. Добавьте в `ADMIN_IDS` в `.env`

## 🔧 База данных

Бот использует SQLite для хранения:

- Пользователей
- Ключей доступа
- Статистики

Файл БД: `data/bot.db`

### Просмотр БД

```bash
# Установка sqlite3
apt install sqlite3

# Подключение к БД
sqlite3 data/bot.db

# Просмотр таблиц
.tables

# Просмотр пользователей
SELECT * FROM users;

# Просмотр ключей
SELECT * FROM keys;
```

## ⚠️ Решение проблем

### Ошибка: "Unauthorized"
- Проверьте токен бота в `.env`
- Убедитесь, что бот не заблокирован

### Ошибка: "Webhook failed"
- Проверьте URL webhook
- Убедитесь, что Vercel деплой успешен

### Бот не отвечает
- Проверьте логи в Vercel Dashboard
- Проверьте, установлен ли webhook

### Ошибка генерации ключа
- Проверьте `SERVER_DOMAIN` в `.env`
- Убедитесь, что сервер доступен

## 📁 Структура файлов бота

```
bot/
├── bot.py              # Основной файл
├── config.py           # Конфигурация
├── database.py         # SQLite БД
├── requirements.txt    # Зависимости
├── vercel.json         # Vercel конфиг
├── .env.example        # Пример .env
├── handlers/
│   ├── start.py        # /start, /help
│   ├── get_key.py      # /get_key, /my_keys
│   └── admin.py        # Админ-команды
├── keyboards/
│   └── inline.py       # Inline-кнопки
├── utils/
│   └── key_generator.py # Генерация ключей
└── api/
    └── index.py        # Vercel serverless функция
```

## 🔗 Полезные ссылки

- [aiogram документация](https://docs.aiogram.dev/)
- [Vercel документация](https://vercel.com/docs)
- [Telegram Bot API](https://core.telegram.org/bots/api)
