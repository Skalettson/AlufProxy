# Настройка сервера AlufProxy (VPS)

## Требования

- VPS с IPv4 (Нидерланды, Финляндия, Германия)
- Ubuntu 22.04+
- Домен (можно бесплатный с dynu.com или no-ip.com)
- Root доступ

## Шаг 1: Аренда VPS

Рекомендуемые провайдеры:
- **Aeza** — от €5/мес, Нидерланды, Финляндия
- **VDSina** — от €5/мес, Нидерланды
- **Timeweb Cloud** — от 200₽/мес, Нидерланды

## Шаг 2: Настройка домена

### Вариант A: Платный домен (.com, .net, .org)
1. Купите домен у регистратора (Namecheap, GoDaddy)
2. Создайте A-запись: `proxy.example.com → IP вашего VPS`

### Вариант B: Бесплатный динамический домен
1. Зарегистрируйтесь на [dynu.com](https://www.dynu.com/)
2. Создайте бесплатный хост (например, `myproxy.dynu.net`)
3. Установите DDNS клиент на VPS для обновления IP

## Шаг 3: Подключение к VPS

```bash
# Подключение по SSH
ssh root@your-vps-ip

# Или используйте PuTTY на Windows
```

## Шаг 4: Установка XRay с VLESS Reality

### Автоматическая установка (рекомендуется)

```bash
# Скачиваем скрипт установки
wget https://raw.githubusercontent.com/your-repo/AlufProxyfier/main/server/install.sh
chmod +x install.sh

# Запускаем с настройками
DOMAIN=proxy.example.com \
EMAIL=admin@example.com \
SNI_DOMAIN=gosuslugi.ru \
VLESS_PORT=443 \
./install.sh
```

### Ручная установка

```bash
# 1. Обновление системы
apt update && apt upgrade -y

# 2. Установка зависимостей
apt install -y curl wget unzip socat cron

# 3. Установка XRay-core
curl -L -o /tmp/xray.zip https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip
unzip -o /tmp/xray.zip -d /usr/local/bin/
chmod +x /usr/local/bin/xray
rm /tmp/xray.zip

# 4. Генерация ключей Reality
X25519_KEY=$(xray x25519)
PRIVATE_KEY=$(echo "$X25519_KEY" | grep "Private key" | cut -d':' -f2 | tr -d ' ')
PUBLIC_KEY=$(echo "$X25519_KEY" | grep "Public key" | cut -d':' -f2 | tr -d ' ')
SHORT_ID=$(openssl rand -hex 8)

echo "Private Key: $PRIVATE_KEY"
echo "Public Key: $PUBLIC_KEY"
echo "Short ID: $SHORT_ID"

# 5. Создание директорий
mkdir -p /etc/xray
mkdir -p /var/log/xray

# 6. Установка SSL сертификата (ACME.sh)
curl https://get.acme.sh | sh
source ~/.bashrc

~/.acme.sh/acme.sh --set-default-ca --server letsencrypt
~/.acme.sh/acme.sh --register-account -m your-email@example.com
~/.acme.sh/acme.sh --issue -d your-domain.com --standalone --force

~/.acme.sh/acme.sh --install-cert -d your-domain.com \
    --key-file /etc/xray/privkey.pem \
    --fullchain-file /etc/xray/fullchain.pem

# 7. Создание конфигурации
cat > /etc/xray/config.json << EOF
{
  "log": {
    "loglevel": "warning",
    "error": "/var/log/xray/error.log",
    "access": "/var/log/xray/access.log"
  },
  "inbounds": [
    {
      "port": 443,
      "protocol": "vless",
      "settings": {
        "clients": [],
        "decryption": "none",
        "fallbacks": [
          {"dest": 8080, "alpn": "h2"}
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "show": false,
          "dest": "gosuslugi.ru:443",
          "serverNames": ["gosuslugi.ru"],
          "privateKey": "$PRIVATE_KEY",
          "shortIds": ["", "$SHORT_ID"]
        }
      },
      "sniffing": {
        "enabled": true,
        "destOverride": ["http", "tls"]
      }
    },
    {
      "listen": "127.0.0.1",
      "port": 8080,
      "protocol": "dokodemo-door",
      "settings": {
        "address": "gosuslugi.ru",
        "port": 443
      },
      "streamSettings": {
        "network": "tcp",
        "security": "tls",
        "tlsSettings": {
          "certificates": [
            {
              "certificateFile": "/etc/xray/fullchain.pem",
              "keyFile": "/etc/xray/privkey.pem"
            }
          ],
          "alpn": ["h2", "http/1.1"]
        }
      }
    }
  ],
  "outbounds": [
    {"protocol": "freedom", "tag": "direct"},
    {"protocol": "blackhole", "tag": "blocked"}
  ],
  "routing": {
    "domainStrategy": "AsIs",
    "rules": [
      {"type": "field", "ip": ["geoip:private"], "outboundTag": "blocked"}
    ]
  }
}
EOF

# 8. Создание systemd сервиса
cat > /etc/systemd/system/xray.service << EOF
[Unit]
Description=XRay Service
After=network.target nss-lookup.target

[Service]
User=nobody
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
NoNewPrivileges=true
ExecStart=/usr/local/bin/xray run -c /etc/xray/config.json
Restart=on-failure
RestartPreventExitStatus=23
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

# 9. Запуск
systemctl daemon-reload
systemctl enable xray
systemctl start xray

# 10. Проверка
systemctl status xray
journalctl -u xray -f
```

## Шаг 5: Проверка работы

```bash
# Проверка порта
netstat -tlnp | grep 443

# Проверка логов
tail -f /var/log/xray/access.log

# Проверка подключения (с клиента)
curl -I https://your-domain.com:443
```

## Шаг 6: Добавление клиентов

### Через API (автоматически, из Telegram-бота)

```bash
# API endpoint для генерации ключа
curl -X POST https://your-api-url/api/generate_key \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"user_id": 123456789, "days": 30}'
```

### Вручную (редактирование конфига)

```bash
# Генерация UUID для клиента
UUID=$(cat /proc/sys/kernel/random/uuid)
echo "UUID: $UUID"

# Добавление клиента в конфиг
# Редактируем /etc/xray/config.json, добавляем в clients:
{
  "id": "$UUID",
  "flow": "xtls-rprx-vision",
  "email": "client@example.com"
}

# Перезапуск
systemctl restart xray
```

## Шаг 7: Настройка брандмауэра

```bash
# UFW (если используется)
ufw allow 443/tcp
ufw allow 22/tcp
ufw enable

# Или iptables
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
```

## 🔧 Управление сервисом

```bash
# Статус
systemctl status xray

# Перезапуск
systemctl restart xray

# Остановка
systemctl stop xray

# Логи
journalctl -u xray -f
tail -f /var/log/xray/error.log
```

## 📊 Мониторинг

```bash
# Статистика подключений
watch -n 1 'netstat -an | grep :443 | wc -l'

# Использование трафика
iftop -P -n -i eth0

# Логи в реальном времени
tail -f /var/log/xray/access.log | grep -E "(TCP|UDP)"
```

## ⚠️ Решение проблем

### Ошибка: "Address already in use"
```bash
# Проверка, что использует порт 443
lsof -i :443
netstat -tlnp | grep 443

# Если занято, смените порт в конфиге
```

### Ошибка SSL
```bash
# Перевыпуск сертификата
~/.acme.sh/acme.sh --renew -d your-domain.com --force
systemctl restart xray
```

### Клиенты не подключаются
```bash
# Проверка firewall
ufw status

# Проверка маршрутизации
ip route

# Проверка DNS
nslookup your-domain.com
```

## 📄 Файлы конфигурации

| Файл | Описание |
|------|----------|
| `/etc/xray/config.json` | Конфигурация XRay |
| `/etc/xray/privkey.pem` | Приватный ключ SSL |
| `/etc/xray/fullchain.pem` | Публичный сертификат |
| `/etc/xray/keys.json` | Ключи Reality |
| `/var/log/xray/access.log` | Логи доступа |
| `/var/log/xray/error.log` | Логи ошибок |
| `/etc/systemd/system/xray.service` | Systemd сервис |
