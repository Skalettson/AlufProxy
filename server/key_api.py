#!/usr/bin/env python3
"""
API сервер для генерации VLESS Reality ключей
Используется Telegram-ботом для создания ключей
"""

import json
import uuid
import secrets
import hashlib
import base64
import sqlite3
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AlufProxy Key API")

# Конфигурация
API_KEY = "AlufProxy:L3iKh38iFLD1GdCOJaaTmUlx4YNRwqjYKu8znbGFaDEOtpPgdGN7mfeFScRldKXfbxDIKAc1GuJ0mpVLUreowyZZ4LTLv8Nc74ZDzdJ9gRnVj0HwYkdG9Hy92HkllDry05zRtVjaQrSxYKJfMgsVyy65o7OyKkuHGKU8OA8v1dCS4Olz2CjcQngDj7lawB0KpJbb4nzDczPzughV3qC7M7z69uutQ2jTcLMOMkRCxCIAPynZD2BywVneUTwut1QZ"  # Заменить на случайный ключ
DATABASE_PATH = "keys.db"
SERVER_DOMAIN = "alufproxy.ddns.net"
SERVER_PORT = 443
SNI_DOMAIN = "vtb.ru"
FALLBACK_DOMAIN = "vtb.ru"


# Модели данных
class KeyGenerateRequest(BaseModel):
    user_id: int
    days: int = 30


class KeyGenerateResponse(BaseModel):
    success: bool
    key_id: str
    vless_key: str
    expires_at: str


class KeyRevokeRequest(BaseModel):
    key_id: str


# База данных
def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Инициализация БД"""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            protocol TEXT DEFAULT 'vless',
            key TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            is_active INTEGER DEFAULT 1,
            traffic_bytes INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()


# Генерация ключей
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


def generate_vless_key(
    uuid_key: str,
    domain: str,
    port: int,
    public_key: str,
    short_id: str,
    sni: str = "vtb.ru"
) -> str:
    """Генерация VLESS Reality ссылки"""
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
    
    return f"vless://{uuid_key}@{domain}:{port}?{query}#{label}"


def generate_server_config(
    private_key: str,
    short_id: str,
    domain: str,
    port: int,
    sni: str = "vtb.ru",
    fallback: str = "vtb.ru"
) -> dict:
    """Генерация конфигурации сервера XRay"""
    return {
        "log": {
            "loglevel": "warning",
            "error": "/var/log/xray/error.log",
            "access": "/var/log/xray/access.log"
        },
        "inbounds": [
            {
                "port": port,
                "protocol": "vless",
                "settings": {
                    "clients": [],
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


# Авторизация
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Проверка API ключа"""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True


# Эндпоинты
@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    init_db()
    logger.info("API server started")


@app.get("/")
async def root():
    return {"status": "ok", "service": "AlufProxy Key API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/api/generate_key", response_model=KeyGenerateResponse)
async def generate_key(
    request: KeyGenerateRequest,
    authorized: bool = Depends(verify_api_key)
):
    """Генерация нового VLESS ключа"""
    try:
        conn = get_db()
        
        # Генерируем ключи
        key_id = str(uuid.uuid4())
        uuid_key = str(uuid.uuid4())
        private_key, public_key = generate_reality_keys()
        short_id = generate_short_id()
        
        # Генерируем VLESS ссылку
        vless_key = generate_vless_key(
            uuid_key=uuid_key,
            domain=SERVER_DOMAIN,
            port=SERVER_PORT,
            public_key=public_key,
            short_id=short_id,
            sni=SNI_DOMAIN
        )
        
        # Вычисляем дату истечения
        expires_at = datetime.now() + timedelta(days=request.days)
        
        # Сохраняем в БД
        conn.execute(
            """INSERT INTO keys (id, user_id, key, expires_at) 
               VALUES (?, ?, ?, ?)""",
            (key_id, request.user_id, vless_key, expires_at.isoformat())
        )
        
        # Добавляем пользователя если нет
        conn.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (request.user_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Generated key for user {request.user_id}: {key_id[:8]}...")
        
        return KeyGenerateResponse(
            success=True,
            key_id=key_id,
            vless_key=vless_key,
            expires_at=expires_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error generating key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/revoke_key")
async def revoke_key(
    request: KeyRevokeRequest,
    authorized: bool = Depends(verify_api_key)
):
    """Деактивация ключа"""
    try:
        conn = get_db()
        conn.execute(
            "UPDATE keys SET is_active = 0 WHERE id = ?",
            (request.key_id,)
        )
        conn.commit()
        affected = conn.total_changes
        conn.close()
        
        if affected == 0:
            raise HTTPException(status_code=404, detail="Key not found")
        
        logger.info(f"Revoked key: {request.key_id[:8]}...")
        
        return {"success": True, "message": "Key revoked"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/user_keys/{user_id}")
async def get_user_keys(
    user_id: int,
    authorized: bool = Depends(verify_api_key)
):
    """Получение ключей пользователя"""
    try:
        conn = get_db()
        cursor = conn.execute(
            """SELECT id, key, created_at, expires_at, is_active, traffic_bytes
               FROM keys WHERE user_id = ? ORDER BY created_at DESC""",
            (user_id,)
        )
        
        keys = []
        for row in cursor.fetchall():
            keys.append({
                "id": row["id"],
                "key": row["key"],
                "created_at": row["created_at"],
                "expires_at": row["expires_at"],
                "is_active": bool(row["is_active"]),
                "traffic_bytes": row["traffic_bytes"]
            })
        
        conn.close()
        
        return {"success": True, "keys": keys}
        
    except Exception as e:
        logger.error(f"Error getting user keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats(
    authorized: bool = Depends(verify_api_key)
):
    """Получение статистики"""
    try:
        conn = get_db()
        
        total_keys = conn.execute("SELECT COUNT(*) FROM keys").fetchone()[0]
        active_keys = conn.execute(
            "SELECT COUNT(*) FROM keys WHERE is_active = 1 AND expires_at > ?",
            (datetime.now().isoformat(),)
        ).fetchone()[0]
        total_users = conn.execute("SELECT COUNT(DISTINCT user_id) FROM keys").fetchone()[0]
        total_traffic = conn.execute("SELECT SUM(traffic_bytes) FROM keys").fetchone()[0] or 0
        
        conn.close()
        
        return {
            "success": True,
            "stats": {
                "total_keys": total_keys,
                "active_keys": active_keys,
                "total_users": total_users,
                "total_traffic_bytes": total_traffic
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/server_config")
async def get_server_config(
    authorized: bool = Depends(verify_api_key)
):
    """Получение конфигурации сервера"""
    private_key, public_key = generate_reality_keys()
    short_id = generate_short_id()
    
    config = generate_server_config(
        private_key=private_key,
        short_id=short_id,
        domain=SERVER_DOMAIN,
        port=SERVER_PORT,
        sni=SNI_DOMAIN,
        fallback=FALLBACK_DOMAIN
    )
    
    return {
        "success": True,
        "config": config,
        "keys": {
            "private_key": private_key,
            "public_key": public_key,
            "short_id": short_id
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
