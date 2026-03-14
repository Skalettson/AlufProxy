#!/bin/bash
# Скрипт установки XRay-core с VLESS Reality
# Для Ubuntu 22.04+
# Использование: ./install.sh

set -e

echo "🚀 Установка XRay-core с VLESS Reality..."
echo ""

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Проверка root прав
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Ошибка: запустите скрипт от root${NC}"
    echo -e "${YELLOW}Используйте: sudo -i && ./install.sh${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Права root подтверждены${NC}"
echo ""

# Переменные (можно изменить перед запуском)
DOMAIN=${DOMAIN:-"proxy.example.com"}
SNI_DOMAIN=${SNI_DOMAIN:-"gosuslugi.ru"}
FALLBACK_DOMAIN=${FALLBACK_DOMAIN:-"gosuslugi.ru"}
VLESS_PORT=${VLESS_PORT:-"443"}
EMAIL=${EMAIL:-"admin@example.com"}

echo -e "${BLUE}=== Конфигурация ===${NC}"
echo -e "Домен: ${YELLOW}${DOMAIN}${NC}"
echo -e "SNI: ${YELLOW}${SNI_DOMAIN}${NC}"
echo -e "Порт: ${YELLOW}${VLESS_PORT}${NC}"
echo -e "Email: ${YELLOW}${EMAIL}${NC}"
echo ""

# Обновление системы
echo -e "${GREEN}[1/9] Обновление системы...${NC}"
apt update -qq && apt upgrade -y -qq
echo -e "${GREEN}✅ Обновлено${NC}"
echo ""

# Установка зависимостей
echo -e "${GREEN}[2/9] Установка зависимостей...${NC}"
apt install -y -qq curl wget unzip socat cron openssl
echo -e "${GREEN}✅ Зависимости установлены${NC}"
echo ""

# Создание директорий
echo -e "${GREEN}[3/9] Создание директорий...${NC}"
mkdir -p /etc/xray
mkdir -p /var/log/xray
echo -e "${GREEN}✅ Директории созданы${NC}"
echo ""

# Установка XRay-core
echo -e "${GREEN}[4/9] Установка XRay-core...${NC}"

# Проверка архитектуры
ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
    XRAY_URL="https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip"
elif [ "$ARCH" = "aarch64" ]; then
    XRAY_URL="https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-arm64-v8a.zip"
else
    echo -e "${RED}❌ Неподдерживаемая архитектура: $ARCH${NC}"
    exit 1
fi

echo -e "Загрузка XRay... (${ARCH})"
curl -L -o /tmp/xray.zip "$XRAY_URL" 2>/dev/null

if [ ! -f /tmp/xray.zip ]; then
    echo -e "${RED}❌ Не удалось загрузить XRay${NC}"
    exit 1
fi

unzip -o /tmp/xray.zip -d /usr/local/bin/ >/dev/null 2>&1
chmod +x /usr/local/bin/xray
rm /tmp/xray.zip

# Проверка установки
if ! command -v xray &> /dev/null; then
    echo -e "${RED}❌ Ошибка установки XRay${NC}"
    exit 1
fi

XRAY_VERSION=$(xray version | head -1)
echo -e "${GREEN}✅ XRay установлен: ${XRAY_VERSION}${NC}"
echo ""

# Генерация ключей Reality
echo -e "${GREEN}[5/9] Генерация ключей Reality...${NC}"

# Проверка, есть ли уже ключи
if [ -f /etc/xray/keys.json ]; then
    echo -e "${YELLOW}⚠️  Ключи уже существуют. Пересоздать? (y/n)${NC}"
    read -r response
    if [ "$response" != "y" ]; then
        echo -e "${GREEN}✅ Используем существующие ключи${NC}"
        PRIVATE_KEY=$(cat /etc/xray/keys.json | grep '"private_key"' | cut -d'"' -f4)
        PUBLIC_KEY=$(cat /etc/xray/keys.json | grep '"public_key"' | cut -d'"' -f4)
        SHORT_ID=$(cat /etc/xray/keys.json | grep '"short_id"' | cut -d'"' -f4)
    fi
fi

# Генерация новых ключей
if [ -z "$PRIVATE_KEY" ]; then
    X25519_OUTPUT=$(xray x25519 2>/dev/null)
    PRIVATE_KEY=$(echo "$X25519_OUTPUT" | grep "Private key" | cut -d':' -f2 | tr -d ' ')
    PUBLIC_KEY=$(echo "$X25519_OUTPUT" | grep "Public key" | cut -d':' -f2 | tr -d ' ')
    SHORT_ID=$(openssl rand -hex 8)
    
    # Сохранение ключей
    cat > /etc/xray/keys.json << EOF
{
    "private_key": "${PRIVATE_KEY}",
    "public_key": "${PUBLIC_KEY}",
    "short_id": "${SHORT_ID}"
}
EOF
    chmod 600 /etc/xray/keys.json
fi

