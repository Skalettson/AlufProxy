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
                    in_support_mode INTEGER DEFAULT 0,
                    payment_status TEXT DEFAULT 'none',
                    payment_ticket_id INTEGER DEFAULT 0
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
                    type TEXT DEFAULT 'support',
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
            
            # Добавляем новые колонки если их нет
            try:
                conn.execute("ALTER TABLE users ADD COLUMN payment_status TEXT DEFAULT 'none'")
            except:
                pass
            try:
                conn.execute("ALTER TABLE users ADD COLUMN payment_ticket_id INTEGER DEFAULT 0")
            except:
                pass
            try:
                conn.execute("ALTER TABLE support_tickets ADD COLUMN type TEXT DEFAULT 'support'")
            except:
                pass
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

    def set_payment_status(self, user_id: int, status: str, ticket_id: int = 0) -> bool:
        """
        Установка статуса оплаты
        status: 'none', 'pending', 'paid'
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE users SET payment_status = ?, payment_ticket_id = ? WHERE id = ?",
                    (status, ticket_id, user_id)
                )
                conn.commit()
                return True
        except Exception:
            return False

    def get_payment_status(self, user_id: int) -> tuple:
        """Получение статуса оплаты"""
        user = self.get_user(user_id)
        if user:
            return user.get('payment_status', 'none'), user.get('payment_ticket_id', 0)
        return 'none', 0

    def create_payment_ticket(self, user_id: int, username: str, months: int, amount: int) -> int:
        """Создание заявки на оплату"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """INSERT INTO support_tickets (user_id, username, status, type) 
                       VALUES (?, ?, 'open', 'payment')""",
                    (user_id, username)
                )
                ticket_id = cursor.lastrowid
                
                # Добавляем сообщение с деталями оплаты
                conn.execute(
                    """INSERT INTO support_messages (ticket_id, user_id, message, is_from_admin)
                       VALUES (?, ?, ?, 0)""",
                    (ticket_id, user_id, f"Оплата подписки на {months} мес. ({amount} руб.)")
                )
                
                conn.commit()
                return ticket_id
        except Exception as e:
            logger.error(f"Ошибка создания заявки: {e}")
            return 0

    def get_payment_tickets(self) -> List[Dict]:
        """Получение всех активных заявок на оплату"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT t.*, u.username, u.first_name 
                   FROM support_tickets t
                   JOIN users u ON t.user_id = u.id
                   WHERE t.type = 'payment' AND t.status = 'open'
                   ORDER BY t.created_at DESC"""
            )
            return [dict(row) for row in cursor.fetchall()]

    def close_ticket(self, ticket_id: int, status: str = 'closed') -> bool:
        """Закрытие заявки"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE support_tickets SET status = ?, closed_at = ? WHERE id = ?",
                    (status, datetime.now().isoformat(), ticket_id)
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

    def get_active_keys_raw(self) -> List[Dict]:
        """Получение всех активных ключей (для API очистки)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT id, user_id, key, expires_at, is_active FROM keys WHERE is_active = 1 AND expires_at > ?",
                (datetime.now().isoformat(),)
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

    def get_users_paginated(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Получение пользователей с пагинацией"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM users ORDER BY registered_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            return [dict(row) for row in cursor.fetchall()]

    def search_users(self, query: str) -> List[Dict]:
        """Поиск пользователей по username или id"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM users WHERE username LIKE ? OR id = ? ORDER BY registered_at DESC",
                (f"%{query}%", query)
            )
            return [dict(row) for row in cursor.fetchall]

    def get_user_full(self, user_id: int) -> Optional[Dict]:
        """Получение полной информации о пользователе"""
        user = self.get_user(user_id)
        if not user:
            return None
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Ключи
            keys = conn.execute(
                "SELECT * FROM keys WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            ).fetchall()
            
            # Заявки
            tickets = conn.execute(
                "SELECT * FROM support_tickets WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            ).fetchall()
            
            user_dict = dict(user)
            user_dict['keys'] = [dict(k) for k in keys]
            user_dict['tickets'] = [dict(t) for t in tickets]
            
            return user_dict

    def extend_subscription_by_id(self, user_id: int, days: int) -> tuple:
        """Продление подписки по ID пользователя"""
        try:
            user = self.get_user(user_id)
            if not user:
                return False, "Пользователь не найден"
            
            current_end = self.get_subscription_end(user_id)
            if current_end and current_end > datetime.now():
                new_end = current_end + timedelta(days=days)
            else:
                new_end = datetime.now() + timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE users SET subscription_end = ? WHERE id = ?",
                    (new_end.isoformat(), user_id)
                )
                conn.commit()
            
            return True, new_end
        except Exception as e:
            return False, str(e)

    def delete_key(self, key_id: str) -> bool:
        """Удаление ключа"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM keys WHERE id = ?", (key_id,))
                conn.commit()
                return True
        except Exception:
            return False

    def get_all_keys(self, limit: int = 100) -> List[Dict]:
        """Получение всех ключей"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT k.*, u.username FROM keys k JOIN users u ON k.user_id = u.id ORDER BY k.created_at DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_advanced_stats(self) -> Dict:
        """Расширенная статистика"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Пользователи по статусам
            total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            active = conn.execute(
                "SELECT COUNT(*) FROM users WHERE subscription_end > ?",
                (datetime.now().isoformat(),)
            ).fetchone()[0]
            banned = conn.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1").fetchone()[0]
            
            # Подписки по срокам
            trial = conn.execute(
                "SELECT COUNT(*) FROM users WHERE payment_status = 'trial'"
            ).fetchone()[0]
            paid = conn.execute(
                "SELECT COUNT(*) FROM users WHERE payment_status = 'paid' AND subscription_end > ?",
                (datetime.now().isoformat(),)
            ).fetchone()[0]
            pending = conn.execute(
                "SELECT COUNT(*) FROM users WHERE payment_status = 'pending'"
            ).fetchone()[0]
            
            # Заявки
            open_tickets = conn.execute(
                "SELECT COUNT(*) FROM support_tickets WHERE status = 'open'"
            ).fetchone()[0]
            payment_tickets = conn.execute(
                "SELECT COUNT(*) FROM support_tickets WHERE type = 'payment' AND status = 'open'"
            ).fetchone()[0]
            
            # Ключи
            total_keys = conn.execute("SELECT COUNT(*) FROM keys").fetchone()[0]
            active_keys = conn.execute(
                "SELECT COUNT(*) FROM keys WHERE is_active = 1 AND expires_at > ?",
                (datetime.now().isoformat(),)
            ).fetchone()[0]
            
            # Топ пользователей по ключам
            top_users = conn.execute(
                "SELECT u.username, u.id, COUNT(k.id) as key_count "
                "FROM users u LEFT JOIN keys k ON u.id = k.user_id "
                "GROUP BY u.id ORDER BY key_count DESC LIMIT 5"
            ).fetchall()
            
            return {
                'total_users': total,
                'active_users': active,
                'banned_users': banned,
                'trial_users': trial,
                'paid_users': paid,
                'pending_payment': pending,
                'open_tickets': open_tickets,
                'payment_tickets': payment_tickets,
                'total_keys': total_keys,
                'active_keys': active_keys,
                'top_users': [dict(u) for u in top_users]
            }

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

    def get_users_in_support_mode(self) -> List[Dict]:
        """Получение пользователей в режиме поддержки"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM users WHERE in_support_mode = 1 ORDER BY id"
            )
            return [dict(row) for row in cursor.fetchall()]
