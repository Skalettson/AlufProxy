# 📡 Key Update API - Инструкция по установке

Автоматическая синхронизация ключей между ботом и XRay сервером.

---

## 🚀 Установка на сервер

### 1. Скопируйте файлы на сервер:

```bash
scp E:\AlufProxyfier\server\key_update_api.py root@your-vps-ip:/root/AlufProxy/AlufProxy/server/
scp E:\AlufProxyfier\server\key_update_api.service root@your-vps-ip:/root/AlufProxy/AlufProxy/server/
```

### 2. Установите зависимости:

```bash
cd /root/AlufProxy/AlufProxy/server
source venv/bin/activate
pip install fastapi uvicorn requests
```

### 3. Установите сервис:

```bash
cp key_update_api.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable key-update-api
systemctl start key-update-api
systemctl status key-update-api
```

### 4. Проверьте работу:

```bash
curl http://127.0.0.1:8081/health
```

**Должно вернуться:**
```json
{"status": "healthy", "xray": "active"}
```

---

## 🔧 Настройка бота

### Добавьте переменные окружения:

```bash
# В .env файл бота
KEY_UPDATE_API_URL=http://127.0.0.1:8081
KEY_UPDATE_API_KEY=AlufProxy-Secret-Key-Change-This-In-Production-2026!
```

### Обновите конфиг бота:

```python
# bot/config.py
KEY_UPDATE_API_URL = os.getenv("KEY_UPDATE_API_URL", "http://127.0.0.1:8081")
KEY_UPDATE_API_KEY = os.getenv("KEY_UPDATE_API_KEY", "AlufProxy-Secret-Key-Change-This-In-Production-2026!")
```

---

## 📋 Как это работает:

### 1. Пользователь нажимает "🔑 Получить ключ" в боте

### 2. Бот генерирует новые ключи:
- UUID (уникальный для каждого клиента)
- Private Key (X25519)
- Public Key
- Short ID

### 3. Бот отправляет ключи на API:
```python
POST http://127.0.0.1:8081/api/update_keys
Headers: X-API-Key: ...
Body: {
    "private_key": "...",
    "public_key": "...",
    "short_id": "...",
    "uuid": "..."
}
```

### 4. API обновляет ключи:
- `/etc/xray/keys.json` → новые ключи
- `/etc/xray/config.json` → обновляет realitySettings
- `systemctl restart xray` → перезапуск XRay

### 5. Бот получает ключ пользователю:
```
vless://uuid@domain:443?...&pbk=public_key&sid=short_id#AlufProxy
```

---

## 🔐 Безопасность

### Смените API ключ:

```bash
# В key_update_api.py
API_KEY = "Your-Super-Secret-Key-Here!"

# В bot/config.py
KEY_UPDATE_API_KEY = "Your-Super-Secret-Key-Here!"
```

### Ограничьте доступ к API:

```bash
# Firewall
ufw allow from 127.0.0.1 to any port 8081
```

---

## 📊 Логи

### API логи:
```bash
journalctl -u key-update-api -f
```

### XRay логи после обновления:
```bash
journalctl -u xray -f
```

---

## ✅ Проверка работы

### 1. Проверьте API:
```bash
curl http://127.0.0.1:8081/health
```

### 2. Получите ключ через бота:
```
/start → 🔑 Получить ключ
```

### 3. Проверьте что ключи обновились:
```bash
cat /etc/xray/keys.json
journalctl -u xray -n 10 --no-pager
```

---

## 🔧 Решение проблем

### API не запускается:
```bash
# Проверьте логи
journalctl -u key-update-api -n 50 --no-pager

# Проверьте порт
netstat -tlnp | grep 8081
```

### XRay не перезапускается:
```bash
# Проверьте конфиг
/usr/local/bin/xray test -c /etc/xray/config.json

# Проверьте статус
systemctl status xray
```

### Бот не может подключиться к API:
```bash
# Проверьте что API слушает
curl http://127.0.0.1:8081/health

# Проверьте firewall
ufw status
```

---

## 📈 Статистика

### Получить текущие ключи:
```bash
curl http://127.0.0.1:8081/api/current_keys \
  -H "X-API-Key: AlufProxy-Secret-Key-Change-This-In-Production-2026!"
```

---

**Готово!** Теперь каждый новый ключ автоматически обновляет XRay! 🎉
