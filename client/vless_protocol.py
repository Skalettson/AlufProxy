"""
VLESS протокол - утилиты для парсинга и работы с ключами
"""

from urllib.parse import urlparse, parse_qs, urlencode
from typing import Dict, Optional
import uuid
import hashlib
import secrets
import base64


class VLESSKey:
    """Класс для работы с VLESS ключами"""
    
    def __init__(self, key: str = ""):
        self.raw_key = key
        self.parsed = {}
        
        if key:
            self.parse(key)
    
    def parse(self, key: str) -> Dict:
        """Парсинг VLESS ключа"""
        if not key.startswith('vless://'):
            raise ValueError("Неверный формат ключа (должен начинаться с vless://)")

        # Парсим полный URL (с схемой vless://)
        parsed = urlparse(key)

        # UUID и сервер
        self.parsed = {
            'uuid': parsed.username or '',
            'host': parsed.hostname or '',
            'port': parsed.port or 443,
            'label': parsed.fragment or 'AlufProxy'
        }

        # Параметры
        params = parse_qs(parsed.query)

        def get_param(name: str, default: str = '') -> str:
            values = params.get(name, [default])
            return values[0] if values else default

        self.parsed.update({
            'encryption': get_param('encryption', 'none'),
            'security': get_param('security', ''),
            'sni': get_param('sni', ''),
            'fp': get_param('fp', 'chrome'),
            'type': get_param('type', 'tcp'),
            'headerType': get_param('headerType', 'none'),
            'pbk': get_param('pbk', ''),
            'sid': get_param('sid', ''),
            'flow': get_param('flow', '')
        })

        self.raw_key = key
        return self.parsed
    
    def generate(
        self,
        uuid_key: str = "",
        host: str = "proxy.example.com",
        port: int = 443,
        sni: str = "gosuslugi.ru",
        public_key: str = "",
        short_id: str = "",
        label: str = "AlufProxy"
    ) -> str:
        """Генерация нового VLESS Reality ключа"""
        if not uuid_key:
            uuid_key = str(uuid.uuid4())

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
        self.raw_key = f"vless://{uuid_key}@{host}:{port}?{query}#{label}"
        
        # Важно: парсим сгенерированный ключ для обновления self.parsed
        self.parse(self.raw_key)

        return self.raw_key
    
    @property
    def uuid(self) -> str:
        return self.parsed.get('uuid', '')
    
    @property
    def host(self) -> str:
        return self.parsed.get('host', '')
    
    @property
    def port(self) -> int:
        return self.parsed.get('port', 443)
    
    @property
    def sni(self) -> str:
        return self.parsed.get('sni', '')
    
    @property
    def public_key(self) -> str:
        return self.parsed.get('pbk', '')
    
    @property
    def short_id(self) -> str:
        return self.parsed.get('sid', '')
    
    @property
    def is_valid(self) -> bool:
        """Проверка валидности ключа"""
        required = ['uuid', 'host', 'port', 'security', 'sni', 'pbk']
        return all(self.parsed.get(field) for field in required)
    
    @property
    def is_reality(self) -> bool:
        """Проверка, Reality ли это"""
        return self.parsed.get('security') == 'reality'
    
    @property
    def mode(self) -> str:
        """Режим работы: 'vless' или 'direct'"""
        if self.is_valid and self.is_reality:
            return 'vless'
        return 'direct'
    
    def to_dict(self) -> Dict:
        """Конвертация в dict"""
        return self.parsed.copy()
    
    def __str__(self) -> str:
        return self.raw_key
    
    def __repr__(self) -> str:
        return f"VLESSKey(host={self.host}, port={self.port}, uuid={self.uuid[:8]}...)"


def generate_reality_keys() -> tuple:
    """Генерация X25519 ключей для Reality"""
    private_key_bytes = secrets.token_bytes(32)
    private_key = base64.b64encode(private_key_bytes).decode('utf-8')
    public_key_bytes = hashlib.sha256(private_key_bytes).digest()
    public_key = base64.b64encode(public_key_bytes).decode('utf-8')
    return private_key, public_key


def generate_short_id() -> str:
    """Генерация Short ID"""
    return secrets.token_hex(8)


def generate_uuid() -> str:
    """Генерация UUID"""
    return str(uuid.uuid4())


if __name__ == "__main__":
    # Тест
    key = VLESSKey()
    private_key, public_key = generate_reality_keys()
    short_id = generate_short_id()
    
    vless_key = key.generate(
        host="proxy.example.com",
        port=443,
        sni="gosuslugi.ru",
        public_key=public_key,
        short_id=short_id,
        label="TestKey"
    )
    
    print(f"Сгенерированный ключ:\n{vless_key}")
    print(f"\nРаспарсенные данные:")
    for k, v in key.to_dict().items():
        print(f"  {k}: {v}")
