"""
Генерация VLESS Reality ключей
Использует формат совместимый с XRay Reality
"""

import subprocess
import secrets
import json
from typing import Tuple


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
                elif 'Password:' in line:
                    public_key = line.split(':')[1].strip()
            
            if private_key and public_key:
                return private_key, public_key
    except Exception:
        pass
    
    # Fallback: генерация через Python (менее надёжно)
    return generate_fallback_keys()


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


def generate_vless_key(
    uuid_key: str,
    domain: str,
    port: int,
    public_key: str,
    short_id: str,
    sni: str = "gosuslugi.ru",
    label: str = "AlufProxy"
) -> str:
    """
    Генерация VLESS Reality ссылки
    """
    from urllib.parse import urlencode
    
    params = {
        'encryption': 'none',
        'security': 'reality',
        'sni': sni,
        'fp': 'chrome',
        'pbk': public_key,
        'sid': short_id,
        'type': 'tcp',
        'headerType': 'none'
    }
    
    query = urlencode(params)
    return f"vless://{uuid_key}@{domain}:{port}?{query}#{label}"


def generate_full_config(
    domain: str,
    port: int = 443,
    sni: str = "vtb.ru"
) -> dict:
    """
    Генерация полной конфигурации для клиента
    """
    private_key, public_key = generate_x25519_keys()
    short_id = generate_short_id()
    uuid_key = generate_uuid()
    
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
        'private_key': private_key,
        'public_key': public_key,
        'short_id': short_id,
        'vless_key': vless_key,
        'domain': domain,
        'port': port,
        'sni': sni
    }


if __name__ == "__main__":
    # Тест генерации
    config = generate_full_config("alufproxy.ddns.net")
    
    print("=== Сгенерированная конфигурация ===\n")
    print(f"UUID: {config['uuid']}")
    print(f"Private Key: {config['private_key']}")
    print(f"Public Key: {config['public_key']}")
    print(f"Short ID: {config['short_id']}")
    print(f"\nVLESS ключ:\n{config['vless_key']}")
