"""
Генерация VLESS Reality ключей
Автоматическая синхронизация с XRay сервером
"""

import subprocess
import secrets
import json
import requests
import os
import logging
import random
from typing import Tuple, Optional, Dict

logger = logging.getLogger(__name__)

# Импортируем SNI домены из конфига
try:
    from config import SNI_DOMAINS, get_random_sni, VLESS_SNI
except ImportError:
    # Fallback если config не доступен
    SNI_DOMAINS = {
        "priority_5": ["www.microsoft.com", "microsoft.com", "www.apple.com"]
    }
    VLESS_SNI = "www.microsoft.com"

# API для обновления ключей на сервере
KEY_UPDATE_API_URL = os.getenv("KEY_UPDATE_API_URL", "http://127.0.0.1:8081")
KEY_UPDATE_API_KEY = os.getenv("KEY_UPDATE_API_KEY", "AlufProxy:L3iKh38iFLD1GdCOJaaTmUlx4YNRwqjYKu8znbGFaDEOtpPgdGN7mfeFScRldKXfbxDIKAc1GuJ0mpVLUreowyZZ4LTLv8Nc74ZDzdJ9gRnVj0HwYkdG9Hy92HkllDry05zRtVjaQrSxYKJfMgsVyy65o7OyKkuHGKU8OA8v1dCS4Olz2CjcQngDj7lawB0KpJbb4nzDczPzughV3qC7M7z69uutQ2jTcLMOMkRCxCIAPynZD2BywVneUTwut1QZ")


