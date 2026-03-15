import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pathlib import Path
import os


class Database:
    def __init__(self, db_path: str = None):
        # Для Vercel используем /tmp (единственное writable место)
        if os.getenv("VERCEL"):
            self.db_path = "/tmp/alufproxy_bot.db"
        else:
            self.db_path = db_path or "data/bot.db"
        
        # Создаём директорию если нужно (только для локальной разработки)
        if not os.getenv("VERCEL"):
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._init_tables()

    def _init_tables(self):
        """Создание таблиц БД"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_banned INTEGER DEFAULT 0,
                    subscription_end TIMESTAMP,
                    in_support_mode INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS keys (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    protocol TEXT DEFAULT 'vless',
                    key TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS support_tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    status TEXT DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS support_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    is_from_admin INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ticket_id) REFERENCES support_tickets(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    key_id TEXT,
                    traffic_bytes INTEGER DEFAULT 0,
                    last_used TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (key_id) REFERENCES keys(id)
                )
            """)
            conn.commit()

    def add_user(self, user_id: int, username: str, first_name: str) -> bool:
        """Добавление нового пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO users (id, username, first_name, subscription_end) VALUES (?, ?, ?, ?)",
                    (user_id, username, first_name, datetime.now() + timedelta(days=3))
                )
                conn.commit()
                return True
        except Exception:
            return False

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получение информации о пользователе"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def is_user_banned(self, user_id: int) -> bool:
        """Проверка, забанен ли пользователь"""
        user = self.get_user(user_id)
        return user.get('is_banned', 0) == 1 if user else False

    def get_subscription_end(self, user_id: int) -> Optional[datetime]:
        """Получение даты окончания подписки"""
        user = self.get_user(user_id)
        if user and user.get('subscription_end'):
            return datetime.fromisoformat(user['subscription_end'])
        return None

    def extend_subscription(self, user_id: int, days: int) -> bool:
        """Продление подписки"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                user = self.get_user(user_id)
                if not user:
                    return False
                
                current_end = self.get_subscription_end(user_id)
                if current_end and current_end > datetime.now():
                    new_end = current_end + timedelta(days=days)
                else:
                    new_end = datetime.now() + timedelta(days=days)
                
                conn.execute(
                    "UPDATE users SET subscription_end = ? WHERE id = ?",
                    (new_end.isoformat(), user_id)
                )
                conn.commit()
                return True
        except Exception:
            return False

    def ban_user(self, user_id: int) -> bool:
        """Бан пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("UPDATE users SET is_banned = 1 WHERE id = ?", (user_id,))
                conn.commit()
                return True
        except Exception:
            return False

    def unban_user(self, user_id: int) -> bool:
        """Разбан пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("UPDATE users SET is_banned = 0 WHERE id = ?", (user_id,))
                conn.commit()
                return True
        except Exception:
            return False

    def set_support_mode(self, user_id: int, enabled: bool) -> bool:
        """Включение/выключение режима поддержки для пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE users SET in_support_mode = ? WHERE id = ?",
                    (1 if enabled else 0, user_id)
                )
                conn.commit()
                return True
        except Exception:
            return False

    def is_in_support_mode(self, user_id: int) -> bool:
        """Проверка, находится ли пользователь в режиме поддержки"""
        user = self.get_user(user_id)
        return user.get('in_support_mode', 0) == 1 if user else False

    def add_key(self, key_id: str, user_id: int, key: str, expires_at: datetime) -> bool:
        """Добавление нового ключа"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO keys (id, user_id, key, expires_at) VALUES (?, ?, ?, ?)",
                    (key_id, user_id, key, expires_at.isoformat())
                )
                conn.commit()
                return True
        except Exception:
            return False

    def get_user_keys(self, user_id: int) -> List[Dict]:
        """Получение всех ключей пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM keys WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_active_keys(self, user_id: int) -> List[Dict]:
        """Получение активных ключей пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM keys WHERE user_id = ? AND is_active = 1 AND expires_at > ? ORDER BY created_at DESC",
                (user_id, datetime.now().isoformat())
            )
            return [dict(row) for row in cursor.fetchall()]

    def deactivate_key(self, key_id: str) -> bool:
        """Деактивация ключа"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("UPDATE keys SET is_active = 0 WHERE id = ?", (key_id,))
                conn.commit()
                return True
        except Exception:
            return False

    def get_stats(self) -> Dict:
        """Получение статистики"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            active_users = conn.execute(
                "SELECT COUNT(*) FROM users WHERE subscription_end > ?",
                (datetime.now().isoformat(),)
            ).fetchone()[0]
            banned_users = conn.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1").fetchone()[0]
            total_keys = conn.execute("SELECT COUNT(*) FROM keys").fetchone()[0]
            active_keys = conn.execute(
                "SELECT COUNT(*) FROM keys WHERE is_active = 1 AND expires_at > ?",
                (datetime.now().isoformat(),)
            ).fetchone()[0]
            open_tickets = conn.execute(
                "SELECT COUNT(*) FROM support_tickets WHERE status = 'open'"
            ).fetchone()[0]
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'banned_users': banned_users,
                'total_keys': total_keys,
                'active_keys': active_keys,
                'open_tickets': open_tickets
            }

    def get_all_users(self) -> List[Dict]:
        """Получение всех пользователей"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM users ORDER BY registered_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    # === Support Tickets ===
    
    def create_support_ticket(self, user_id: int, username: str) -> int:
        """Создание нового обращения в поддержку"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "INSERT INTO support_tickets (user_id, username) VALUES (?, ?)",
                    (user_id, username)
                )
                conn.commit()
                return cursor.lastrowid
        except Exception:
            return -1

    def add_support_message(self, ticket_id: int, user_id: int, message: str, is_from_admin: bool = False) -> bool:
        """Добавление сообщения в обращение"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO support_messages (ticket_id, user_id, message, is_from_admin) VALUES (?, ?, ?, ?)",
                    (ticket_id, user_id, message, 1 if is_from_admin else 0)
                )
                conn.execute(
                    "UPDATE support_tickets SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (ticket_id,)
                )
                conn.commit()
                return True
        except Exception:
            return False

    def get_user_open_ticket(self, user_id: int) -> Optional[Dict]:
        """Получение открытого обращения пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM support_tickets WHERE user_id = ? AND status = 'open' ORDER BY id DESC LIMIT 1",
                (user_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_ticket(self, ticket_id: int) -> Optional[Dict]:
        """Получение обращения по ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM support_tickets WHERE id = ?", (ticket_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_ticket_messages(self, ticket_id: int) -> List[Dict]:
        """Получение всех сообщений обращения"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM support_messages WHERE ticket_id = ? ORDER BY created_at ASC",
                (ticket_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_open_tickets(self) -> List[Dict]:
        """Получение всех открытых обращений"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM support_tickets WHERE status = 'open' ORDER BY updated_at ASC"
            )
            return [dict(row) for row in cursor.fetchall()]

    def close_ticket(self, ticket_id: int) -> bool:
        """Закрытие обращения"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE support_tickets SET status = 'closed', closed_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (ticket_id,)
                )
                conn.commit()
                return True
        except Exception:
            return False

    def get_users_in_support_mode(self) -> List[Dict]:
        """Получение пользователей в режиме поддержки"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM users WHERE in_support_mode = 1 ORDER BY id"
            )
            return [dict(row) for row in cursor.fetchall()]
