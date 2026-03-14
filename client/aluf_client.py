"""
AlufProxy Client - GUI приложение для Windows
Проксификатор с поддержкой VLESS Reality
Дизайн в стиле vay2run
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Optional, Dict
import customtkinter as ctk
import pystray
from PIL import Image, ImageDraw, ImageFont

from vless_protocol import VLESSKey
from socks5_server import SOCKS5Server

# Настройки приложения
APP_NAME = "AlufProxy"
APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
CONFIG_FILE = APP_DIR / "config.json"
LOG_FILE = APP_DIR / "alufproxy.log"

# Цветовая схема в стиле vay2run
# Автоматический выбор темы от системы
ctk.set_appearance_mode("system")  # Системная тема
ctk.set_default_color_theme("blue")

# Цвета
COLOR_PRIMARY = "#5D3FD3"  # Фиолетовый акцент
COLOR_PRIMARY_HOVER = "#4B32A8"
COLOR_SUCCESS = "#10B981"
COLOR_ERROR = "#EF4444"
COLOR_WARNING = "#F59E0B"

# Логирование
log = logging.getLogger("alufproxy")


def setup_logging(verbose: bool = False):
    """Настройка логирования"""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # File handler
    fh = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-5s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"))
    root.addHandler(fh)
    
    # Console handler (только если не frozen)
    if not getattr(sys, "frozen", False):
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG if verbose else logging.INFO)
        ch.setFormatter(logging.Formatter(
            "%(asctime)s  %(levelname)-5s  %(message)s",
            datefmt="%H:%M:%S"))
        root.addHandler(ch)


def load_config() -> dict:
    """Загрузка конфигурации"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.warning(f"Ошибка загрузки конфига: {e}")
    
    return {
        "vless_key": "",
        "socks5_port": 1080,
        "socks5_host": "127.0.0.1",
        "auto_start": False,
        "dpi_bypass": False,
        "verbose": False
    }


