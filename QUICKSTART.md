# 🚀 Быстрый старт AlufProxy

Этот файл содержит краткую инструкцию по развёртыванию всей системы.

---

## 📋 Что нужно сделать

1. **Арендовать VPS** (€5-10/мес)
2. **Настроить сервер** (XRay VLESS Reality)
3. **Создать Telegram-бота** и задеплоить на Vercel
4. **Собрать ПК-клиент** (или скачать готовый .exe)

---

## 1️⃣ Аренда VPS

### Рекомендуемые провайдеры:
- **Aeza** — https://aeza.net/, от €5/мес, Нидерланды
- **VDSina** — https://vdsina.com/, от €5/мес, Нидерланды
- **Timeweb Cloud** — https://timeweb.cloud/, от 200₽/мес, Нидерланды

### Требования:
- Ubuntu 22.04+
- IPv4 адрес
- Root доступ

---

## 2️⃣ Настройка сервера

```bash
# 1. Подключение к VPS
ssh root@your-vps-ip

# 2. Скачивание скрипта установки
wget https://raw.githubusercontent.com/your-username/alufproxy/main/server/install.sh
chmod +x install.sh

# 3. Запуск установки
DOMAIN=proxy.example.com \
EMAIL=admin@example.com \
SNI_DOMAIN=gosuslugi.ru \
./install.sh

# 4. Сохраните ключи из вывода!
# Private Key, Public Key, Short ID
```

📖 **Подробная инструкция:** [docs/server_setup.md](docs/server_setup.md)

---

## 3️⃣ Telegram-бот

### Создание бота:
1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. `/newbot` → введите имя и username
3. Сохраните токен

### Локальная настройка:
```bash
cd bot/
cp .env.example .env
nano .env
```

Заполните `.env`:
```bash
BOT_TOKEN=your_token_from_botfather
SERVER_DOMAIN=proxy.example.com
ADMIN_IDS=your_telegram_id
```

### Деплой на Vercel:
```bash
# Установка Vercel CLI
npm install -g vercel

# Вход
vercel login

# Деплой
vercel --prod
```

### Настройка Environment Variables в Vercel:
- `BOT_TOKEN` — токен бота
- `SERVER_DOMAIN` — домен сервера
- `SERVER_PORT` — порт (443)
- `ADMIN_IDS` — ваш Telegram ID

📖 **Подробная инструкция:** [docs/bot_setup.md](docs/bot_setup.md)

---

## 4️⃣ ПК-клиент

### Вариант A: Готовый .exe
Скачайте из [Releases](https://github.com/your-username/alufproxy/releases)

### Вариант B: Сборка самостоятельно
```bash
cd client/
pip install -r requirements.txt
pip install pyinstaller
pyinstaller packaging/windows.spec --clean
```

Готовый файл: `dist/AlufProxy.exe`

### Использование:
1. Откройте бота, получите ключ
2. Запустите клиент
3. Вставьте ключ
4. Нажмите "Подключиться"

📖 **Подробная инструкция:** [docs/client_setup.md](docs/client_setup.md)

---

## ✅ Проверка работы

### 1. Сервер
```bash
# Проверка сервиса
systemctl status xray

# Проверка порта
netstat -tlnp | grep 443
```

### 2. Бот
- Откройте бота в Telegram
- `/start` — должно появиться приветствие
- "🔑 Получить ключ" — должен сгенерироваться ключ

### 3. Клиент
- Вставьте ключ
- "▶️ Подключиться" — индикатор станет "🟢 Подключено"
- Проверьте IP: https://2ip.ru/

---

## 💰 Итоговая стоимость

| Компонент | Стоимость |
|-----------|-----------|
| VPS | €5-10/мес |
| Домен | €0-5/год (можно бесплатный) |
| Vercel | €0 (бесплатно) |
| **Итого** | **€5-15/мес** |

---

## 🔗 Файлы проекта

```
AlufProxyfier/
├── README.md              # Основная документация
├── QUICKSTART.md          # Этот файл
├── .gitignore
│
├── bot/                   # Telegram-бот
│   ├── README.md
│   ├── bot.py
│   ├── config.py
│   ├── database.py
│   ├── requirements.txt
│   └── ...
│
├── server/                # Сервер (VPS)
│   ├── install.sh
│   ├── key_api.py
│   ├── config.json
│   └── requirements.txt
│
├── client/                # ПК-клиент
│   ├── aluf_client.py
│   ├── vless_protocol.py
│   ├── socks5_server.py
│   ├── dpi_helper.py
│   └── requirements.txt
│
└── docs/                  # Документация
    ├── server_setup.md
    ├── bot_setup.md
    └── client_setup.md
```

---

## ⚠️ Важные замечания

1. **VLESS Reality** маскирует трафик под обычный HTTPS — это обходит DPI
2. **Не делитесь ключами** — каждый ключ персональный
3. **При блокировке домена** — смените домен и перевыпустите сертификаты
4. **Backup ключей** — сохраните Private Key и Short ID в надёжном месте

---

## 📞 Поддержка

- Telegram: @aluf_support
- GitHub Issues: https://github.com/your-username/alufproxy/issues

---

## 📚 Дополнительные ресурсы

- [XRay VLESS Reality документация](https://github.com/XTLS/Xray-core#reality)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Vercel документация](https://vercel.com/docs)
- [customtkinter документация](https://customtkinter.tomschimansky.com/)
