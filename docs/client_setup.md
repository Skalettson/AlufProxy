# Настройка ПК-клиента AlufProxy

## Требования

- Windows 10/11
- Python 3.9+ (для запуска из исходников)
- VLESS ключ от Telegram-бота

## Быстрый старт

### Вариант 1: Готовый .exe (рекомендуется)

1. Скачайте последнюю версию из [Releases](https://github.com/your-username/alufproxy/releases)
2. Запустите `AlufProxy.exe`
3. Вставьте VLESS ключ из бота
4. Нажмите "Подключиться"

### Вариант 2: Запуск из исходников

```bash
# Клонирование репозитория
git clone https://github.com/your-username/alufproxy.git
cd alufproxy/client

# Установка зависимостей
pip install -r requirements.txt

# Запуск
python aluf_client.py
```

## 📖 Использование

### 1. Получение ключа

1. Откройте Telegram-бота (@AlufProxyBot)
2. Нажмите "🔑 Получить ключ"
3. Скопируйте полученный VLESS ключ

### 2. Подключение

1. Запустите AlufProxy Client
2. Вставьте ключ в поле "VLESS ключ подключения"
3. Настройте параметры (опционально):
   - SOCKS5 порт (по умолчанию 1080)
   - Автозапуск
   - DPI-обход
4. Нажмите "▶️ Подключиться"

### 3. Проверка подключения

Индикатор изменится на "🟢 Подключено"

Теперь трафик идёт через SOCKS5 прокси на `127.0.0.1:1080`

## ⚙️ Настройка приложений

### Telegram Desktop

1. Настройки → Продвинутые → Тип подключения
2. Добавить прокси:
   - Тип: **SOCKS5**
   - Сервер: **127.0.0.1**
   - Порт: **1080** (или ваш)
   - Логин/Пароль: оставить пустыми

### Браузер (Firefox)

1. Настройки → Прокси
2. Настройка прокси:
   - SOCKS5: **127.0.0.1**
   - Порт: **1080**
   - SOCKS5 v5

### Chrome/Edge (через расширение)

Установите расширение типа "Proxy SwitchyOmega" и настройте:
- Protocol: SOCKS5
- Server: 127.0.0.1
- Port: 1080

## 🔧 Настройки клиента

### SOCKS5 порт

Порт локального прокси. По умолчанию **1080**.

Если порт занят, измените на другой (например, 9050).

### Автозапуск с Windows

При включении клиент автоматически запускается при старте системы.

Для работы требуется ярлык в автозагрузке.

### DPI-обход (экспериментально)

Использует Zapret/GoodbyeDPI для обхода блокировок без VPN.

**Требования:**
- Наличие `winws.exe` или `goodbyedpi.exe` в папке `bin/`
- Запуск от имени администратора

**Включение:**
1. Отметьте галочку "DPI-обход"
2. Перезапустите клиент
3. Запустите от имени администратора

## 🛠 Сборка .exe

```bash
cd client/

# Установка зависимостей
pip install -r requirements.txt
pip install pyinstaller

# Сборка
pyinstaller packaging/windows.spec --clean

# Готовый файл в dist/AlufProxy.exe
```

### Требования для сборки

- Python 3.9+
- pip install pyinstaller>=6.0

## 📁 Структура файлов клиента

```
client/
├── aluf_client.py        # GUI приложение
├── vless_protocol.py     # VLESS утилиты
├── socks5_server.py      # SOCKS5 прокси
├── dpi_helper.py         # DPI-обход
├── config.example.json   # Пример конфига
├── requirements.txt      # Зависимости
└── packaging/
    └── windows.spec      # PyInstaller спецификация
```

## 📊 Логи

Логи сохраняются в:
- Windows: `%APPDATA%\AlufProxy\alufproxy.log`

Для просмотра:
```bash
# PowerShell
Get-Content "$env:APPDATA\AlufProxy\alufproxy.log" -Tail 50 -Wait
```

## ⚠️ Решение проблем

### "Неверный формат VLESS ключа"

Убедитесь, что ключ начинается с `vless://`

Пример правильного ключа:
```
vless://uuid-key@proxy.example.com:443?encryption=none&security=reality&sni=gosuslugi.ru&fp=chrome&pbk=public-key&sid=short-id&type=tcp&headerType=none#AlufProxy-abc123
```

### "Не удалось запустить прокси"

1. Проверьте, не занят ли порт 1080
2. Попробуйте другой порт (например, 9050)
3. Запустите от имени администратора

### Клиент не подключается к серверу

1. Проверьте доступность сервера:
   ```bash
   ping proxy.example.com
   ```

2. Проверьте порт:
   ```bash
   telnet proxy.example.com 443
   ```

3. Убедитесь, что ключ действителен (не истёк)

### DPI-обход не работает

1. Убедитесь, что `winws.exe` или `goodbyedpi.exe` есть в папке `bin/`
2. Запустите клиент от имени администратора
3. Проверьте брандмауэр Windows

### Трей-иконка не отображается

Перезапустите клиент. Если не помогло — переустановите:
```bash
pip uninstall pystray Pillow
pip install pystray Pillow
```

## 🔗 Интеграция с другими клиентами

Ключ VLESS совместим с:

| Клиент | Платформа | Ссылка |
|--------|-----------|--------|
| v2rayNG | Android | [GitHub](https://github.com/2dust/v2rayNG) |
| Shadowrocket | iOS | App Store |
| NekoBox | Android | [GitHub](https://github.com/MatsuriDayo/NekoBoxForAndroid) |
| Hiddify | Все | [GitHub](https://github.com/hiddify/hiddify-next) |
| Clash Verge | Все | [GitHub](https://github.com/clash-verge-rev/clash-verge-rev) |

### Импорт ключа

1. Скопируйте VLESS ключ из бота
2. В клиенте нажмите "Import from clipboard"
3. Подключитесь

## 🎯 Продвинутая настройка

### Ручное редактирование конфига

Файл: `%APPDATA%\AlufProxy\config.json`

```json
{
  "vless_key": "vless://...",
  "socks5_port": 1080,
  "socks5_host": "127.0.0.1",
  "auto_start": true,
  "dpi_bypass": false,
  "verbose": false
}
```

### Добавление в автозапуск (вручную)

1. Нажмите `Win + R`
2. Введите `shell:startup`
3. Создайте ярлык для `AlufProxy.exe`

## 📞 Поддержка

- Telegram: @aluf_support
- GitHub Issues: [ссылка]