def save_config(config: dict):
    """Сохранение конфигурации"""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def _make_icon_image(size: int = 64) -> Image.Image:
    """Создание иконки приложения в стиле vay2run"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Фиолетовый круг с градиентом
    margin = 2
    draw.ellipse([margin, margin, size - margin, size - margin],
                 fill=(93, 63, 211, 255))  # COLOR_PRIMARY
    
    # Молния (логотип)
    lightning_points = [
        (size * 0.55, size * 0.2),   # Верх
        (size * 0.35, size * 0.55),  # Лево верх
        (size * 0.5, size * 0.55),   # Центр лево
        (size * 0.35, size * 0.85),  # Низ лево
        (size * 0.65, size * 0.5),   # Право низ
        (size * 0.5, size * 0.5),    # Центр право
    ]
    draw.polygon(lightning_points, fill=(255, 255, 255, 255))
    
    return img


class AlufProxyClient:
    """Основной класс клиента"""
    
    def __init__(self):
        self.config = load_config()
        self.proxy_thread: Optional[threading.Thread] = None
        self.proxy_server: Optional[SOCKS5Server] = None
        self.connected = False
        self.vless_key: Optional[VLESSKey] = None
        self.vless_config: Optional[dict] = None
    
    def parse_key(self, key: str) -> bool:
        """Парсинг VLESS ключа"""
        try:
            self.vless_key = VLESSKey(key)
            
            if not self.vless_key.is_valid:
                log.error("Ключ невалиден")
                return False
            
            # Создаём конфиг для VLESS клиента
            self.vless_config = {
                'uuid': self.vless_key.uuid,
                'host': self.vless_key.host,
                'port': self.vless_key.port,
                'sni': self.vless_key.sni,
                'public_key': self.vless_key.public_key,
                'short_id': self.vless_key.short_id,
                'flow': 'xtls-rprx-vision'
            }
            
            log.info(f"Ключ распарсен: {self.vless_key.host}:{self.vless_key.port}")
            return True
            
        except Exception as e:
            log.error(f"Ошибка парсинга ключа: {e}")
            return False
    
    def start_proxy(self) -> bool:
        """Запуск прокси сервера"""
        if self.proxy_thread and self.proxy_thread.is_alive():
            log.info("Прокси уже запущен")
            return True
        
        # Определяем режим работы
        mode = self.config.get("mode", "auto")
        dpi_bypass = self.config.get("dpi_bypass", False)
        
        # Если режим 'direct' или нет валидного ключа — используем direct
        if mode == "direct" or not self.vless_config:
            vless_config = None
            use_mode = "direct"
        elif mode == "hybrid" and self.vless_config:
            vless_config = self.vless_config
            use_mode = "hybrid"
        else:
            vless_config = self.vless_config
            use_mode = mode
        
        def run_proxy():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Создаём SOCKS5 сервер с режимом и DPI-обходом
            self.proxy_server = SOCKS5Server(
                host=self.config.get("socks5_host", "127.0.0.1"),
                port=self.config.get("socks5_port", 1080),
                vless_config=vless_config,
                mode=use_mode,
                dpi_bypass=dpi_bypass
            )
            
            try:
                loop.run_until_complete(self.proxy_server.start())
            except Exception as e:
                log.error(f"Ошибка прокси: {e}")
            finally:
                loop.close()
        
        self.proxy_thread = threading.Thread(target=run_proxy, daemon=True, name="proxy")
        self.proxy_thread.start()
        self.connected = True
        log.info(f"Прокси запущен в режиме {use_mode}" + (" + DPI-обход" if dpi_bypass else ""))
        return True
    
    def stop_proxy(self):
        """Остановка прокси"""
        if self.proxy_server:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.proxy_server.stop())
            loop.close()
        
        self.proxy_thread = None
        self.connected = False
        log.info("Прокси остановлен")
    
    def get_status(self) -> dict:
        """Получение статуса"""
        return {
            "connected": self.connected,
            "key_valid": self.vless_key.is_valid if self.vless_key else False,
            "server": self.vless_key.host if self.vless_key else "",
            "port": self.vless_key.port if self.vless_key else 0
        }


class AlufProxyGUI:
    """GUI приложение в стиле vay2run"""

    def __init__(self):
        self.client = AlufProxyClient()
        self.tray_icon = None
        self.window = None

    def create_window(self) -> ctk.CTk:
        """Создание главного окна в стиле vay2run"""
        window = ctk.CTk()
        window.title("AlufProxy")
        window.resizable(False, True)
        window.attributes("-topmost", False)

        # Размеры как в vay2run
        w, h = 480, 600
        sw = window.winfo_screenwidth()
        sh = window.winfo_screenheight()
        window.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        
        # Главный контейнер
        main_frame = ctk.CTkFrame(window, corner_radius=0, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # === ЗАГОЛОВОК ===
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent", height=80)
        header_frame.pack(fill="x", pady=(0, 20))
        header_frame.pack_propagate(False)

        # Логотип и название
        logo_label = ctk.CTkLabel(
            header_frame,
            text="⚡ AlufProxy",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLOR_PRIMARY
        )
        logo_label.pack(anchor="w", pady=(10, 5))

        subtitle = ctk.CTkLabel(
            header_frame,
            text="Проксификатор нового поколения",
            font=ctk.CTkFont(size=13),
            text_color="gray"
        )
        subtitle.pack(anchor="w")

        # === СТАТУС ===
        status_frame = ctk.CTkFrame(main_frame, corner_radius=16, fg_color="transparent")
        status_frame.pack(fill="x", pady=(0, 20))

        self.status_indicator = ctk.CTkLabel(
            status_frame,
            text="●",
            font=ctk.CTkFont(size=16),
            text_color=COLOR_ERROR
        )
        self.status_indicator.pack(side="left", padx=(0, 10))

        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Отключено",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLOR_ERROR
        )
        self.status_label.pack(side="left")

        # === КНОПКА ПОДКЛЮЧЕНИЯ ===
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent", height=70)
        button_frame.pack(fill="x", pady=(0, 25))
        button_frame.pack_propagate(False)

        self.connect_btn = ctk.CTkButton(
            button_frame,
            text="ПОДКЛЮЧИТЬСЯ",
            font=ctk.CTkFont(size=16, weight="bold"),
            width=300,
            height=54,
            corner_radius=27,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            command=self.toggle_connection
        )
        self.connect_btn.pack()

        # === VLESS КЛЮЧ ===
        key_container = ctk.CTkFrame(main_frame, fg_color="transparent")
        key_container.pack(fill="x", pady=(0, 20))

        key_label = ctk.CTkLabel(
            key_container,
            text="VLESS ключ",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_PRIMARY
        )
        key_label.pack(anchor="w", pady=(0, 8))

        self.key_entry = ctk.CTkTextbox(
            key_container,
            height=80,
            corner_radius=12,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="gray"
        )
        self.key_entry.pack(fill="x")

        # Загружаем сохранённый ключ
        if self.client.config.get("vless_key"):
            self.key_entry.insert("1.0", self.client.config["vless_key"])

        # === НАСТРОЙКИ ===
        settings_container = ctk.CTkScrollableFrame(
            main_frame,
            corner_radius=16,
            fg_color="transparent"
        )
        settings_container.pack(fill="both", expand=True, pady=(0, 15))

        # Заголовок настроек
        settings_header = ctk.CTkLabel(
            settings_container,
            text="⚙️ Настройки",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_PRIMARY
        )
        settings_header.pack(anchor="w", pady=(0, 15))

        # Режим работы
        mode_row = ctk.CTkFrame(settings_container, fg_color="transparent")
        mode_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            mode_row,
            text="Режим",
            font=ctk.CTkFont(size=13),
            width=100,
            anchor="w"
        ).pack(side="left")

        self.mode_var = ctk.StringVar(value=self.client.config.get("mode", "auto"))
        self.mode_menu = ctk.CTkOptionMenu(
            mode_row,
            values=["auto", "vless", "direct", "hybrid"],
            variable=self.mode_var,
            width=180,
            height=36,
            corner_radius=10,
            fg_color="transparent",
            button_color=COLOR_PRIMARY,
            button_hover_color=COLOR_PRIMARY_HOVER,
            font=ctk.CTkFont(size=13)
        )
        self.mode_menu.pack(side="right")

        # Порт SOCKS5
        port_row = ctk.CTkFrame(settings_container, fg_color="transparent")
        port_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            port_row,
            text="Порт",
            font=ctk.CTkFont(size=13),
            width=100,
            anchor="w"
        ).pack(side="left")

        self.port_var = ctk.StringVar(value=str(self.client.config.get("socks5_port", 1080)))
        port_entry = ctk.CTkEntry(
            port_row,
            textvariable=self.port_var,
            width=180,
            height=36,
            corner_radius=10,
            font=ctk.CTkFont(size=13)
        )
        port_entry.pack(side="right")

        # Автозапуск
        self.auto_start_var = ctk.BooleanVar(value=self.client.config.get("auto_start", False))
        auto_start_cb = ctk.CTkCheckBox(
            settings_container,
            text="Автозапуск с Windows",
            variable=self.auto_start_var,
            font=ctk.CTkFont(size=13),
            checkbox_width=20,
            checkbox_height=20,
            corner_radius=5,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER
        )
        auto_start_cb.pack(anchor="w", pady=(8, 0))

        # DPI-обход
        self.dpi_bypass_var = ctk.BooleanVar(value=self.client.config.get("dpi_bypass", False))
        dpi_cb = ctk.CTkCheckBox(
            settings_container,
            text="DPI-обход (Zapret)",
            variable=self.dpi_bypass_var,
            font=ctk.CTkFont(size=13),
            checkbox_width=20,
            checkbox_height=20,
            corner_radius=5,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER
        )
        dpi_cb.pack(anchor="w", pady=(8, 0))

        # === ЛОГИ ===
        log_container = ctk.CTkFrame(main_frame, corner_radius=16, fg_color="transparent")
        log_container.pack(fill="both", expand=True)

        log_header = ctk.CTkLabel(
            log_container,
            text="📋 Логи",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_PRIMARY,
            anchor="w"
        )
        log_header.pack(anchor="w", pady=(0, 8))

        self.log_text = ctk.CTkTextbox(
            log_container,
            height=100,
            corner_radius=12,
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color="gray",
            fg_color="transparent",
            border_width=1,
            border_color="gray"
        )
        self.log_text.pack(fill="both", expand=True)

        return window
    
    def toggle_connection(self):
        """Переключение подключения"""
        if self.client.connected:
            self.client.stop_proxy()
            self.update_status(False)
        else:
            key = self.key_entry.get("1.0", "end").strip()
            if not key:
                self.show_error("Введите VLESS ключ")
                return
            
            if not self.client.parse_key(key):
                self.show_error("Неверный формат VLESS ключа")
                return
            
            # Сохраняем ключ и настройки
            self.client.config["vless_key"] = key
            self.client.config["socks5_port"] = int(self.port_var.get())
            self.client.config["auto_start"] = self.auto_start_var.get()
            self.client.config["dpi_bypass"] = self.dpi_bypass_var.get()
            self.client.config["mode"] = self.mode_var.get()
            save_config(self.client.config)

            if self.client.start_proxy():
                self.update_status(True)
            else:
                self.show_error("Не удалось запустить прокси")
    
    def update_status(self, connected: bool):
        """Обновление статуса в стиле vay2run"""
        mode = self.mode_var.get()
        mode_name = {"auto": "Авто", "vless": "VLESS", "direct": "Direct", "hybrid": "Hybrid"}.get(mode, mode)
        
        if connected:
            # Зелёный статус
            self.status_indicator.configure(text_color=COLOR_SUCCESS)
            self.status_label.configure(
                text=f"Подключено · {mode_name}",
                text_color=COLOR_SUCCESS
            )
            self.connect_btn.configure(
                text="ОТКЛЮЧИТЬСЯ",
                fg_color="gray",
                hover_color="darkgray"
            )
            
            status = self.client.get_status()
            if mode == "direct":
                self.log_text.insert("end", f"✓ Подключено: режим Direct (DPI-обход)\n")
            elif mode == "hybrid":
                self.log_text.insert("end", f"✓ Подключено: режим Hybrid\n")
            else:
                self.log_text.insert("end", f"✓ Подключено: {status.get('server', 'N/A')}:{status.get('port', 'N/A')}\n")
        else:
            # Красный статус
            self.status_indicator.configure(text_color=COLOR_ERROR)
            self.status_label.configure(
                text="Отключено",
                text_color=COLOR_ERROR
            )
            self.connect_btn.configure(
                text="ПОДКЛЮЧИТЬСЯ",
                fg_color=COLOR_PRIMARY,
                hover_color=COLOR_PRIMARY_HOVER
            )
            self.log_text.insert("end", "○ Отключено\n")
        
        self.log_text.see("end")
    
    def show_error(self, message: str):
        """Показ ошибки"""
        self.log_text.insert("end", f"✗ {message}\n")
        self.log_text.see("end")
    
    def create_tray_icon(self):
        """Создание иконки в трее"""
        icon_image = _make_icon_image()
        
        menu = pystray.Menu(
            pystray.MenuItem("Открыть", self.open_window, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Подключиться/Отключиться", self.toggle_connection_tray),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Выход", self.exit_app)
        )
        
        self.tray_icon = pystray.Icon(APP_NAME, icon_image, "AlufProxy", menu)
        return self.tray_icon
    
    def open_window(self, icon=None, item=None):
        """Открытие окна"""
        if self.window:
            self.window.attributes("-topmost", True)
            self.window.focus_force()
    
    def toggle_connection_tray(self, icon=None, item=None):
        """Переключение из трея"""
        if self.client.connected:
            self.client.stop_proxy()
            if self.window:
                self.update_status(False)
        else:
            key = self.client.config.get("vless_key", "")
            if key and self.client.parse_key(key):
                self.client.start_proxy()
                if self.window:
                    self.update_status(True)
    
    def exit_app(self, icon=None, item=None):
        """Выход из приложения"""
        self.client.stop_proxy()
        if self.tray_icon:
            self.tray_icon.stop()
        if self.window:
            self.window.quit()
    
    def run(self):
        """Запуск приложения"""
        setup_logging(self.client.config.get("verbose", False))
        log.info("AlufProxy Client запускается")
        
        # Создаём окно
        self.window = self.create_window()
        
        # Запускаем трей в отдельном потоке
        tray_thread = threading.Thread(target=self.create_tray_icon().run, daemon=True)
        tray_thread.start()
        
        # Запускаем GUI
        self.window.protocol("WM_DELETE_WINDOW", lambda: self.window.withdraw())
        self.window.mainloop()


def main():
    app = AlufProxyGUI()
    app.run()


if __name__ == "__main__":
    main()
