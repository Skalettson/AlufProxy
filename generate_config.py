#!/usr/bin/env python3
"""
Генератор тестовых конфигураций для AlufProxy
Создаёт тестовые ключи, конфиги для сервера и клиента

Поддержка автовыбора SNI из пула доменов.
"""

import json
import uuid
import hashlib
import secrets
import base64
import argparse
import random
import subprocess
from datetime import datetime
from pathlib import Path


# Пул SNI доменов (актуально на 16.03.2026)
SNI_DOMAINS = {
    "priority_5": [
        "www.microsoft.com", "microsoft.com",
        "www.apple.com", "apple.com",
        "gateway.icloud.com", "itunes.apple.com",
        "www.nvidia.com", "www.cisco.com", "www.amd.com",
    ],
    "priority_4": [
        "www.bbc.co.uk", "www.theguardian.com",
        "www.netflix.com", "www.spotify.com",
        "www.telegram.org", "www.whatsapp.com",
    ],
    "priority_3": [
        "www.gosuslugi.ru", "gosuslugi.ru",
        "www.sberbank.ru", "sberbank.ru",
        "www.yandex.ru", "yandex.ru",
        "www.amazon.com", "www.visa.com",
    ],
}


def check_sni_available(domain: str, timeout: int = 5) -> bool:
    """
    Проверка доступности SNI домена.
    
    Args:
        domain: Домен для проверки
        timeout: Таймаут в секундах
        
    Returns:
        True если домен доступен
    """
    try:
        result = subprocess.run(
            ["curl", "-kI", "-s", "-o", "/dev/null",
             "--connect-timeout", str(timeout),
             f"https://{domain}:443"],
            timeout=timeout + 2,
            capture_output=True
        )
        return result.returncode == 0
    except Exception:
        return False


def find_working_sni(domains: list = None, timeout: int = 5) -> str:
    """
    Поиск рабочего SNI домена.
    
    Args:
        domains: Список доменов для проверки
        timeout: Таймаут проверки
        
    Returns:
        Первый рабочий домен или случайный из priority_5
    """
    if domains is None:
        domains = SNI_DOMAINS["priority_5"] + SNI_DOMAINS["priority_4"]
    
    print(f"🔍 Поиск рабочего SNI среди {len(domains)} доменов...")
    
    for i, domain in enumerate(domains, 1):
        if i % 5 == 0:
            print(f"  Проверено {i}/{len(domains)} доменов...")
        
        if check_sni_available(domain, timeout):
            print(f"✅ Найден рабочий домен: {domain}")
            return domain
    
    # Если ничего не найдено, возвращаем случайный из priority_5
    fallback = random.choice(SNI_DOMAINS["priority_5"])
    print(f"⚠️ Не найдено рабочих доменов, используем {fallback}")
    return fallback


def generate_uuid() -> str:
    """Генерация UUID"""
    return str(uuid.uuid4())


def generate_reality_keys() -> tuple:
    """Генерация ключей Reality"""
    private_key_bytes = secrets.token_bytes(32)
    private_key = base64.b64encode(private_key_bytes).decode('utf-8')
    public_key_bytes = hashlib.sha256(private_key_bytes).digest()
    public_key = base64.b64encode(public_key_bytes).decode('utf-8')
    return private_key, public_key


def generate_short_id() -> str:
    """Генерация Short ID"""
    return secrets.token_hex(8)


def generate_vless_key(uuid_key: str, host: str, port: int, 
                       public_key: str, short_id: str, sni: str) -> str:
    """Генерация VLESS ссылки"""
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
    label = f"AlufProxy-{uuid_key[:8]}"
    
    return f"vless://{uuid_key}@{host}:{port}?{query}#{label}"