def generate_x25519_keys() -> Tuple[str, str]:
    """
    Генерация X25519 ключей через xray x25519
    Возвращает (private_key, public_key) в формате XRay Reality
    """
    try:
        # Пробуем через xray x25519
        result = subprocess.run(
            ['xray', 'x25519'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            private_key = None
            public_key = None

            for line in result.stdout.split('\n'):
                if 'PrivateKey:' in line:
                    private_key = line.split(':')[1].strip()
                elif 'Password:' in line:  # В некоторых версиях public key называется Password
                    public_key = line.split(':')[1].strip()

            if private_key and public_key:
                return private_key, public_key
    except Exception:
        pass

    # Fallback: генерация через Python (менее надёжно)
    return generate_fallback_keys()


def compute_public_key(private_key: str) -> Tuple[bool, str]:
    """
    Вычисление public key из private key через xray x25519
    
    Возвращает (success, public_key или error_message)
    """
    try:
        # xray x25519 генерирует новую пару, но мы можем использовать
        # команду для вычисления public key из private
        # Для этого используем Python библиотеку cryptography
        
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
        import base64
        
        try:
            # Декодируем private key из base64
            private_key_bytes = base64.b64decode(private_key)
            private_key_obj = X25519PrivateKey.from_private_bytes(private_key_bytes)
            public_key_obj = private_key_obj.public_key()
            public_key_bytes = public_key_obj.public_bytes()
            public_key = base64.b64encode(public_key_bytes).decode('utf-8')
            
            logger.info(f"✅ Public key вычислен из private key")
            return True, public_key
            
        except Exception as e:
            logger.error(f"❌ Ошибка вычисления public key: {e}")
            return False, f"Ошибка вычисления: {e}"
            
    except ImportError:
        logger.error("❌ cryptography не установлен")
        return False, "cryptography не установлен"
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        return False, str(e)


def generate_fallback_keys() -> Tuple[str, str]:
    """
    Резервная генерация ключей (если xray недоступен)
    """
    # Генерируем случайную строку 43 символа (256 бит в base64)
    private_key = secrets.token_urlsafe(32)
    public_key = secrets.token_urlsafe(32)
    return private_key, public_key


def generate_short_id() -> str:
    """Генерация Short ID (8 байт = 16 hex символов)"""
    return secrets.token_hex(8)


def generate_uuid() -> str:
    """Генерация UUID"""
    import uuid
    return str(uuid.uuid4())


def get_server_keys() -> Tuple[bool, str, str]:
    """
    Получение текущих ключей сервера
    
    Возвращает (success, public_key, short_id)
    """
    try:
        logger.info(f"📡 Получение ключей сервера: {KEY_UPDATE_API_URL}/api/server_keys")
        
        response = requests.get(
            f"{KEY_UPDATE_API_URL}/api/server_keys",
            timeout=10
        )
        
        logger.info(f"📥 Ответ от сервера: HTTP {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"   Response: {result}")
            if result.get('success'):
                public_key = result.get('public_key', '')
                short_id = result.get('short_id', '')
                
                # Если public_key пустой, пробуем вычислить из private_key
                if not public_key:
                    logger.warning("⚠️ Public key отсутствует, пробуем получить через /api/current_keys...")
                    
                    # Пробуем получить через авторизованный endpoint
                    auth_response = requests.get(
                        f"{KEY_UPDATE_API_URL}/api/current_keys",
                        headers={"X-API-Key": KEY_UPDATE_API_KEY},
                        timeout=10
                    )
                    
                    if auth_response.status_code == 200:
                        auth_result = auth_response.json()
                        # Public key может быть в ответе
                        public_key = auth_result.get('keys', {}).get('public_key', '')
                        logger.info(f"   Получен public_key из /api/current_keys: {public_key[:16] if public_key else 'None'}...")
                
                if public_key and short_id:
                    logger.info(f"✅ Ключи сервера получены: pbk={public_key[:16]}..., sid={short_id}")
                    return True, public_key, short_id
                else:
                    logger.error(f"❌ Ключи не получены: pbk={public_key}, sid={short_id}")
                    return False, '', "Ключи сервера пустые"
            else:
                error_msg = result.get('message', 'Ошибка сервера')
                logger.error(f"❌ Ошибка сервера: {error_msg}")
                return False, '', error_msg
        else:
            error_text = response.text[:200] if response.text else "No response body"
            logger.error(f"❌ Ошибка HTTP {response.status_code}: {error_text}")
            return False, '', f"Ошибка HTTP {response.status_code}"

    except requests.exceptions.ConnectionError as e:
        logger.error(f"❌ ConnectionError: Сервер недоступен")
        return False, '', "Сервер недоступен (ConnectionError)"
    except requests.exceptions.Timeout as e:
        logger.error(f"❌ Timeout: Превышено время ожидания")
        return False, '', "Превышено время ожидания (Timeout)"
    except Exception as e:
        logger.error(f"❌ Ошибка: {type(e).__name__}: {str(e)}")
        return False, '', f"Ошибка: {str(e)}"


def sync_keys_to_server(
    private_key: str,
    public_key: str,
    short_id: str,
    uuid: str
) -> Tuple[bool, str]:
    """
    Отправка ключей на сервер для обновления XRay

    Возвращает (success, message)
    """
    try:
        logger.info(f"📡 Отправка ключей на сервер: {KEY_UPDATE_API_URL}/api/update_keys")
        logger.info(f"   UUID: {uuid[:8]}...")
        logger.info(f"   Private Key: {private_key[:16]}...")
        logger.info(f"   Short ID: {short_id}")
        
        response = requests.post(
            f"{KEY_UPDATE_API_URL}/api/update_keys",
            json={
                "private_key": private_key,
                "public_key": public_key,
                "short_id": short_id,
                "uuid": uuid
            },
            headers={
                "X-API-Key": KEY_UPDATE_API_KEY,
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        logger.info(f"📥 Ответ от сервера: HTTP {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"   Response: {result}")
            if result.get('success'):
                logger.info("✅ Ключи обновлены на сервере")
                return True, "Ключи обновлены на сервере"
            else:
                error_msg = result.get('message', 'Ошибка сервера')
                logger.error(f"❌ Ошибка сервера: {error_msg}")
                return False, error_msg
        elif response.status_code == 401:
            logger.error("❌ Неверный API ключ (401 Unauthorized)")
            return False, "Неверный API ключ"
        else:
            error_text = response.text[:200] if response.text else "No response body"
            logger.error(f"❌ Ошибка HTTP {response.status_code}: {error_text}")
            return False, f"Ошибка HTTP {response.status_code}"

    except requests.exceptions.ConnectionError as e:
        logger.error(f"❌ ConnectionError: Сервер недоступен")
        return False, "Сервер недоступен (ConnectionError)"
    except requests.exceptions.Timeout as e:
        logger.error(f"❌ Timeout: Превышено время ожидания")
        return False, "Превышено время ожидания (Timeout)"
    except Exception as e:
        logger.error(f"❌ Ошибка: {type(e).__name__}: {str(e)}")
        return False, f"Ошибка: {str(e)}"


def generate_vless_key(
    uuid_key: str,
    domain: str,
    port: int,
    public_key: str,
    short_id: str,
    sni: str = None,  # По умолчанию берётся из конфига
    label: str = "AlufProxy"
) -> str:
    """
    Генерация VLESS Reality ссылки
    """
    from urllib.parse import urlencode

    # Если SNI не указан, берём из конфига
    if sni is None:
        sni = VLESS_SNI

    params = {
        'encryption': 'none',
        'security': 'reality',
        'sni': sni,
        'fp': 'chrome',
        'pbk': public_key,
        'sid': short_id,
        'type': 'tcp',
        'headerType': 'none',
        'flow': 'xtls-rprx-vision'  # Обязательно для Reality!
    }

    query = urlencode(params)
    return f"vless://{uuid_key}@{domain}:{port}?{query}#{label}"


def generate_full_config(
    domain: str,
    port: int = 443,
    sni: str = None,  # По умолчанию берётся из конфига
    use_server_keys: bool = True
) -> dict:
    """
    Генерация полной конфигурации для клиента

    Если use_server_keys=True, используются существующие ключи сервера
    (не генерируются новые каждый раз)
    """
    uuid_key = generate_uuid()
    
    # Получаем ключи сервера (если включено)
    public_key = ''
    short_id = ''
    sync_success = False
    sync_message = ''
    
    if use_server_keys:
        sync_success, public_key, short_id_or_error = get_server_keys()
        if not sync_success:
            logger.warning(f"⚠️ Не удалось получить ключи сервера: {short_id_or_error}")
            # Fallback: генерируем новые (старое поведение)
            logger.info("🔄 Fallback: генерация новых ключей...")
            private_key, public_key = generate_x25519_keys()
            short_id = generate_short_id()
            # Синхронизируем новые ключи с сервером
            sync_success, sync_message = sync_keys_to_server(
                private_key=private_key,
                public_key=public_key,
                short_id=short_id,
                uuid=uuid_key
            )
        else:
            short_id = short_id_or_error
            logger.info(f"✅ Используем ключи сервера: pbk={public_key[:16]}..., sid={short_id}")
    else:
        # Старое поведение: генерируем новые ключи каждый раз
        private_key, public_key = generate_x25519_keys()
        short_id = generate_short_id()

    vless_key = generate_vless_key(
        uuid_key=uuid_key,
        domain=domain,
        port=port,
        public_key=public_key,
        short_id=short_id,
        sni=sni
    )

    return {
        'uuid': uuid_key,
        'private_key': private_key if not use_server_keys else '',
        'public_key': public_key,
        'short_id': short_id,
        'vless_key': vless_key,
        'domain': domain,
        'port': port,
        'sni': sni,
        'sync_success': sync_success,
        'sync_message': sync_message
    }


if __name__ == "__main__":
    # Тест генерации
    config = generate_full_config("proxy.example.com")
    
    print("=== Сгенерированная конфигурация ===\n")
    print(f"UUID: {config['uuid']}")
    print(f"Private Key: {config['private_key']}")
    print(f"Public Key: {config['public_key']}")
    print(f"Short ID: {config['short_id']}")
    print(f"\nVLESS ключ:\n{config['vless_key']}")
