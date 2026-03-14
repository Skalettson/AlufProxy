"""
DPI Helper - интеграция с Zapret для обхода блокировок
Опциональный компонент для AlufProxy Client
"""

import subprocess
import logging
import os
import sys
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)


class ZapretHelper:
    """
    Helper для работы с Zapret (winws)
    """
    
    def __init__(self, bin_dir: Optional[str] = None):
        """
        Инициализация
        
        Args:
            bin_dir: Директория с winws.exe и DLL
        """
        if bin_dir:
            self.bin_dir = Path(bin_dir)
        else:
            # По умолчанию ищем в директории клиента
            self.bin_dir = Path(__file__).parent / "bin"
        
        self.winws_path = self.bin_dir / "winws.exe"
        self.process: Optional[subprocess.Popen] = None
        self.running = False
    
    def is_available(self) -> bool:
        """Проверка доступности winws.exe"""
        return self.winws_path.exists()
    
    def start(
        self,
        ports: List[int] = None,
        dpi_desync: str = "fake",
        dpi_repeats: int = 6,
        verbose: bool = False
    ) -> bool:
        """
        Запуск winws
        
        Args:
            ports: Порты для перехвата (TCP)
            dpi_desync: Метод DPI обхода (fake, multisplit)
            dpi_repeats: Количество повторений
            verbose: Подробное логирование
        
        Returns:
            True если запуск успешен
        """
        if not self.is_available():
            logger.error("winws.exe не найден")
            return False
        
        if self.process and self.process.poll() is None:
            logger.warning("winws уже запущен")
            return True
        
        # Стандартные порты
        if ports is None:
            ports = [80, 443, 8443]
        
        # Формируем команду
        cmd = [
            str(self.winws_path),
            "--wf-tcp=" + ",".join(map(str, ports)),
            "--dpi-desync=" + dpi_desync,
            "--dpi-desync-repeats=" + str(dpi_repeats),
        ]
        
        # Добавляем флаги для конкретных сервисов
        # Discord
        discord_list = self.bin_dir / "list-discord.txt"
        if discord_list.exists():
            cmd.extend([
                "--filter-udp=443",
                f"--hostlist={discord_list}",
                "--dpi-desync=fake",
                "--dpi-desync-repeats=6",
                "--new"
            ])
        
        # YouTube/Google
        google_list = self.bin_dir / "list-google.txt"
        if google_list.exists():
            cmd.extend([
                "--filter-tcp=443",
                f"--hostlist={google_list}",
                "--dpi-desync=multisplit",
                "--dpi-desync-split-seqovl=681",
                "--dpi-desync-split-pos=1",
                "--new"
            ])
        
        if verbose:
            cmd.append("--debug")
        
        logger.info(f"Запуск winws: {' '.join(cmd)}")
        
        try:
            # Запускаем в фоне (скрыто)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            self.process = subprocess.Popen(
                cmd,
                startupinfo=startupinfo,
                cwd=str(self.bin_dir)
            )
            
            # Ждём немного и проверяем, не упал ли сразу
            time.sleep(0.5)
            
            if self.process.poll() is not None:
                logger.error(f"winws не запустился (код {self.process.returncode})")
                return False
            
            self.running = True
            logger.info("winws запущен успешно")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка запуска winws: {e}")
            return False
    
    def stop(self) -> bool:
        """Остановка winws"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                logger.info("winws остановлен")
                self.process = None
                self.running = False
                return True
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process = None
                self.running = False
                return True
            except Exception as e:
                logger.error(f"Ошибка остановки winws: {e}")
                return False
        
        self.running = False
        return True
    
    def is_running(self) -> bool:
        """Проверка, запущен ли winws"""
        if self.process:
            return self.process.poll() is None
        return False
    
    def create_default_lists(self):
        """Создание списков доменов по умолчанию"""
        lists = {
            "list-discord.txt": [
                "discord.com",
                "discord.gg",
                "discordapp.com",
                "discordapp.net",
                "discordcdn.com",
                "discord.media"
            ],
            "list-google.txt": [
                "youtube.com",
                "google.com",
                "googlevideo.com",
                "ytimg.com"
            ],
            "list-exclude.txt": [
                "*.ru",
                "*.rf"
            ]
        }
        
        for filename, domains in lists.items():
            filepath = self.bin_dir / filename
            if not filepath.exists():
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write("\n".join(domains))
                logger.info(f"Создан список: {filename}")


class GoodbyeDPIHelper:
    """
    Helper для работы с GoodbyeDPI
    """
    
    def __init__(self, bin_dir: Optional[str] = None):
        if bin_dir:
            self.bin_dir = Path(bin_dir)
        else:
            self.bin_dir = Path(__file__).parent / "bin"
        
        self.goodbyedpi_path = self.bin_dir / "goodbyedpi.exe"
        self.process: Optional[subprocess.Popen] = None
    
    def is_available(self) -> bool:
        """Проверка доступности goodbyedpi.exe"""
        return self.goodbyedpi_path.exists()
    
    def start(
        self,
        mode: str = "youtube",
        verbose: bool = False
    ) -> bool:
        """
        Запуск GoodbyeDPI
        
        Args:
            mode: Режим работы (youtube, general, custom)
            verbose: Подробное логирование
        
        Returns:
            True если запуск успешен
        """
        if not self.is_available():
            logger.error("goodbyedpi.exe не найден")
            return False
        
        if self.process and self.process.poll() is None:
            logger.warning("GoodbyeDPI уже запущен")
            return True
        
        # Команды для разных режимов
        modes = {
            "youtube": [
                "-9",  # Режим для YouTube
                "--fake-from-hex",
                "14030300010101",
                "--fake-frag",
                "--ttl", "6"
            ],
            "general": [
                "-1",  # Базовый режим
                "--fake",
                "--ttl", "6"
            ],
            "discord": [
                "-9",
                "--fake-from-hex",
                "14030300010101"
            ]
        }
        
        cmd = [str(self.goodbyedpi_path)]
        cmd.extend(modes.get(mode, modes["general"]))
        
        if verbose:
            cmd.append("-v")
        
        logger.info(f"Запуск GoodbyeDPI: {' '.join(cmd)}")
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.bin_dir)
            )
            
            import time
            time.sleep(0.5)
            
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                logger.error(f"GoodbyeDPI не запустился: {stderr.decode()}")
                return False
            
            logger.info("GoodbyeDPI запущен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка запуска GoodbyeDPI: {e}")
            return False
    
    def stop(self) -> bool:
        """Остановка GoodbyeDPI"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                logger.info("GoodbyeDPI остановлен")
                self.process = None
                return True
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process = None
                return True
            except Exception as e:
                logger.error(f"Ошибка остановки GoodbyeDPI: {e}")
                return False
        
        return True
    
    def is_running(self) -> bool:
        """Проверка, запущен ли GoodbyeDPI"""
        if self.process:
            return self.process.poll() is None
        return False


if __name__ == "__main__":
    # Тест
    logging.basicConfig(level=logging.DEBUG)
    
    zapret = ZapretHelper()
    print(f"Zapret доступен: {zapret.is_available()}")
    
    gdpi = GoodbyeDPIHelper()
    print(f"GoodbyeDPI доступен: {gdpi.is_available()}")
