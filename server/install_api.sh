#!/bin/bash
# Быстрая установка Key Update API на сервер

set -e

echo "🚀 Установка Key Update API..."

cd /root/AlufProxy/AlufProxy/server

# Установка зависимостей
echo "📦 Установка зависимостей..."
source venv/bin/activate
pip install fastapi uvicorn requests

# Копирование сервиса
echo "📋 Копирование сервиса..."
cp key_update_api.service /etc/systemd/system/key-update-api.service

# Перезагрузка systemd
echo "🔄 Перезагрузка systemd..."
systemctl daemon-reload

# Включение сервиса
echo "✅ Включение сервиса..."
systemctl enable key-update-api

# Запуск сервиса
echo "▶️  Запуск сервиса..."
systemctl start key-update-api

# Проверка
echo "🔍 Проверка..."
sleep 2
systemctl status key-update-api --no-pager

# Тест API
echo "🧪 Тест API..."
curl http://127.0.0.1:8081/health

echo ""
echo "✅ Key Update API установлен!"
echo ""
echo "📋 Следующие шаги:"
echo ""
echo "  1. Перезапустите бота"
echo ""
