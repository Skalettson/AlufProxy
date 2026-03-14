#!/bin/bash
# Скрипт установки XRay-core с VLESS Reality
# Для Ubuntu 22.04+

set -e

echo "🚀 Установка XRay-core с VLESS Reality..."

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка root прав
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Ошибка: запустите скрипт от root${NC}"
    exit 1
fi

# Переменные (можно изменить перед запуском)
DOMAIN=${DOMAIN:-"proxy.example.com"}
SNI_DOMAIN=${SNI_DOMAIN:-"gosuslugi.ru"}
FALLBACK_DOMAIN=${FALLBACK_DOMAIN:-"gosuslugi.ru"}
VLESS_PORT=${VLESS_PORT:-"443"}
EMAIL=${EMAIL:-"admin@example.com"}

echo -e "${YELLOW}Домен: ${DOMAIN}${NC}"
echo -e "${YELLOW}SNI: ${SNI_DOMAIN}${NC}"
echo -e "${YELLOW}Порт: ${VLESS_PORT}${NC}"

# Обновление системы
echo -e "${GREEN}[1/8] Обновление системы...${NC}"
apt update && apt upgrade -y

# Установка зависимостей
echo -e "${GREEN}[2/8] Установка зависимостей...${NC}"
apt install -y curl wget unzip socat cron

# Создание директорий
echo -e "${GREEN}[3/8] Создание директорий...${NC}"
mkdir -p /etc/xray
mkdir -p /var/log/xray

# Установка XRay-core
echo -e "${GREEN}[4/8] Установка XRay-core...${NC}"
XRAY_VERSION=$(curl -s https://api.github.com/repos/XTLS/Xray-core/releases/latest | grep '"tag_name"' | cut -d'"' -f4)
XRAY_VERSION=${XRAY_VERSION:-"v24.1.1"}

curl -L -o /tmp/xray.zip "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip"
unzip -o /tmp/xray.zip -d /usr/local/bin/
chmod +x /usr/local/bin/xray
rm /tmp/xray.zip

# Проверка установки
if ! command -v xray &> /dev/null; then
    echo -e "${RED}Ошибка установки XRay${NC}"
    exit 1
fi

echo -e "${GREEN}XRay установлен: $(xray version | head -1)${NC}"

# Генерация ключей Reality
echo -e "${GREEN}[5/8] Генерация ключей Reality...${NC}"
X25519_KEY=$(xray x25519)
PRIVATE_KEY=$(echo "$X25519_KEY" | grep "Private key" | cut -d':' -f2 | tr -d ' ')
PUBLIC_KEY=$(echo "$X25519_KEY" | grep "Public key" | cut -d':' -f2 | tr -d ' ')
SHORT_ID=$(openssl rand -hex 8)

echo -e "${YELLOW}Private Key: ${PRIVATE_KEY}${NC}"
echo -e "${YELLOW}Public Key: ${PUBLIC_KEY}${NC}"
echo -e "${YELLOW}Short ID: ${SHORT_ID}${NC}"

# Сохранение ключей
cat > /etc/xray/keys.json << EOF
{
    "private_key": "${PRIVATE_KEY}",
    "public_key": "${PUBLIC_KEY}",
    "short_id": "${SHORT_ID}"
}
EOF

chmod 600 /etc/xray/keys.json

# Установка сертификата (ACME.sh)
echo -e "${GREEN}[6/8] Установка SSL сертификата...${NC}"
curl https://get.acme.sh | sh
source ~/.bashrc

~/.acme.sh/acme.sh --set-default-ca --server letsencrypt
~/.acme.sh/acme.sh --register-account -m "${EMAIL}"
~/.acme.sh/acme.sh --issue -d "${DOMAIN}" --standalone --force

# Копирование сертификатов
~/.acme.sh/acme.sh --install-cert -d "${DOMAIN}" \
    --key-file /etc/xray/privkey.pem \
    --fullchain-file /etc/xray/fullchain.pem

# Создание конфигурации XRay
echo -e "${GREEN}[7/8] Создание конфигурации...${NC}"
cat > /etc/xray/config.json << EOF
{
  "log": {
    "loglevel": "warning",
    "error": "/var/log/xray/error.log",
    "access": "/var/log/xray/access.log"
  },
  "inbounds": [
    {
      "port": ${VLESS_PORT},
      "protocol": "vless",
      "settings": {
        "clients": [],
        "decryption": "none",
        "fallbacks": [
          {
            "dest": 8080,
            "alpn": "h2"
          }
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "show": false,
          "dest": "${FALLBACK_DOMAIN}:443",
          "serverNames": [
            "${FALLBACK_DOMAIN}",
            "${SNI_DOMAIN}"
          ],
          "privateKey": "${PRIVATE_KEY}",
          "shortIds": [
            "",
            "${SHORT_ID}"
          ]
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
        "address": "${FALLBACK_DOMAIN}",
        "port": 443,
        "network": "tcp"
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
    {
      "protocol": "freedom",
      "tag": "direct"
    },
    {
      "protocol": "blackhole",
      "tag": "blocked"
    }
  ],
  "routing": {
    "domainStrategy": "AsIs",
    "rules": [
      {
        "type": "field",
        "ip": ["geoip:private"],
        "outboundTag": "blocked"
      }
    ]
  }
}
EOF

# Создание systemd сервиса
echo -e "${GREEN}[8/8] Настройка сервиса...${NC}"
cat > /etc/systemd/system/xray.service << EOF
[Unit]
Description=XRay Service
Documentation=https://github.com/xtls
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

# Перезагрузка systemd и запуск
systemctl daemon-reload
systemctl enable xray
systemctl start xray

# Проверка статуса
sleep 2
systemctl status xray --no-pager

# Вывод информации
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}✅ Установка завершена успешно!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${YELLOW}Конфигурация:${NC}"
echo "  Домен: ${DOMAIN}"
echo "  Порт: ${VLESS_PORT}"
echo "  SNI: ${SNI_DOMAIN}"
echo ""
echo -e "${YELLOW}Ключи (сохраните!):${NC}"
echo "  Private Key: ${PRIVATE_KEY}"
echo "  Public Key: ${PUBLIC_KEY}"
echo "  Short ID: ${SHORT_ID}"
echo ""
echo -e "${YELLOW}Файлы:${NC}"
echo "  Конфиг: /etc/xray/config.json"
echo "  Ключи: /etc/xray/keys.json"
echo "  Логи: /var/log/xray/"
echo ""
echo -e "${YELLOW}Команды управления:${NC}"
echo "  systemctl status xray  - статус"
echo "  systemctl restart xray - перезапуск"
echo "  systemctl stop xray    - остановка"
echo "  journalctl -u xray -f  - логи"
echo ""

# Сохранение информации в файл
cat > /root/xray_info.txt << EOF
XRay VLESS Reality - Информация
================================
Домен: ${DOMAIN}
Порт: ${VLESS_PORT}
SNI: ${SNI_DOMAIN}

Private Key: ${PRIVATE_KEY}
Public Key: ${PUBLIC_KEY}
Short ID: ${SHORT_ID}

Конфигурация: /etc/xray/config.json
EOF

echo -e "${GREEN}Информация сохранена в /root/xray_info.txt${NC}"
