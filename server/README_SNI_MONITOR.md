# SNI Monitor для XRay Reality

Автоматическая система мониторинга и переключения SNI доменов для XRay Reality.

## 📋 Описание

Проблема: XRay Reality использует SNI (Server Name Indication) для маскировки трафика под обычный HTTPS. Если домен SNI блокируется провайдером, подключение перестаёт работать.

Решение: Автоматический мониторинг доступности SNI доменов и переключение на альтернативные при блокировке.

## 🚀 Возможности

- ✅ **100+ доменов** в пуле (РФ + международные)
- ✅ **Авто-мониторинг** каждые 2 минуты
- ✅ **Мгновенное переключение** при блокировке (<3 сек)
- ✅ **Приоритизация** доменов (5 уровней)
- ✅ **Логирование** всех переключений
- ✅ **Уведомления** админа (опционально)
- ✅ **TLS ping проверка** — только рабочие домены

## 📁 Структура файлов

```
server/
├── sni_domains.py          # База из 100+ SNI доменов
├── check_sni.py            # Скрипт проверки доступности
├── sni_updater.py          # Авто-обновление SNI
├── install_sni_monitor.sh  # Скрипт установки
├── systemd/
│   ├── sni-monitor.service # Systemd сервис
│   └── sni-monitor.timer   # Timer для запуска каждые 2 мин
└── config.json             # Конфиг XRay (обновлённый)
```

## 🛠️ Установка на сервер

### 1. Клонирование/копирование файлов

```bash
# На сервере
cd /opt
git clone <repo_url> alufproxy
cd alufproxy/server
```

### 2. Запуск установщика

```bash
sudo bash install_sni_monitor.sh
```

Скрипт:
- Создаст директории `/opt/alufproxy`, `/var/log/xray`, `/var/lib/xray`
- Скопирует файлы
- Установит systemd сервисы
- Запустит таймер

### 3. Проверка статуса

```bash
# Статус таймера
systemctl status sni-monitor.timer

# Просмотр логов
journalctl -u sni-monitor.service -f

# Логи смены SNI
tail -f /var/log/xray/sni_changes.log
```

## 📖 Использование

### Проверка доступных SNI

```bash
# Быстрая проверка (топ-20 доменов)
python3 /opt/alufproxy/check_sni.py --quick

# Проверка доменов с приоритетом 5
python3 /opt/alufproxy/check_sni.py --priority 5 --top 20

# Экспорт результатов в JSON
python3 /opt/alufproxy/check_sni.py --priority 5 --output results.json
```

### Принудительное обновление SNI

```bash
# Принудительная смена на рабочий домен
python3 /opt/alufproxy/sni_updater.py --force

# С уведомлением админа
python3 /opt/alufproxy/sni_updater.py --force --notify

# Сухой прогон (без изменений)
python3 /opt/alufproxy/sni_updater.py --dry-run
```

### Просмотр статуса

```bash
python3 /opt/alufproxy/sni_updater.py --status
```

## ⚙️ Настройка

### Изменение интервала мониторинга

Отредактируйте `/etc/systemd/system/sni-monitor.timer`:

```ini
[Timer]
OnBootSec=1min
OnUnitActiveSec=2min  # Изменить на нужное значение
```

Перезапустите таймер:

```bash
systemctl daemon-reload
systemctl restart sni-monitor.timer
```

### Добавление своих доменов

Отредактируйте `/opt/alufproxy/sni_domains.py`:

```python
SNI_DOMAINS = {
    "priority_5": [
        "www.microsoft.com",
        # Добавьте свои домены
        "your-domain.com",
    ],
    # ...
}
```

### Настройка уведомлений

Отредактируйте функцию `send_notification()` в `/opt/alufproxy/sni_updater.py`:

```python
def send_notification(self, old_dest: str, new_dest: str):
    """Отправка уведомления в Telegram"""
    import requests
    
    bot_token = "YOUR_BOT_TOKEN"
    chat_id = "YOUR_CHAT_ID"
    
    message = f"🔄 AlufProxy: Смена SNI\nСтарый: {old_dest}\nНовый: {new_dest}"
    
    requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={"chat_id": chat_id, "text": message}
    )
```

## 📊 Пул доменов

### Приоритет 5⭐ (Технологические гиганты)
- www.microsoft.com, microsoft.com
- www.apple.com, apple.com
- gateway.icloud.com, itunes.apple.com
- www.nvidia.com, www.cisco.com, www.amd.com

### Приоритет 4⭐ (Европейские, стриминговые)
- www.bbc.co.uk, www.theguardian.com
- www.netflix.com, www.spotify.com
- www.telegram.org, www.whatsapp.com

### Приоритет 3⭐ (РФ, e-commerce)
- www.gosuslugi.ru, www.sberbank.ru
- www.yandex.ru, www.vk.com
- www.amazon.com, www.visa.com

## 🔧 Генерация конфига с автовыбором SNI

```bash
# Автоматический выбор рабочего SNI
python3 generate_config.py --auto-sni --host your-domain.com

# С указанием таймаута
python3 generate_config.py --auto-sni --timeout 10
```

## 📝 Логи

### Расположение логов

- **Логи смены SNI:** `/var/log/xray/sni_changes.log`
- **Systemd логи:** `journalctl -u sni-monitor.service`
- **Состояние:** `/var/lib/xray/sni_state.json`

### Формат логов

```
2026-03-16 20:30:15,123 [INFO] ============================================================
2026-03-16 20:30:15,124 [INFO]   SNI Updater - Проверка и обновление SNI
2026-03-16 20:30:15,124 [INFO] ============================================================
2026-03-16 20:30:15,125 [INFO] Текущий SNI: www.microsoft.com
2026-03-16 20:30:15,125 [INFO] Текущий dest: www.microsoft.com
2026-03-16 20:30:15,126 [INFO] Проверка доступности www.microsoft.com...
2026-03-16 20:30:15,456 [INFO] ✅ Домен www.microsoft.com доступен
```

## 🚨 Решение проблем

### XRay не перезапускается

```bash
# Проверка конфига
/usr/local/bin/xray -test -c /etc/xray/config.json

# Статус XRay
systemctl status xray

# Логи XRay
journalctl -u xray -n 50
```

### SNI не переключается

```bash
# Проверка доступности текущего SNI
curl -kI https://current-sni.com:443

# Принудительное переключение
python3 /opt/alufproxy/sni_updater.py --force

# Проверка логов
tail -n 100 /var/log/xray/sni_changes.log
```

### Таймер не запускается

```bash
# Перезапуск таймера
systemctl daemon-reload
systemctl restart sni-monitor.timer

# Проверка статуса
systemctl list-timers | grep sni-monitor
```

## 📈 Мониторинг

### Дашборд (опционально)

Создайте скрипт для вывода статуса:

```bash
#!/bin/bash
echo "=== SNI Monitor Status ==="
echo
cat /var/lib/xray/sni_state.json | jq '.'
echo
echo "=== Последние смены SNI ==="
tail -n 10 /var/log/xray/sni_changes.log
```

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи
2. Запустите в режиме `--dry-run`
3. Проверьте доступность доменов через `check_sni.py`

## 📄 Лицензия

MIT License
