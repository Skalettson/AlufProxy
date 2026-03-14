# 🚀 Быстрый запуск AlufProxy для тестирования

Этот файл содержит инструкции по быстрому запуску и тестированию AlufProxy локально.

---

## 📋 Требования

- Python 3.9+
- pip
- Docker (опционально, для полного развёртывания)

---

## 🔧 Вариант 1: Локальное тестирование (рекомендуется для разработки)

### Шаг 1: Установка зависимостей

```bash
# Для бота
cd bot
pip install -r requirements.txt

# Для клиента
cd ../client
pip install -r requirements.txt

# Для сервера/API
cd ../server
pip install -r requirements.txt
```

### Шаг 2: Запуск тестов

```bash
# Запуск тестового скрипта
python test_local.py
```

Ожидаемый вывод:
```
✅ Парсинг VLESS ключа
✅ Генерация VLESS ключа
✅ Импорт модулей
✅ Сохранение конфигурации
✅ SOCKS5 сервер

Итого: 5/5 тестов пройдено
🎉 Все тесты пройдены!
```

### Шаг 3: Генерация тестовых ключей

```bash
# Генерация конфигурации
python generate_config.py --host localhost --port 443 --output test_config
```

Будут созданы файлы:
- `test_config/vless_key.txt` - VLESS ключ для клиента
- `test_config/xray_config.json` - Конфиг для сервера
- `test_config/info.json` - Полная информация

### Шаг 4: Запуск клиента (Windows)

```bash
cd client
python aluf_client.py
```

Откроется GUI окно. Вставьте VLESS ключ из `test_config/vless_key.txt`.

---

## 🐳 Вариант 2: Docker развёртывание

### Шаг 1: Подготовка

```bash
# Генерация конфигурации
python generate_config.py --host your-domain.com --output docker_config

# Копирование конфига
cp docker_config/xray_config.json docker/xray_config.json
```

### Шаг 2: Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```bash
# Telegram Bot
BOT_TOKEN=your_bot_token_from_botfather
SERVER_DOMAIN=your-domain.com
ADMIN_IDS=your_telegram_id

# API
API_KEY=your-secret-api-key

# Для docker-compose
export $(cat .env | xargs)
```

### Шаг 3: Запуск Docker

```bash
docker-compose up -d
```

Проверка статуса:
```bash
docker-compose ps
docker-compose logs -f
```

---

## 🖥 Вариант 3: Прямой запуск компонентов

### Запуск бота (локально)

```bash
cd bot
cp .env.example .env
# Редактируем .env, вставляем BOT_TOKEN
python bot.py
```

### Запуск API сервера

```bash
cd server
python key_api.py
```

API будет доступно на `http://localhost:8000`

Проверка:
```bash
curl http://localhost:8000/health
```

### Запуск клиента

```bash
cd client
python aluf_client.py
```

---

## 🧪 Тестирование функциональности

### Тест 1: Парсинг ключа

```bash
python -c "
from client.vless_protocol import VLESSKey
key = VLESSKey('vless://55555555-5555-5555-5555-555555555555@proxy.example.com:443?encryption=none&security=reality&sni=gosuslugi.ru&fp=chrome&pbk=key&sid=id&type=tcp')
print('Valid:', key.is_valid)
print('Host:', key.host)
"
```

### Тест 2: SOCKS5 прокси

```bash
# Запуск SOCKS5 сервера
python -c "
import asyncio
from client.socks5_server import SOCKS5Server

async def main():
    server = SOCKS5Server('127.0.0.1', 19080)
    print('SOCKS5 запущен на 127.0.0.1:19080')
    await server.start()

asyncio.run(main())
```

В другом терминале:
```bash
# Проверка через curl
curl -x socks5h://127.0.0.1:19080 https://httpbin.org/ip
```

### Тест 3: VLESS клиент

```bash
python -c "
import asyncio
from client.vless_client import VLESSRealityClient

async def test():
    client = VLESSRealityClient(
        uuid='55555555-5555-5555-5555-555555555555',
        host='your-server.com',
        port=443,
        sni='gosuslugi.ru',
        public_key='your-public-key',
        short_id='your-short-id'
    )
    
    if await client.connect():
        print('✅ Подключение успешно')
        await client.close()
    else:
        print('❌ Подключение не удалось')

asyncio.run(test())
```

---

## 📊 Проверка работы

### Чеклист работоспособности

- [ ] Бот отвечает на `/start`
- [ ] Бот генерирует ключи через "🔑 Получить ключ"
- [ ] Клиент принимает VLESS ключ
- [ ] Клиент запускает SOCKS5 прокси
- [ ] SOCKS5 прокси слушает порт 1080
- [ ] Трафик идёт через VLESS сервер

### Команды для проверки

```bash
# Проверка SOCKS5 порта
netstat -an | grep 1080

# Проверка подключения (через proxychains или curl)
curl -x socks5h://127.0.0.1:1080 https://httpbin.org/ip

# Проверка логов
# Windows: Get-Content "$env:APPDATA\AlufProxy\alufproxy.log"
# Linux: tail -f ~/.config/AlufProxy/alufproxy.log
```

---

## ⚠️ Решение проблем

### Ошибка: "ModuleNotFoundError"

```bash
# Установите зависимости
pip install -r client/requirements.txt
pip install -r bot/requirements.txt
pip install -r server/requirements.txt
```

### Ошибка: "Address already in use"

```bash
# Найдите процесс на порту
# Windows:
netstat -ano | findstr :1080
taskkill /F /PID <PID>

# Linux:
lsof -i :1080
kill <PID>
```

### Ошибка: "Invalid VLESS key"

Убедитесь, что ключ содержит все необходимые параметры:
- `uuid`
- `host` и `port`
- `security=reality`
- `sni`
- `pbk` (public key)
- `sid` (short id)

### Бот не отвечает

1. Проверьте токен в `.env`
2. Убедитесь, что бот не заблокирован
3. Проверьте логи: `python bot.py` (в режиме polling)

---

## 📁 Структура файлов для тестирования

```
AlufProxyfier/
├── test_local.py           # Главный тестовый скрипт
├── generate_config.py      # Генератор конфигов
├── docker-compose.yml      # Docker развёртывание
│
├── bot/
│   ├── bot.py             # Telegram бот
│   ├── requirements.txt
│   └── .env.example
│
├── server/
│   ├── key_api.py         # API для ключей
│   ├── install.sh         # Установка на VPS
│   └── requirements.txt
│
├── client/
│   ├── aluf_client.py     # GUI клиент
│   ├── vless_client.py    # VLESS клиент
│   ├── socks5_server.py   # SOCKS5 сервер
│   ├── vless_protocol.py  # VLESS утилиты
│   └── requirements.txt
│
└── docker/
    └── xray_config.json   # Конфиг для Docker
```

---

## 🎯 Следующие шаги после тестирования

1. **Арендовать VPS** для сервера
2. **Настроить домен** (или использовать динамический)
3. **Получить SSL сертификаты** (acme.sh)
4. **Развернуть сервер** через `install.sh`
5. **Задеплоить бота** на Vercel
6. **Собрать клиент** в .exe

---

## 📞 Поддержка

- Telegram: @aluf_support
- GitHub Issues: https://github.com/your-username/alufproxy/issues
