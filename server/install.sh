#!/bin/bash
# Скрипт установки XRay-core с VLESS Reality
# Версия с IP вместо домена для dest

set -e

echo "🚀 Установка XRay-core с VLESS Reality..."
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Ошибка: запустите скрипт от root${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Права root подтверждены${NC}"
echo ""

DOMAIN=${DOMAIN:-"alufproxy.ddns.net"}
SNI_DOMAIN=${SNI_DOMAIN:-"gosuslugi.ru"}
FALLBACK_DOMAIN=${SNI_DOMAIN:-"gosuslugi.ru"}
VLESS_PORT=${VLESS_PORT:-"443"}
EMAIL=${EMAIL:-"ettsonskal@gmail.com"}

echo -e "${BLUE}=== Конфигурация ===${NC}"
echo -e "Домен: ${YELLOW}${DOMAIN}${NC}"
echo -e "SNI: ${YELLOW}${SNI_DOMAIN}${NC}"
echo -e "Порт: ${YELLOW}${VLESS_PORT}${NC}"
echo ""

echo -e "${GREEN}[1/8] Обновление системы...${NC}"
apt update -qq && apt upgrade -y -qq >/dev/null 2>&1
echo -e "${GREEN}✅ Обновлено${NC}"
echo ""

echo -e "${GREEN}[2/8] Установка зависимостей...${NC}"
apt install -y -qq curl wget unzip socat openssl python3 dnsutils >/dev/null 2>&1
echo -e "${GREEN}✅ Зависимости установлены${NC}"
echo ""

echo -e "${GREEN}[3/8] Создание директорий...${NC}"
mkdir -p /etc/xray /var/log/xray
echo -e "${GREEN}✅ Директории созданы${NC}"
echo ""

echo -e "${GREEN}[4/8] Установка XRay-core...${NC}"
curl -L -o /tmp/xray.zip "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip" 2>/dev/null
unzip -o /tmp/xray.zip -d /usr/local/bin/ >/dev/null 2>&1
chmod +x /usr/local/bin/xray
rm /tmp/xray.zip
echo -e "${GREEN}✅ XRay установлен: $(xray version | head -1)${NC}"
echo ""

echo -e "${GREEN}[5/8] Генерация ключей Reality...${NC}"

X25519_OUTPUT=$(/usr/local/bin/xray x25519 2>&1)
PRIVATE_KEY=$(echo "$X25519_OUTPUT" | grep "PrivateKey:" | awk '{print $2}')
SHORT_ID=$(openssl rand -hex 8)

if [ -z "$PRIVATE_KEY" ]; then
    echo -e "${RED}❌ Не удалось сгенерировать ключи${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Ключи сгенерированы:${NC}"
echo -e "${YELLOW}Private Key: ${PRIVATE_KEY}${NC}"
echo -e "${YELLOW}Short ID: ${SHORT_ID}${NC}"

cat > /etc/xray/keys.json << EOF
{
    "private_key": "${PRIVATE_KEY}",
    "short_id": "${SHORT_ID}"
}
EOF

echo -e "${GREEN}✅ Ключи сохранены в /etc/xray/keys.json${NC}"
echo ""

echo -e "${GREEN}[6/8] Установка SSL сертификата...${NC}"

if [ ! -f ~/.acme.sh/acme.sh ]; then
    curl https://get.acme.sh | sh >/dev/null 2>&1
    source ~/.bashrc
fi

~/.acme.sh/acme.sh --set-default-ca --server letsencrypt
~/.acme.sh/acme.sh --register-account -m "${EMAIL}" >/dev/null 2>&1

if [ ! -f /etc/xray/fullchain.pem ]; then
    ~/.acme.sh/acme.sh --issue -d "${DOMAIN}" --standalone --force >/dev/null 2>&1
    ~/.acme.sh/acme.sh --install-cert -d "${DOMAIN}" \
        --key-file /etc/xray/privkey.pem \
        --fullchain-file /etc/xray/fullchain.pem
    echo -e "${GREEN}✅ Сертификат установлен${NC}"
else
    echo -e "${GREEN}✅ Сертификат уже существует${NC}"
fi
echo ""

echo -e "${GREEN}[7/8] Создание конфигурации...${NC}"

# Получаем IP для gosuslugi.ru (обход блокировки портов)
echo "Получение IP адреса для ${FALLBACK_DOMAIN}..."
DEST_IP=$(dig +short ${FALLBACK_DOMAIN} | head -1)

if [ -z "$DEST_IP" ]; then
    echo -e "${YELLOW}⚠️  Не удалось получить IP, используем домен...${NC}"
    DEST="${FALLBACK_DOMAIN}:443"
else
    echo -e "${GREEN}✅ IP получен: ${DEST_IP}${NC}"
    DEST="${DEST_IP}:443"
fi

PRIVATE_KEY=$(cat /etc/xray/keys.json | grep '"private_key"' | cut -d'"' -f4)
SHORT_ID=$(cat /etc/xray/keys.json | grep '"short_id"' | cut -d'"' -f4)
CLIENT_UUID=$(cat /proc/sys/kernel/random/uuid)

cat > /etc/xray/config.json << CFGEOF
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
        "clients": [
          {
            "id": "${CLIENT_UUID}",
            "flow": "xtls-rprx-vision",
            "email": "ettsonskal@gmail.com"
          }
        ],
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
          "dest": "${DEST}",
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
CFGEOF

echo -e "${GREEN}✅ Конфигурация создана${NC}"
echo -e "${BLUE}Dest: ${DEST}${NC}"
echo ""

echo -e "${GREEN}[8/8] Настройка сервиса...${NC}"

cat > /etc/systemd/system/xray.service << SVCEOF
[Unit]
Description=XRay Service
Documentation=https://github.com/xtls
After=network.target nss-lookup.target

[Service]
Type=simple
User=root
Group=root
ExecStart=/usr/local/bin/xray run -c /etc/xray/config.json
Restart=on-failure
RestartPreventExitStatus=23
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable xray
echo -e "${GREEN}✅ Сервис настроен${NC}"
echo ""

echo -e "${GREEN}Запуск XRay...${NC}"
systemctl start xray
sleep 2

if systemctl is-active --quiet xray; then
    echo -e "${GREEN}✅ XRay запущен и работает${NC}"
else
    echo -e "${RED}❌ Ошибка запуска XRay${NC}"
    journalctl -u xray -n 10 --no-pager
    exit 1
fi

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}✅ Установка завершена успешно!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${BLUE}Ключи (сохраните!):${NC}"
cat /etc/xray/keys.json
echo ""
echo -e "${BLUE}Client UUID:${NC}"
echo "${CLIENT_UUID}"
echo ""
echo -e "${BLUE}Команды управления:${NC}"
echo "  systemctl status xray  - статус"
echo "  systemctl restart xray - перезапуск"
echo "  journalctl -u xray -f  - логи"
echo ""