echo -e "${GREEN}✅ Ключи сгенерированы${NC}"
echo -e "${YELLOW}Private Key: ${PRIVATE_KEY}${NC}"
echo -e "${YELLOW}Public Key: ${PUBLIC_KEY}${NC}"
echo -e "${YELLOW}Short ID: ${SHORT_ID}${NC}"
echo ""

# Установка сертификата (ACME.sh)
echo -e "${GREEN}[6/9] Установка SSL сертификата...${NC}"

# Проверка, есть ли уже сертификат
if [ -f /etc/xray/fullchain.pem ] && [ -f /etc/xray/privkey.pem ]; then
    echo -e "${YELLOW}⚠️  Сертификат уже существует. Пересоздать? (y/n)${NC}"
    read -r response
    if [ "$response" != "y" ]; then
        echo -e "${GREEN}✅ Используем существующий сертификат${NC}"
    else
        rm -f /etc/xray/fullchain.pem /etc/xray/privkey.pem
    fi
fi

if [ ! -f /etc/xray/fullchain.pem ]; then
    # Установка acme.sh
    if [ ! -f ~/.acme.sh/acme.sh ]; then
        echo "Установка acme.sh..."
        curl https://get.acme.sh | sh >/dev/null 2>&1
        source ~/.bashrc
    fi
    
    # Регистрация
    ~/.acme.sh/acme.sh --set-default-ca --server letsencrypt
    ~/.acme.sh/acme.sh --register-account -m "${EMAIL}" >/dev/null 2>&1
    
    # Выпуск сертификата
    echo "Выпуск сертификата для ${DOMAIN}..."
    ~/.acme.sh/acme.sh --issue -d "${DOMAIN}" --standalone --force >/dev/null 2>&1
    
    # Копирование
    ~/.acme.sh/acme.sh --install-cert -d "${DOMAIN}" \
        --key-file /etc/xray/privkey.pem \
        --fullchain-file /etc/xray/fullchain.pem
    
    echo -e "${GREEN}✅ Сертификат установлен${NC}"
else
    echo -e "${GREEN}✅ Сертификат уже установлен${NC}"
fi
echo ""

# Создание конфигурации XRay
echo -e "${GREEN}[7/9] Создание конфигурации...${NC}"

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

echo -e "${GREEN}✅ Конфигурация создана${NC}"
echo ""

# Создание systemd сервиса
echo -e "${GREEN}[8/9] Настройка сервиса...${NC}"

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

systemctl daemon-reload
systemctl enable xray

echo -e "${GREEN}✅ Сервис настроен${NC}"
echo ""

# Запуск XRay
echo -e "${GREEN}[9/9] Запуск XRay...${NC}"
systemctl start xray
sleep 2

# Проверка статуса
if systemctl is-active --quiet xray; then
    echo -e "${GREEN}✅ XRay запущен и работает${NC}"
else
    echo -e "${RED}❌ Ошибка запуска XRay${NC}"
    echo -e "${YELLOW}Проверьте логи: journalctl -u xray -f${NC}"
    exit 1
fi
echo ""

# Вывод информации
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}✅ Установка завершена успешно!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${BLUE}Конфигурация:${NC}"
echo -e "  Домен: ${YELLOW}${DOMAIN}${NC}"
echo -e "  Порт: ${YELLOW}${VLESS_PORT}${NC}"
echo -e "  SNI: ${YELLOW}${SNI_DOMAIN}${NC}"
echo ""
echo -e "${BLUE}Ключи (сохраните!):${NC}"
echo -e "  ${YELLOW}Private Key: ${PRIVATE_KEY}${NC}"
echo -e "  ${YELLOW}Public Key: ${PUBLIC_KEY}${NC}"
echo -e "  ${YELLOW}Short ID: ${SHORT_ID}${NC}"
echo ""
echo -e "${BLUE}Файлы:${NC}"
echo -e "  Конфиг: ${YELLOW}/etc/xray/config.json${NC}"
echo -e "  Ключи: ${YELLOW}/etc/xray/keys.json${NC}"
echo -e "  Логи: ${YELLOW}/var/log/xray/${NC}"
echo ""
echo -e "${BLUE}Команды управления:${NC}"
echo -e "  ${YELLOW}systemctl status xray${NC}  - статус"
echo -e "  ${YELLOW}systemctl restart xray${NC} - перезапуск"
echo -e "  ${YELLOW}systemctl stop xray${NC}    - остановка"
echo -e "  ${YELLOW}journalctl -u xray -f${NC}  - логи"
echo ""
echo -e "${BLUE}Следующие шаги:${NC}"
echo -e "  1. Настройте DNS (A запись ${DOMAIN} → ваш IP)"
echo -e "  2. Получите ключ для клиента из бота"
echo -e "  3. Подключайтесь!"
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
Ключи: /etc/xray/keys.json
EOF

echo -e "${GREEN}Информация сохранена в /root/xray_info.txt${NC}"
