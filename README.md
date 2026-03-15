# AlufProxy — Проксификатор для обхода блокировок

**AlufProxy** — это комплексное решение для обхода интернет-блокировок в России. Включает Telegram-бота для выдачи ключей, сервер на базе XRay VLESS Reality, и ПК-клиент для Windows.

## 📋 Содержание

- [Возможности](#возможности)
- [Архитектура](#архитектура)
- [Быстрый старт](#быстрый-старт)
- [Установка и настройка](#установка-и-настройка)
- [Использование](#использование)
- [Юридическая информация](#юридическая-информация)

---

## 🚀 Возможности

### Telegram-бот (@AlufProxyBot)
- ✅ Автоматическая выдача ключей VLESS Reality
- ✅ Пробный период (3 дня)
- ✅ Управление подписками
- ✅ Админ-панель
- ✅ Статистика использования

### Сервер (VPS)
- ✅ VLESS Reality — маскировка под обычный HTTPS
- ✅ Fallback на gosuslugi.ru (или другой домен)
- ✅ Обход DPI блокировок
- ✅ Автоматическая установка скриптом

### ПК-клиент (Windows)
- ✅ Простой GUI интерфейс
- ✅ Tray-иконка в системном трее
- ✅ SOCKS5 прокси на локальном порту
- ✅ Поддержка VLESS Reality ключей
- ✅ Опциональный DPI-обход (Zapret/GoodbyeDPI)
- ✅ Автозапуск с Windows

---

## 🏗 Архитектура

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│  Telegram Bot   │ ──────► │   Server (VPS)  │ ◄────── │   PC Client     │
│  (aiogram +     │  ключи  │   XRay VLESS    │  трафик │   (Windows)     │
│   FastAPI)      │         │   Reality       │         │   SOCKS5 proxy  │
└─────────────────┘         └─────────────────┘         └─────────────────┘
         │                          │                          │
         ▼                          ▼                          ▼
    SQLite БД                  VPS (Ubuntu)              Пользователь
    (пользователи,             (Нидерланды,             (Telegram Desktop,
     ключи)                     Финляндия)                браузер, игры)
```

---

## 🎯 Быстрый старт

### 1. Развёртывание сервера (VPS)

```bash
# Арендуем VPS (Нидерланды, ~€5/мес)
# Например: Aeza, VDSina, Timeweb

# Копируем скрипт установки на сервер
scp server/install.sh root@your-vps-ip:/root/

# Выполняем установку
ssh root@your-vps-ip
cd /root
chmod +x install.sh

# Запускаем с настройками
DOMAIN=proxy.example.com \
EMAIL=admin@example.com \
SNI_DOMAIN=gosuslugi.ru \
./install.sh
```

### 2. Настройка Telegram-бота

```bash
# Создаём бота через @BotFather в Telegram
# Получаем токен

# Копируем .env.example в .env
cd bot/
cp .env.example .env

# Редактируем .env
nano .env
# BOT_TOKEN=your_token_here
# SERVER_DOMAIN=proxy.example.com
# ADMIN_IDS=your_telegram_id

# Деплоим на Vercel
vercel --prod
```

### 3. Установка ПК-клиента

```bash
# Скачиваем готовый .exe из релизов
# Или собираем самостоятельно:

cd client/
pip install -r requirements.txt
pyinstaller packaging/windows.spec --clean
```

---

## 📖 Подробная документация

- [Настройка бота](docs/bot_setup.md)
- [Настройка сервера](docs/server_setup.md)
- [Настройка клиента](docs/client_setup.md)

---

## 🔧 Структура проекта

```
AlufProxyfier/
├── bot/                    # Telegram-бот
│   ├── bot.py             # Основной файл
│   ├── config.py          # Конфигурация
│   ├── database.py        # SQLite БД
│   ├── handlers/          # Обработчики команд
│   ├── keyboards/         # Inline-клавиатуры
│   ├── utils/             # Утилиты (генерация ключей)
│   ├── api/               # Vercel serverless функции
│   └── requirements.txt
│
├── server/                # Серверная часть
│   ├── install.sh         # Скрипт установки XRay
│   ├── key_api.py         # API для генерации ключей
│   ├── config.json        # Шаблон конфига XRay
│   └── requirements.txt
│
├── client/                # ПК-клиент
│   ├── aluf_client.py     # GUI приложение
│   ├── vless_protocol.py  # VLESS утилиты
│   ├── socks5_server.py   # SOCKS5 прокси
│   ├── dpi_helper.py      # DPI-обход (Zapret)
│   ├── packaging/         # PyInstaller спецификации
│   └── requirements.txt
│
└── docs/                  # Документация
    ├── README.md
    ├── bot_setup.md
    ├── server_setup.md
    └── client_setup.md
```

---

## 💰 Стоимость

| Компонент | Стоимость | Примечание |
|-----------|-----------|------------|
| VPS | €5-10/мес | Нидерланды, Финляндия |
| Домен | €0-5/год | Можно бесплатный (dynu.com) |
| Vercel | €0 | Бесплатный тариф |
| **Итого** | **€5-15/мес** | Зависит от VPS |

---

## ⚠️ Важные замечания

1. **VLESS Reality** маскирует трафик под обычный HTTPS, что делает его устойчивым к DPI-блокировкам
2. **Не делитесь ключами** — каждый ключ персональный
3. **При блокировке домена** — смените домен и перевыпустите сертификаты
4. **Для обхода блокировок Discord/YouTube** используйте встроенный DPI-обход

---

## ⚖️ Юридическая информация

### Лицензия

Программное обеспечение предоставляется по **Лицензии с полными правами**.

📄 **[Полный текст лицензии](LICENSE)**

### Ваши права

| Право | Описание |
|-------|----------|
| ✅ Использовать | Для любых целей, включая коммерческие |
| ✅ Модифицировать | Изменять исходный код |
| ✅ Распространять | Передавать третьим лицам |
| ✅ Сублицензировать | Предоставлять права дальше |

### Важные документы

- 📋 **[Условия использования](TERMS_OF_USE.md)** — права и обязанности, отказ от ответственности
- 🔒 **[Политика конфиденциальности](PRIVACY_POLICY.md)** — сбор и использование данных
- 📜 **[Лицензия](LICENSE)** — полные права на использование

### Отказ от ответственности

**РАЗРАБОТЧИКИ ALUFPROXY НЕ НЕСУТ ОТВЕТСТВЕННОСТИ ЗА ДЕЙСТВИЯ КЛИЕНТОВ.**

Вы используете Программное обеспечение на свой страх и риск. Подробнее см. [Условия использования](TERMS_OF_USE.md).

---

## 📞 Поддержка и контакты

- **Telegram бот:** [@AlufProxyBot](https://t.me/AlufProxyBot)
- **Telegram разработчика:** [@a_skale](https://t.me/a_skale)
- **GitHub:** [Skalettson](https://github.com/Skalettson)
- **Issues:** [GitHub Issues](https://github.com/Skalettson/alufproxy/issues)

---

## 📄 Лицензия

MIT License с расширенными правами.

📄 **[Полный текст лицензии](LICENSE)**

---

## 🔗 Ссылки

- [XRay-core](https://github.com/XTLS/Xray-core)
- [VLESS Reality](https://github.com/XTLS/Xray-core#reality)
- [aiogram](https://docs.aiogram.dev/)
- [customtkinter](https://customtkinter.tomschimansky.com/)
