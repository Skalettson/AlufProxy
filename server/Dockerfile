FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода API
COPY . .

# Создание директории для данных
RUN mkdir -p /app/data

# Экспорт порта
EXPOSE 8000

# Запуск API сервера
CMD ["uvicorn", "key_api:app", "--host", "0.0.0.0", "--port", "8000"]
