#!/bin/bash
# Скрипт установки SNI Monitor для XRay Reality
# Использование: sudo bash install_sni_monitor.sh

set -e

echo "============================================================"
echo "  Установка SNI Monitor для XRay Reality"
echo "============================================================"
echo

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Пути
SCRIPT_DIR="/root/AlufProxy/AlufProxy/server"
SYSTEMD_DIR="/etc/systemd/system"
STATE_DIR="/var/lib/xray"
LOG_DIR="/var/log/xray"

# Проверка root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Ошибка: Требуется запуск от root${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Проверка прав root... OK${NC}"
echo

# 1. Создание директорий
echo "📁 Создание директорий..."
mkdir -p "$STATE_DIR"
mkdir -p "$LOG_DIR"
echo -e "${GREEN}✓ Директории созданы${NC}"
echo

# 2. Копирование Python скриптов
echo "📋 Копирование Python скриптов..."
cp "$SCRIPT_DIR/sni_domains.py" "$SCRIPT_DIR/"
cp "$SCRIPT_DIR/check_sni.py" "$SCRIPT_DIR/"
cp "$SCRIPT_DIR/sni_updater.py" "$SCRIPT_DIR/"
chmod +x "$SCRIPT_DIR"/*.py
echo -e "${GREEN}✓ Python скрипты скопированы${NC}"
echo

# 3. Установка systemd сервисов
echo "⚙️ Установка systemd сервисов..."
cp "$SCRIPT_DIR/sni-monitor.service" "$SYSTEMD_DIR/"
cp "$SCRIPT_DIR/sni-monitor.timer" "$SYSTEMD_DIR/"

chmod 644 "$SYSTEMD_DIR/sni-monitor.service"
chmod 644 "$SYSTEMD_DIR/sni-monitor.timer"
echo -e "${GREEN}✓ Systemd сервисы установлены${NC}"
echo

# 4. Перезагрузка systemd
echo "🔄 Перезагрузка systemd..."
systemctl daemon-reload
echo -e "${GREEN}✓ Systemd перезапущен${NC}"
echo

# 5. Включение таймера
echo "⏰ Включение таймера SNI Monitor..."
systemctl enable sni-monitor.timer
systemctl start sni-monitor.timer
echo -e "${GREEN}✓ Таймер запущен${NC}"
echo

# 6. Проверка статуса
echo "📊 Статус сервиса:"
systemctl status sni-monitor.timer --no-pager
echo

# 7. Проверка логов
echo "📋 Последние логи:"
journalctl -u sni-monitor.service -n 10 --no-pager
echo

# 8. Создание отчёта
echo "============================================================"
echo "  Установка завершена!"
echo "============================================================"
echo
echo -e "${GREEN}✓ SNI Monitor установлен и запущен${NC}"
echo
echo "Полезные команды:"
echo "  # Проверка статуса таймера:"
echo "  systemctl status sni-monitor.timer"
echo
echo "  # Просмотр логов:"
echo "  journalctl -u sni-monitor.service -f"
echo
echo "  # Текущее состояние:"
echo "  cat $STATE_DIR/sni_state.json"
echo
echo "============================================================"
