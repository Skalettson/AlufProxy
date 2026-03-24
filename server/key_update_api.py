#!/usr/bin/env python3
"""
Key Update API - обновление ключей XRay Reality
Используется Telegram-ботом для синхронизации ключей
"""

import json
import os
import subprocess
import logging
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="XRay Key Update API")

# API ключ для авторизации бота
API_KEY = "AlufProxy:L3iKh38iFLD1GdCOJaaTmUlx4YNRwqjYKu8znbGFaDEOtpPgdGN7mfeFScRldKXfbxDIKAc1GuJ0mpVLUreowyZZ4LTLv8Nc74ZDzdJ9gRnVj0HwYkdG9Hy92HkllDry05zRtVjaQrSxYKJfMgsVyy65o7OyKkuHGKU8OA8v1dCS4Olz2CjcQngDj7lawB0KpJbb4nzDczPzughV3qC7M7z69uutQ2jTcLMOMkRCxCIAPynZD2BywVneUTwut1QZ"

# Пути к файлам XRay
KEYS_FILE = "/etc/xray/keys.json"
CONFIG_FILE = "/etc/xray/config.json"


class KeyUpdateRequest(BaseModel):
    """Запрос на обновление ключей"""
    private_key: str
    public_key: str
    short_id: str
    uuid: str


class KeyUpdateResponse(BaseModel):
    """Ответ на обновление ключей"""
    success: bool
    message: str


def verify_api_key(x_api_key: str = Header(None)):
    """Проверка API ключа"""
    logger.debug(f"Проверка API ключа: ожидаемый='{API_KEY[:20]}...', полученный='{x_api_key[:20] if x_api_key else None}...'")
    if x_api_key != API_KEY:
        logger.warning(f"❌ API ключ не совпадает!")
        raise HTTPException(status_code=401, detail="Invalid API key")
    logger.info("✅ API ключ валиден")
    return True


def update_keys_file(private_key: str, public_key: str, short_id: str) -> bool:
    """Обновление файла ключей"""
    try:
        logger.info(f"📝 Обновление файла ключей: {KEYS_FILE}")
        keys_data = {
            "private_key": private_key,
            "public_key": public_key,
            "short_id": short_id
        }

        with open(KEYS_FILE, 'w') as f:
            json.dump(keys_data, f, indent=2)

        logger.info(f"✅ Ключи обновлены: {private_key[:16]}...")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка записи ключей: {e}")
        return False


def update_config(private_key: str, short_id: str) -> bool:
    """Обновление конфига XRay"""
    try:
        logger.info(f"📝 Обновление конфига XRay: {CONFIG_FILE}")
        # Читаем конфиг
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)

        # Обновляем realitySettings
        for inbound in config.get('inbounds', []):
            if inbound.get('protocol') == 'vless':
                reality_settings = inbound.get('streamSettings', {}).get('realitySettings', {})
                reality_settings['privateKey'] = private_key
                reality_settings['shortIds'] = ["", short_id]
                logger.info(f"   Обновлено privateKey и shortIds в realitySettings")
                break

        # Записываем конфиг
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)

        logger.info("✅ Конфиг XRay обновлён")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка обновления конфига: {e}")
        return False


