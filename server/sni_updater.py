#!/usr/bin/env python3
"""
SNI Updater - Автоматическое обновление SNI для XRay Reality

Скрипт проверяет доступность текущего SNI домена и при необходимости
переключается на альтернативный домен из пула.

Использование:
    python sni_updater.py [--dry-run] [--notify] [--force]

Настройка cron (каждые 2 минуты):
    */2 * * * * /usr/bin/python3 /root/AlufProxy/AlufProxy/server/sni_updater.py >> /var/log/xray/sni_updater.log 2>&1
"""

import json
import os
import sys
import subprocess
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

# Добавляем текущую директорию в path для импорта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sni_domains import (
    ALL_DOMAINS,
    RF_DOMAINS,
    INTERNATIONAL_DOMAINS,
    QUICK_CHECK_DOMAINS,
    get_all_domains,
    get_unique_domains,
)

# Настройки
CONFIG_FILE = "/etc/xray/config.json"
KEYS_FILE = "/etc/xray/keys.json"
LOG_FILE = "/var/log/xray/sni_changes.log"
STATE_FILE = "/var/lib/xray/sni_state.json"
TIMEOUT = 5  # секунд

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SNIUpdater:
    """Автоматическое обновление SNI для XRay Reality"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.current_sni = None
        self.current_dest = None
        self.state = self.load_state()
    
    def load_state(self) -> dict:
        """Загрузка последнего состояния"""
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "last_sni": None,
                "last_dest": None,
                "last_change": None,
                "changes_count": 0,
                "failed_checks": 0
            }
    
    def save_state(self):
        """Сохранение состояния"""
        try:
            os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
            with open(STATE_FILE, "w") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения состояния: {e}")
    
    def get_current_config(self) -> Optional[dict]:
        """Получение текущей конфигурации XRay"""
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка чтения конфига: {e}")
            return None
    
    def get_current_sni(self) -> Optional[str]:
        """Получение текущего SNI из конфига"""
        config = self.get_current_config()
        if not config:
            return None
        
        for inbound in config.get("inbounds", []):
            if inbound.get("protocol") == "vless":
                reality_settings = inbound.get("streamSettings", {}).get("realitySettings", {})
                server_names = reality_settings.get("serverNames", [])
                if server_names:
                    return server_names[0]
        
        return None
    
    def get_current_dest(self) -> Optional[str]:
        """Получение текущего dest из конфига"""
        config = self.get_current_config()
        if not config:
            return None
        
        for inbound in config.get("inbounds", []):
            if inbound.get("protocol") == "vless":
                reality_settings = inbound.get("streamSettings", {}).get("realitySettings", {})
                dest = reality_settings.get("dest", "")
                if dest:
                    # Извлекаем домен из dest (например, "www.microsoft.com:443")
                    return dest.split(":")[0]
        
        return None
    
    def check_sni_available(self, domain: str, timeout: int = TIMEOUT) -> bool:
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
                [
                    "curl", "-kI", "-s", "-o", "/dev/null",
                    "--connect-timeout", str(timeout),
                    f"https://{domain}:443"
                ],
                timeout=timeout + 2
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def check_xray_status(self) -> str:
        """Проверка статуса XRay"""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "xray"],
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"
    
    def validate_config(self) -> bool:
        """Валидация конфига XRay"""
        try:
            result = subprocess.run(
                ["/usr/local/bin/xray", "-test", "-c", CONFIG_FILE],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                logger.error(f"Валидация конфига не пройдена: {result.stderr or result.stdout}")
                return False
            return True
        except Exception as e:
            logger.error(f"Ошибка валидации конфига: {e}")
            return False
    
    def update_config(self, new_sni: str, new_dest: str) -> bool:
        """
        Обновление конфига XRay с новым SNI.
        
        Args:
            new_sni: Новый SNI домен
            new_dest: Новый dest домен
            
        Returns:
            True если успешно
        """
        try:
            config = self.get_current_config()
            if not config:
                return False
            
            # Обновляем realitySettings
            for inbound in config.get("inbounds", []):
                if inbound.get("protocol") == "vless":
                    reality_settings = inbound.get("streamSettings", {}).get("realitySettings", {})
                    
                    # Обновляем dest
                    reality_settings["dest"] = f"{new_dest}:443"
                    
                    # Обновляем serverNames
                    reality_settings["serverNames"] = [new_sni, f"www.{new_sni}" if not new_sni.startswith("www.") else new_sni]
                    
                    logger.info(f"Обновлено dest: {new_dest}:443")
                    logger.info(f"Обновлено serverNames: {reality_settings['serverNames']}")
                    break
            
            # Сохраняем конфиг
            if not self.dry_run:
                with open(CONFIG_FILE, "w") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                logger.info(f"Конфиг сохранён в {CONFIG_FILE}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления конфига: {e}")
            return False
    
    def restart_xray(self) -> bool:
        """Перезапуск XRay"""
        try:
            if self.dry_run:
                logger.info("[DRY RUN] Перезапуск XRay")
                return True
            
            logger.info("Перезапуск XRay...")
            
            # Перезапускаем через systemctl
            subprocess.run(
                ["systemctl", "restart", "xray"],
                capture_output=True,
                timeout=30
            )
            
            # Проверяем статус
            status = self.check_xray_status()
            if status == "active":
                logger.info("✅ XRay успешно перезапущен")
                return True
            else:
                logger.error(f"❌ XRay не запустился: статус {status}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка перезапуска XRay: {e}")
            return False
    
    def find_working_sni(self, domains: list = None) -> Optional[str]:
        """
        Поиск рабочего SNI домена.
        
        Args:
            domains: Список доменов для проверки (по умолчанию все)
            
        Returns:
            Первый рабочий домен или None
        """
        if domains is None:
            # Проверяем по приоритетам
            domains = (
                ALL_DOMAINS.get("priority_5", []) +
                ALL_DOMAINS.get("priority_4", []) +
                ALL_DOMAINS.get("priority_3", [])
            )
        
        logger.info(f"Поиск рабочего SNI среди {len(domains)} доменов...")
        
        for i, domain in enumerate(domains, 1):
            if i % 10 == 0:
                logger.info(f"Проверено {i}/{len(domains)} доменов...")
            
            if self.check_sni_available(domain):
                logger.info(f"✅ Найден рабочий домен: {domain}")
                return domain
        
        logger.warning("❌ Не найдено рабочих доменов")
        return None
    
    def log_change(self, old_sni: str, new_sni: str, old_dest: str, new_dest: str):
        """Логирование смены SNI"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "old_sni": old_sni,
            "new_sni": new_sni,
            "old_dest": old_dest,
            "new_dest": new_dest,
            "reason": "auto-switch"
        }
        
        logger.info(f"Смена SNI: {old_sni} → {new_sni}")
        logger.info(f"Смена dest: {old_dest} → {new_dest}")
        
        # Обновляем состояние
        self.state["last_sni"] = new_sni
        self.state["last_dest"] = new_dest
        self.state["last_change"] = log_entry["timestamp"]
        self.state["changes_count"] = self.state.get("changes_count", 0) + 1
        self.state["failed_checks"] = 0
        self.save_state()
    
    def run(self, force: bool = False, notify: bool = False) -> bool:
        """
        Запуск проверки и обновления SNI.
        
        Args:
            force: Принудительное обновление
            notify: Отправить уведомление
            
        Returns:
            True если успешно
        """
        logger.info("=" * 60)
        logger.info("  SNI Updater - Проверка и обновление SNI")
        logger.info("=" * 60)
        
        # Получаем текущие значения
        current_sni = self.get_current_sni()
        current_dest = self.get_current_dest()
        
        logger.info(f"Текущий SNI: {current_sni}")
        logger.info(f"Текущий dest: {current_dest}")
        
        # Если принудительное обновление
        if force:
            logger.info("🔄 Принудительное обновление SNI...")
            new_dest = self.find_working_sni()
            if new_dest and new_dest != current_dest:
                if self.update_config(new_dest, new_dest):
                    if self.validate_config():
                        if self.restart_xray():
                            self.log_change(current_sni, new_dest, current_dest, new_dest)
                            return True
            return False
        
        # Проверяем доступность текущего dest
        if current_dest:
            logger.info(f"Проверка доступности {current_dest}...")
            
            if not self.check_sni_available(current_dest):
                logger.warning(f"⚠️ Домен {current_dest} недоступен!")
                
                # Увеличиваем счётчик неудач
                self.state["failed_checks"] = self.state.get("failed_checks", 0) + 1
                self.save_state()
                
                # Если 3 неудачи подряд - ищем новый
                if self.state["failed_checks"] >= 3:
                    logger.info("🔍 Поиск альтернативного домена...")
                    new_dest = self.find_working_sni()
                    
                    if new_dest and new_dest != current_dest:
                        logger.info(f"📝 Обновление конфига с {current_dest} на {new_dest}")
                        
                        if self.update_config(new_dest, new_dest):
                            if self.validate_config():
                                if self.restart_xray():
                                    self.log_change(current_sni, new_dest, current_dest, new_dest)
                                    
                                    # Уведомление
                                    if notify:
                                        self.send_notification(current_dest, new_dest)
                                    
                                    return True
                else:
                    logger.info(f"Неудачная проверка {self.state['failed_checks']}/3")
            else:
                logger.info(f"✅ Домен {current_dest} доступен")
                self.state["failed_checks"] = 0
                self.save_state()
        else:
            logger.error("Не удалось определить текущий dest")
        
        return True
    
    def send_notification(self, old_dest: str, new_dest: str):
        """Отправка уведомления о смене SNI"""
        try:
            # Здесь можно добавить отправку в Telegram
            message = (
                f"🔄 AlufProxy: Смена SNI\n"
                f"Старый: {old_dest}\n"
                f"Новый: {new_dest}\n"
                f"Время: {datetime.now().strftime('%H:%M:%S')}"
            )
            logger.info(f"📢 Уведомление: {message}")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {e}")
    
    def show_status(self):
        """Показать текущий статус"""
        print("=" * 60)
        print("  SNI Updater Status")
        print("=" * 60)
        print()
        print(f"Текущий SNI: {self.get_current_sni()}")
        print(f"Текущий dest: {self.get_current_dest()}")
        print()
        print(f"Последняя смена: {self.state.get('last_change', 'никогда')}")
        print(f"Всего смен: {self.state.get('changes_count', 0)}")
        print(f"Неудачных проверок: {self.state.get('failed_checks', 0)}")
        print()
        print(f"Статус XRay: {self.check_xray_status()}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Автоматическое обновление SNI для XRay Reality"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Режим сухой проверки (без изменений)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Принудительное обновление SNI"
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Отправить уведомление при смене SNI"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Показать текущий статус"
    )
    
    args = parser.parse_args()
    
    updater = SNIUpdater(dry_run=args.dry_run)
    
    if args.status:
        updater.show_status()
    else:
        success = updater.run(force=args.force, notify=args.notify)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