def generate_xray_config(private_key: str, short_id: str, 
                         uuid_key: str, sni: str, fallback: str) -> dict:
    """Генерация конфига для XRay сервера"""
    return {
        "log": {
            "loglevel": "info",
            "error": "/var/log/xray/error.log",
            "access": "/var/log/xray/access.log"
        },
        "inbounds": [
            {
                "port": 443,
                "protocol": "vless",
                "settings": {
                    "clients": [
                        {
                            "id": uuid_key,
                            "flow": "xtls-rprx-vision",
                            "email": "user@alufproxy.local"
                        }
                    ],
                    "decryption": "none",
                    "fallbacks": [
                        {"dest": 8080, "alpn": "h2"}
                    ]
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "reality",
                    "realitySettings": {
                        "show": False,
                        "dest": f"{fallback}:443",
                        "serverNames": [fallback, sni],
                        "privateKey": private_key,
                        "shortIds": ["", short_id]
                    }
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls"]
                }
            },
            {
                "listen": "127.0.0.1",
                "port": 8080,
                "protocol": "dokodemo-door",
                "settings": {
                    "address": fallback,
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
            {"protocol": "freedom", "tag": "direct"},
            {"protocol": "blackhole", "tag": "blocked"}
        ],
        "routing": {
            "domainStrategy": "AsIs",
            "rules": [
                {"type": "field", "ip": ["geoip:private"], "outboundTag": "blocked"}
            ]
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Генератор конфигураций AlufProxy")
    parser.add_argument("--host", default="proxy.example.com", help="Домен сервера")
    parser.add_argument("--port", type=int, default=443, help="Порт сервера")
    parser.add_argument("--sni", default=None, help="SNI домен (или --auto-sni для автовыбора)")
    parser.add_argument("--fallback", default=None, help="Fallback домен")
    parser.add_argument("--output", default="generated_config", help="Префикс выходных файлов")
    parser.add_argument("--auto-sni", action="store_true", help="Автоматический выбор рабочего SNI")
    parser.add_argument("--timeout", type=int, default=5, help="Таймаут проверки SNI в секундах")

    args = parser.parse_args()

    print("=" * 60)
    print("  AlufProxy - Генератор конфигураций")
    print("=" * 60)
    print()

    # Автовыбор SNI если указано
    if args.auto_sni or args.sni is None:
        print(" Автоматический выбор SNI...")
        args.sni = find_working_sni(timeout=args.timeout)
        if args.fallback is None:
            args.fallback = args.sni
    else:
        if args.fallback is None:
            args.fallback = args.sni

    # Генерируем ключи
    print("Генерация ключей...")
    uuid_key = generate_uuid()
    private_key, public_key = generate_reality_keys()
    short_id = generate_short_id()

    print(f"  UUID:        {uuid_key}")
    print(f"  Private Key: {private_key[:40]}...")
    print(f"  Public Key:  {public_key[:40]}...")
    print(f"  Short ID:    {short_id}")
    print(f"  SNI:         {args.sni}")
    print(f"  Fallback:    {args.fallback}")
    print()
    
    # Генерируем VLESS ключ
    vless_key = generate_vless_key(
        uuid_key=uuid_key,
        host=args.host,
        port=args.port,
        public_key=public_key,
        short_id=short_id,
        sni=args.sni
    )
    
    print("VLESS ключ для клиента:")
    print("-" * 60)
    print(vless_key)
    print("-" * 60)
    print()
    
    # Генерируем конфиг для сервера
    xray_config = generate_xray_config(
        private_key=private_key,
        short_id=short_id,
        uuid_key=uuid_key,
        sni=args.sni,
        fallback=args.fallback
    )
    
    # Сохраняем файлы
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Файл с VLESS ключом
    key_file = output_path / "vless_key.txt"
    with open(key_file, 'w', encoding='utf-8') as f:
        f.write(vless_key)
    print(f"✅ Ключ сохранён: {key_file}")
    
    # Файл с конфигом XRay
    config_file = output_path / "xray_config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(xray_config, f, indent=2, ensure_ascii=False)
    print(f"✅ Конфиг XRay сохранён: {config_file}")
    
    # Файл с информацией
    info_file = output_path / "info.json"
    info = {
        "generated_at": datetime.now().isoformat(),
        "uuid": uuid_key,
        "private_key": private_key,
        "public_key": public_key,
        "short_id": short_id,
        "host": args.host,
        "port": args.port,
        "sni": args.sni,
        "fallback": args.fallback,
        "vless_key": vless_key
    }
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=2, ensure_ascii=False)
    print(f"✅ Информация сохранена: {info_file}")
    
    # Файл для быстрого развёртывания
    deploy_file = output_path / "deploy.sh"
    with open(deploy_file, 'w', encoding='utf-8') as f:
        f.write(f"""#!/bin/bash
# Скрипт быстрого развёртывания с готовыми ключами

DOMAIN="{args.host}"
SNI="{args.sni}"
FALLBACK="{args.fallback}"
PRIVATE_KEY="{private_key}"
SHORT_ID="{short_id}"
UUID="{uuid_key}"

echo "Копирование конфига..."
cp xray_config.json /etc/xray/config.json

echo "Перезапуск XRay..."
systemctl restart xray

echo "Готово!"
echo "VLESS ключ: {vless_key}"
""")
    print(f"✅ Скрипт развёртывания сохранён: {deploy_file}")
    
    print()
    print("=" * 60)
    print("  Генерация завершена!")
    print("=" * 60)
    print()
    print("Следующие шаги:")
    print("  1. Скопируйте xray_config.json на сервер в /etc/xray/")
    print("  2. Получите SSL сертификаты (acme.sh)")
    print("  3. Запустите XRay: systemctl restart xray")
    print("  4. Используйте vless_key.txt в клиенте")
    print()


if __name__ == "__main__":
    main()