def restart_xray() -> bool:
    """Перезапуск XRay через systemd"""
    try:
        logger.info("🔄 Проверка конфига XRay перед перезапуском...")
        # Проверяем конфиг перед перезапуском (используем -test вместо test)
        result = subprocess.run(
            ['/usr/local/bin/xray', '-test', '-c', CONFIG_FILE],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            logger.error(f"❌ Ошибка валидации конфига: {result.stderr or result.stdout}")
            return False

        logger.info("✅ Конфиг валиден, перезапуск XRay...")
        # Перезапускаем XRay
        subprocess.run(
            ['/usr/bin/systemctl', 'restart', 'xray'],
            capture_output=True,
            timeout=30
        )

        # Проверяем что XRay запустился
        result = subprocess.run(
            ['/usr/bin/systemctl', 'is-active', 'xray'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.stdout.strip() == 'active':
            logger.info("✅ XRay успешно перезапущен")
            return True
        else:
            logger.error(f"❌ XRay не запустился: {result.stdout}")
            return False

    except Exception as e:
        logger.error(f"❌ Ошибка перезапуска XRay: {e}")
        return False


@app.on_event("startup")
async def startup():
    """Проверка при запуске"""
    logger.info("Key Update API запущен")
    logger.info(f"Keys file: {KEYS_FILE}")
    logger.info(f"Config file: {CONFIG_FILE}")


@app.get("/")
async def root():
    return {"status": "ok", "service": "XRay Key Update API"}


@app.get("/health")
async def health_check():
    """Проверка работоспособности"""
    try:
        xray_status = subprocess.run(
            ['/usr/bin/systemctl', 'is-active', 'xray'],
            capture_output=True,
            text=True
        ).stdout.strip()
    except:
        xray_status = "unknown"
    
    return {
        "status": "healthy",
        "xray": xray_status
    }


@app.post("/api/update_keys", response_model=KeyUpdateResponse)
async def update_keys(
    request: KeyUpdateRequest,
    x_api_key: str = Header(None, alias="X-API-Key")
):
    """
    Обновление ключей XRay

    Требует авторизации через X-API-Key header
    """
    # Логирование входящего запроса
    logger.info(f"📥 Получен запрос на /api/update_keys")
    logger.info(f"   X-API-Key заголовок: {'present' if x_api_key else 'MISSING'}")
    logger.info(f"   UUID: {request.uuid[:8]}...")
    
    # Проверка API ключа
    if not verify_api_key(x_api_key):
        logger.error("❌ Неверный API ключ!")
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    logger.info("✅ API ключ проверен успешно")
    logger.info(f"Private Key: {request.private_key[:16]}...")
    logger.info(f"Short ID: {request.short_id}")
    
    # 1. Обновляем файл ключей
    logger.info("📝 Шаг 1/3: Обновление файла ключей...")
    if not update_keys_file(request.private_key, request.public_key, request.short_id):
        logger.error("❌ Ошибка обновления файла ключей")
        return KeyUpdateResponse(
            success=False,
            message="Ошибка записи ключей"
        )
    logger.info("✅ Файл ключей обновлён")

    # 2. Обновляем конфиг
    logger.info("📝 Шаг 2/3: Обновление конфига XRay...")
    if not update_config(request.private_key, request.short_id):
        logger.error("❌ Ошибка обновления конфига")
        return KeyUpdateResponse(
            success=False,
            message="Ошибка обновления конфига"
        )
    logger.info("✅ Конфиг XRay обновлён")

    # 3. Перезапускаем XRay
    logger.info("📝 Шаг 3/3: Перезапуск XRay...")
    if not restart_xray():
        logger.error("❌ Ошибка перезапуска XRay!")
        return KeyUpdateResponse(
            success=False,
            message="Ошибка перезапуска XRay"
        )
    logger.info("✅ XRay перезапущен")
    
    logger.info("✅ Ключи обновлены успешно")
    return KeyUpdateResponse(
        success=True,
        message="Ключи обновлены, XRay перезапущен"
    )


@app.get("/api/current_keys")
async def get_current_keys(
    authorized: bool = Header(None)
):
    """Получение текущих ключей"""
    if not verify_api_key(authorized):
        raise HTTPException(status_code=401, detail="Invalid API key")

    try:
        with open(KEYS_FILE, 'r') as f:
            keys = json.load(f)

        return {
            "success": True,
            "keys": {
                "private_key": keys.get('private_key', '')[:16] + "...",
                "public_key": keys.get('public_key', ''),
                "short_id": keys.get('short_id', '')
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/server_keys")
async def get_server_keys():
    """Получение публичных ключей сервера (без авторизации, для бота)"""
    try:
        with open(KEYS_FILE, 'r') as f:
            keys = json.load(f)

        public_key = keys.get('public_key', '')
        short_id = keys.get('short_id', '')
        private_key = keys.get('private_key', '')

        # Если public_key нет, но есть private_key — вычисляем public_key
        if not public_key and private_key:
            try:
                from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
                import base64
                
                private_key_bytes = base64.b64decode(private_key)
                private_key_obj = X25519PrivateKey.from_private_bytes(private_key_bytes)
                public_key_obj = private_key_obj.public_key()
                public_key_bytes = public_key_obj.public_bytes()
                public_key = base64.b64encode(public_key_bytes).decode('utf-8')
                
                # Сохраняем вычисленный public_key
                keys['public_key'] = public_key
                with open(KEYS_FILE, 'w') as f:
                    json.dump(keys, f, indent=2)
                    
                logger.info(f"✅ Public key вычислен из private key")
            except Exception as e:
                logger.error(f"❌ Ошибка вычисления public key: {e}")

        if not public_key or not short_id:
            return {
                "success": False,
                "message": "Ключи сервера ещё не сгенерированы"
            }

        return {
            "success": True,
            "public_key": public_key,
            "short_id": short_id
        }
    except FileNotFoundError:
        return {
            "success": False,
            "message": "Файл ключей не найден"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ClientAddRequest(BaseModel):
    """Запрос на добавление клиента"""
    uuid: str
    email: str = ""


@app.post("/api/add_client")
async def add_client(
    request: ClientAddRequest,
    x_api_key: str = Header(None, alias="X-API-Key")
):
    """
    Добавление клиента в конфиг XRay
    
    Автоматически добавляет UUID в массив clients и перезапускает XRay
    """
    if not verify_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")

    logger.info(f"📥 Добавление клиента: uuid={request.uuid[:8]}..., email={request.email}")

    try:
        # Читаем конфиг
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)

        # Находим VLESS inbound
        vless_inbound = None
        for inbound in config.get('inbounds', []):
            if inbound.get('protocol') == 'vless':
                vless_inbound = inbound
                break

        if not vless_inbound:
            logger.error("❌ VLESS inbound не найден")
            return {"success": False, "message": "VLESS inbound не найден"}

        # Проверяем есть ли уже такой клиент
        clients = vless_inbound.get('settings', {}).get('clients', [])
        for client in clients:
            if client.get('id') == request.uuid:
                logger.info(f"✅ Клиент уже существует: {request.uuid[:8]}...")
                return {
                    "success": True,
                    "message": "Клиент уже существует",
                    "uuid": request.uuid
                }

        # Добавляем нового клиента
        new_client = {
            "id": request.uuid,
            "flow": "xtls-rprx-vision",
            "email": request.email or f"user-{request.uuid[:8]}"
        }
        clients.append(new_client)

        logger.info(f"✅ Клиент добавлен в конфиг. Всего клиентов: {len(clients)}")

        # Сохраняем конфиг
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)

        # Перезапускаем XRay
        logger.info("🔄 Перезапуск XRay...")
        subprocess.run(
            ['/usr/bin/systemctl', 'restart', 'xray'],
            capture_output=True,
            timeout=30
        )

        # Проверяем статус
        result = subprocess.run(
            ['/usr/bin/systemctl', 'is-active', 'xray'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.stdout.strip() == 'active':
            logger.info("✅ XRay перезапущен успешно")
            return {
                "success": True,
                "message": "Клиент добавлен",
                "uuid": request.uuid,
                "total_clients": len(clients)
            }
        else:
            logger.error(f"❌ XRay не запустился: {result.stdout}")
            # Откатываем изменения
            clients.pop()
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            return {
                "success": False,
                "message": "XRay не запустился"
            }

    except Exception as e:
        logger.error(f"❌ Ошибка добавления клиента: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/clients")
async def get_clients(
    x_api_key: str = Header(None, alias="X-API-Key")
):
    """Получение списка клиентов"""
    if not verify_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")

    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)

        clients = []
        for inbound in config.get('inbounds', []):
            if inbound.get('protocol') == 'vless':
                clients = inbound.get('settings', {}).get('clients', [])
                break

        return {
            "success": True,
            "clients": clients,
            "total": len(clients)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ClientRemoveRequest(BaseModel):
    """Запрос на удаление клиента"""
    uuid: str


@app.post("/api/remove_client")
async def remove_client(
    request: ClientRemoveRequest,
    x_api_key: str = Header(None, alias="X-API-Key")
):
    """
    Удаление клиента из конфига XRay
    """
    if not verify_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")

    logger.info(f"📥 Удаление клиента: uuid={request.uuid[:8]}...")

    try:
        # Читаем конфиг
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)

        # Находим VLESS inbound
        vless_inbound = None
        for inbound in config.get('inbounds', []):
            if inbound.get('protocol') == 'vless':
                vless_inbound = inbound
                break

        if not vless_inbound:
            logger.error("❌ VLESS inbound не найден")
            return {"success": False, "message": "VLESS inbound не найден"}

        # Находим и удаляем клиента
        clients = vless_inbound.get('settings', {}).get('clients', [])
        initial_count = len(clients)
        clients = [c for c in clients if c.get('id') != request.uuid]

        if len(clients) == initial_count:
            logger.warning(f"⚠️ Клиент не найден: {request.uuid[:8]}...")
            return {
                "success": False,
                "message": "Клиент не найден"
            }

        vless_inbound['settings']['clients'] = clients
        logger.info(f"✅ Клиент удалён. Осталось клиентов: {len(clients)}")

        # Сохраняем конфиг
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)

        # Перезапускаем XRay
        logger.info("🔄 Перезапуск XRay...")
        subprocess.run(
            ['/usr/bin/systemctl', 'restart', 'xray'],
            capture_output=True,
            timeout=30
        )

        # Проверяем статус
        result = subprocess.run(
            ['/usr/bin/systemctl', 'is-active', 'xray'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.stdout.strip() == 'active':
            logger.info("✅ XRay перезапущен успешно")
            return {
                "success": True,
                "message": "Клиент удалён",
                "uuid": request.uuid,
                "total_clients": len(clients)
            }
        else:
            logger.error(f"❌ XRay не запустился: {result.stdout}")
            return {
                "success": False,
                "message": "XRay не запустился"
            }

    except Exception as e:
        logger.error(f"❌ Ошибка удаления клиента: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cleanup_expired")
async def cleanup_expired(
    x_api_key: str = Header(None, alias="X-API-Key")
):
    """
    Очистка истёкших клиентов из конфига XRay
    """
    if not verify_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")

    logger.info("📥 Очистка истёкших клиентов...")

    try:
        # Читаем конфиг
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)

        # Находим VLESS inbound
        vless_inbound = None
        for inbound in config.get('inbounds', []):
            if inbound.get('protocol') == 'vless':
                vless_inbound = inbound
                break

        if not vless_inbound:
            logger.error("❌ VLESS inbound не найден")
            return {"success": False, "message": "VLESS inbound не найден"}

        # Получаем список активных ключей из БД
        from database import Database
        db = Database()
        active_keys = db.get_active_keys_raw()  # Нужен новый метод

        # Фильтруем клиентов
        clients = vless_inbound.get('settings', {}).get('clients', [])
        initial_count = len(clients)

        # Оставляем только тех у кого email начинается на user- и есть в active_keys
        active_uuids = {k['id'] for k in active_keys}
        filtered_clients = [
            c for c in clients
            if c.get('id') in active_uuids or not c.get('email', '').startswith('user-')
        ]

        removed_count = initial_count - len(filtered_clients)
        vless_inbound['settings']['clients'] = filtered_clients

        logger.info(f"✅ Удалено истёкших клиентов: {removed_count}. Осталось: {len(filtered_clients)}")

        # Сохраняем конфиг
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)

        # Перезапускаем XRay
        logger.info("🔄 Перезапуск XRay...")
        subprocess.run(
            ['/usr/bin/systemctl', 'restart', 'xray'],
            capture_output=True,
            timeout=30
        )

        # Проверяем статус
        result = subprocess.run(
            ['/usr/bin/systemctl', 'is-active', 'xray'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.stdout.strip() == 'active':
            logger.info("✅ XRay перезапущен успешно")
            return {
                "success": True,
                "message": f"Удалено {removed_count} истёкших клиентов",
                "total_clients": len(filtered_clients)
            }
        else:
            logger.error(f"❌ XRay не запустился: {result.stdout}")
            return {
                "success": False,
                "message": "XRay не запустился"
            }

    except Exception as e:
        logger.error(f"❌ Ошибка очистки: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8081)
