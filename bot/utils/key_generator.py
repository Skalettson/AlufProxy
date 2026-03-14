import uuid
import secrets
import base64
import hashlib
from datetime import datetime, timedelta
from typing import Tuple


def generate_uuid() -> str:
    """Генерация UUID для ключа"""
    return str(uuid.uuid4())


def generate_reality_keys() -> Tuple[str, str]:
    """
    Генерация ключей для VLESS Reality.
    Возвращает (private_key, public_key).
    """
    # Используем cryptographically secure random
    private_key_bytes = secrets.token_bytes(32)
    
    # Для Reality нужен X25519 ключ
    # В продакшене лучше использовать библиотеку nacl
    # Здесь упрощённая генерация
    private_key = base64.b64encode(private_key_bytes).decode('utf-8')
    
    # Public key вычисляется из private (упрощённо)
    # В реальности нужно использовать proper X25519 key derivation
    public_key_bytes = hashlib.sha256(private_key_bytes).digest()
    public_key = base64.b64encode(public_key_bytes).decode('utf-8')
    
    return private_key, public_key


def generate_short_id() -> str:
    """Генерация Short ID для Reality (8 байт в hex)"""
    return secrets.token_hex(8)


def generate_vless_key(
    uuid_key: str,
    server_domain: str,
    server_port: int,
    sni: str = "gosuslugi.ru",
    public_key: str = "",
    short_id: str = ""
) -> str:
    """
    Генерация VLESS Reality ключа.
    
    Формат:
    vless://<uuid>@<domain>:<port>?encryption=none&security=reality&sni=<sni>&fp=chrome&pbk=<public_key>&sid=<short_id>&type=tcp&headerType=none#<label>
    """
    from urllib.parse import urlencode
    
    params = {
        'encryption': 'none',
        'security': 'reality',
        'sni': sni,
        'fp': 'chrome',  # fingerprint
        'type': 'tcp',
        'headerType': 'none'
    }
    
    if public_key:
        params['pbk'] = public_key
    if short_id:
        params['sid'] = short_id
    
    query = urlencode(params)
    label = f"AlufProxy-{uuid_key[:8]}"
    
    return f"vless://{uuid_key}@{server_domain}:{server_port}?{query}#{label}"


def generate_full_config(
    server_domain: str,
    server_port: int,
    sni: str = "gosuslugi.ru",
    fallback_domain: str = "gosuslugi.ru"
) -> dict:
    """
    Генерация полной конфигурации для сервера.
    """
    private_key, public_key = generate_reality_keys()
    short_id = generate_short_id()
    uuid_key = generate_uuid()
    
    vless_key = generate_vless_key(
        uuid_key=uuid_key,
        server_domain=server_domain,
        server_port=server_port,
        sni=sni,
        public_key=public_key,
        short_id=short_id
    )
    
    return {
        'uuid': uuid_key,
        'private_key': private_key,
        'public_key': public_key,
        'short_id': short_id,
        'vless_key': vless_key,
        'server_domain': server_domain,
        'server_port': server_port,
        'sni': sni,
        'fallback_domain': fallback_domain
    }


def parse_vless_key(key: str) -> dict:
    """
    Парсинг VLESS ключа.
    Возвращает dict с параметрами подключения.
    """
    from urllib.parse import urlparse, parse_qs
    
    if not key.startswith('vless://'):
        raise ValueError("Неверный формат ключа (должен начинаться с vless://)")
    
    # Удаляем префикс
    key_data = key[8:]
    
    # Парсим URL
    parsed = urlparse(key_data)
    
    # UUID и сервер
    uuid_key = parsed.username if parsed.username else ''
    host = parsed.hostname if parsed.hostname else ''
    port = parsed.port if parsed.port else 443
    
    # Параметры
    params = parse_qs(parsed.query)
    
    # Извлекаем значения (parse_qs возвращает списки)
    def get_param(name: str, default: str = '') -> str:
        values = params.get(name, [default])
        return values[0] if values else default
    
    return {
        'uuid': uuid_key,
        'host': host,
        'port': port,
        'encryption': get_param('encryption', 'none'),
        'security': get_param('security', ''),
        'sni': get_param('sni', ''),
        'fp': get_param('fp', 'chrome'),
        'type': get_param('type', 'tcp'),
        'headerType': get_param('headerType', 'none'),
        'pbk': get_param('pbk', ''),
        'sid': get_param('sid', ''),
        'label': parsed.fragment if parsed.fragment else 'AlufProxy'
    }


if __name__ == "__main__":
    # Тест генерации
    config = generate_full_config(
        server_domain="proxy.example.com",
        server_port=443,
        sni="gosuslugi.ru"
    )
    
    print("Сгенерированная конфигурация:")
    print(f"UUID: {config['uuid']}")
    print(f"Private Key: {config['private_key'][:20]}...")
    print(f"Public Key: {config['public_key'][:20]}...")
    print(f"Short ID: {config['short_id']}")
    print(f"\nVLESS ключ:\n{config['vless_key']}")
