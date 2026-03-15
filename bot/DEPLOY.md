# 🚀 Деплой Telegram-бота на VPS

Эта инструкция описывает установку и настройку Telegram-бота AlufProxy на VPS сервер (Ubuntu 22.04+).

---

## 📋 Требования

- VPS с Ubuntu 22.04+ (тот же где установлен XRay)
- Python 3.9+
- Telegram-бот (токен от @BotFather)
- Root доступ к серверу

---

## 1️⃣ Подготовка

### 1.1 Создание бота

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot`
3. Введите имя: `AlufProxy Bot`
4. Введите username: `AlufProxyBot`
5. **Сохраните токен** (выглядит как `123456789:ABCdef...`)

### 1.2 Получение Admin ID

1. Откройте [@userinfobot](https://t.me/userinfobot)
2. Нажмите "Start"
3. **Сохраните ваш ID** (например, `123456789`)

---

## 2️⃣ Установка на VPS

### 2.1 Подключение к серверу

```bash
ssh root@your-vps-ip
```

### 2.2 Обновление системы

```bash
apt update && apt upgrade -y
```

### 2.3 Установка зависимостей

```bash
apt install -y python3 python3-pip python3-venv git
```

### 2.4 Создание директории

```bash
mkdir -p /root/alufproxy/bot
cd /root/alufproxy/bot
```

### 2.5 Копирование файлов

#### Вариант A: Через Git (рекомендуется)

```bash
git clone https://github.com/your-username/alufproxy.git /tmp/alufproxy
cp -r /tmp/alufproxy/bot/* /root/alufproxy/bot/
cd /root/alufproxy/bot
```

#### Вариант B: Через SCP (с локального компьютера)

```bash
# На локальном компьютере (не на VPS!)
scp -r bot/ root@your-vps-ip:/root/alufproxy/bot/
```

#### Вариант C: Через nano (вручную)

```bash
# Создайте файлы вручную через nano
nano railway_bot.py
# Вставьте содержимое файла
# Ctrl+O, Enter, Ctrl+X
```

---

## 3️⃣ Настройка

### 3.1 Создание виртуального окружения

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3.2 Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3.3 Создание .env файла

```bash
nano .env
```

Вставьте следующее (замените на свои значения):

```bash
# Telegram Bot Token (от @BotFather)
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Server настройки (домен вашего VPS с XRay)
SERVER_DOMAIN=proxy.example.com
SERVER_PORT=443
VLESS_PORT=443

# База данных
DATABASE_PATH=data/bot.db

# Admin IDs (ваш Telegram ID, узнать через @userinfobot)
ADMIN_IDS=123456789

# Тарифы
TRIAL_DAYS=3
DEFAULT_SUBSCRIPTION_DAYS=30

# VLESS Reality настройки
VLESS_SNI=gosuslugi.ru
FALLBACK_DOMAIN=gosuslugi.ru

# Поддержка (true/false)
SUPPORT_ENABLED=true
```

**Сохраните:** `Ctrl+O` → `Enter` → `Ctrl+X`

### 3.4 Создание директории для БД

```bash
mkdir -p data
```

---

## 4️⃣ Настройка systemd сервиса

### 4.1 Создание файла сервиса

```bash
nano /etc/systemd/system/alufbot.service
```

Вставьте следующее:

```ini
[Unit]
Description=AlufProxy Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/alufproxy/bot
Environment="PATH=/root/alufproxy/bot/venv/bin"
ExecStart=/root/alufproxy/bot/venv/bin/python3 railway_bot.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=alufbot

[Install]
WantedBy=multi-user.target
```

**Сохраните:** `Ctrl+O` → `Enter` → `Ctrl+X`

### 4.2 Перезагрузка systemd

```bash
systemctl daemon-reload
```

### 4.3 Включение автозапуска

```bash
systemctl enable alufbot
```

### 4.4 Запуск бота

```bash
systemctl start alufbot
```

### 4.5 Проверка статуса

```bash
systemctl status alufbot
```

**Должно быть:** `active (running)`

---

## 5️⃣ Настройка команд бота

Отправьте @BotFather команду `/setcommands` и выберите бота.

Введите список команд:

```
start - Запустить бота
get_key - Получить ключ подключения
my_keys - Мои ключи
support - Поддержка
help - Инструкция
admin - Админ-панель (для админов)
```

---

## 6️⃣ Тестирование

### 6.1 Проверка работы

1. Откройте бота в Telegram
2. Нажмите `/start`
3. Должно появиться приветствие с кнопками

### 6.2 Проверка генерации ключей

1. Нажмите "🔑 Получить ключ"
2. Должен сгенерироваться VLESS ключ

### 6.3 Проверка поддержки

1. Нажмите "📞 Поддержка"
2. Напишите сообщение
3. Админ должен получить уведомление

---

## 7️⃣ Управление ботом

### Просмотр логов

```bash
# В реальном времени
journalctl -u alufbot -f

# Последние 50 строк
journalctl -u alufbot -n 50

# За сегодня
journalctl -u alufbot --since today
```

### Перезапуск

```bash
systemctl restart alufbot
```

### Остановка

```bash
systemctl stop alufbot
```

### Запуск

```bash
systemctl start alufbot
```

### Отключение автозапуска

```bash
systemctl disable alufbot
```

---

## 8️⃣ Обновление бота

```bash
# Перейдите в директорию бота
cd /root/alufproxy/bot

# Если через Git
git pull origin main

# Если вручную - скопируйте новые файлы
# ...

# Перезапустите бота
systemctl restart alufbot

# Проверьте логи
journalctl -u alufbot -f
```

---

## 9️⃣ Админ-панель

### Команды администратора:

| Команда | Описание |
|---------|----------|
| `/admin` | Открыть админ-панель |
| `/add_time <user_id> <days>` | Продлить подписку |
| `/ban <user_id>` | Забанить пользователя |
| `/unban <user_id>` | Разбанить пользователя |
| `/cancel` | Выйти из режима ответа |

### Режим поддержки:

1. Пользователь пишет в поддержку через `/support`
2. Админ получает уведомление с кнопками
3. Админ нажимает "✍️ Ответить"
4. Пишет сообщение — оно отправляется пользователю
5. После ответа админ может закрыть обращение "✅ Закрыть"

---

## 🔟 Решение проблем

### Бот не запускается

```bash
# Проверьте статус
systemctl status alufbot

# Проверьте логи
journalctl -u alufbot -f

# Проверьте .env
cat .env

# Проверьте Python
which python3
python3 --version
```

### Ошибка: "No module named 'aiogram'"

```bash
# Активируйте venv
cd /root/alufproxy/bot
source venv/bin/activate

# Переустановите зависимости
pip install -r requirements.txt

# Перезапустите бота
systemctl restart alufbot
```

### Ошибка: "Unauthorized"

- Проверьте токен бота в `.env`
- Убедитесь, что бот не заблокирован

### Бот не отвечает на команды

- Проверьте логи: `journalctl -u alufbot -f`
- Проверьте, что бот запущен: `systemctl status alufbot`
- Проверьте токен в `.env`

### Обращения не приходят админу

- Проверьте `ADMIN_IDS` в `.env`
- Убедитесь, что ID правильный (через @userinfobot)
- Проверьте, что админ не заблокировал бота

### Ошибка: "DATABASE_PATH: Read-only file system"

```bash
# Создайте директорию
mkdir -p data
chmod 755 data

# Перезапустите бота
systemctl restart alufbot
```

---

## 📁 Структура файлов

```
/root/alufproxy/bot/
├── railway_bot.py        # Основной файл бота (polling)
├── config.py             # Конфигурация
├── database.py           # SQLite БД
├── .env                  # Переменные окружения (не коммитить!)
├── .env.example          # Пример .env
├── requirements.txt      # Зависимости
├── data/
│   └── bot.db            # База данных (создаётся автоматически)
├── handlers/
│   ├── start.py          # /start, /help, /support
│   ├── get_key.py        # Генерация ключей
│   └── support.py        # Поддержка + админ
├── keyboards/
│   └── inline.py         # Inline-кнопки
└── utils/
    └── key_generator.py  # Генерация VLESS ключей
```

---

## 🔧 Полезные команды

```bash
# Статус бота
systemctl status alufbot

# Логи в реальном времени
journalctl -u alufbot -f

# Перезапуск
systemctl restart alufbot

# Проверка процесса
ps aux | grep railway_bot

# Проверка порта (если используется webhook)
netstat -tlnp | grep 8000

# Проверка БД
sqlite3 data/bot.db "SELECT * FROM users LIMIT 5;"
```

---

## 📞 Поддержка

- **Telegram разработчика:** [@a_skale](https://t.me/a_skale)
- **GitHub:** [Skalettson](https://github.com/Skalettson)

---

## 📊 Мониторинг

### Проверка использования ресурсов

```bash
# Использование памяти
ps aux | grep railway_bot | awk '{print $6}'

# Использование CPU
top -p $(pgrep -f railway_bot)

# Размер БД
ls -lh data/bot.db
```

### Резервное копирование БД

```bash
# Создать бэкап
cp data/bot.db data/bot.db.backup.$(date +%Y%m%d)

# Восстановить из бэкапа
cp data/bot.db.backup.20260314 data/bot.db
systemctl restart alufbot
```

---

## ✅ Чек-лист после установки

- [ ] Бот отвечает на `/start`
- [ ] Генерация ключей работает
- [ ] Поддержка работает
- [ ] Админ получает уведомления
- [ ] Бот перезапускается после перезагрузки сервера
- [ ] Логи пишутся корректно

---

**Готово!** Бот запущен и работает. 🎉
