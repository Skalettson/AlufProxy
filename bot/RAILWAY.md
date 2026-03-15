# AlufProxy Bot для Railway

## Деплой

1. Создайте проект на [Railway](https://railway.app)
2. Подключите GitHub репозиторий
3. Добавьте переменные окружения (см. .env.example)
4. Railway автоматически задеплоит

## Переменные окружения

| Переменная | Значение |
|------------|----------|
| `BOT_TOKEN` | Токен от @BotFather |
| `SERVER_DOMAIN` | Домен VPS |
| `SERVER_PORT` | Порт (443) |
| `ADMIN_IDS` | Ваш Telegram ID |
| `DATABASE_PATH` | `data/bot.db` |
| `SUPPORT_ENABLED` | `true` |

## Запуск

Railway автоматически запустит бота через polling.

Для webhook используйте команду:
```
/setup_webhook
```

## Логи

В Railway Dashboard → Logs
