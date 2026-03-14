#!/usr/bin/env python3
"""
Тестовый скрипт для локальной проверки AlufProxy
Запускает тестовый сервер и клиент для проверки функциональности
"""

import asyncio
import sys
import os
import json
import time
import threading
from pathlib import Path

# Добавляем client в path
sys.path.insert(0, str(Path(__file__).parent / "client"))

from vless_protocol import VLESSKey
from socks5_server import SOCKS5Server
from vless_client import VLESSClient, VLESSRealityClient

# Цвета для вывода
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")


def print_success(text: str):
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")


def print_error(text: str):
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")


def print_info(text: str):
    print(f"{Colors.YELLOW}ℹ️  {text}{Colors.RESET}")


def test_vless_key_parsing():
    """Тест парсинга VLESS ключа"""
    print_header("ТЕСТ 1: Парсинг VLESS ключа")
    
    # Сначала генерируем валидный ключ
    from client.vless_protocol import VLESSKey, generate_reality_keys, generate_short_id, generate_uuid
    
    uuid_key = generate_uuid()
    private_key, public_key = generate_reality_keys()
    short_id = generate_short_id()
    
    key = VLESSKey()
    test_key = key.generate(
        uuid_key=uuid_key,
        host="proxy.example.com",
        port=443,
        sni="gosuslugi.ru",
        public_key=public_key,
        short_id=short_id,
        label="TestKey"
    )
    
    print(f"  Сгенерированный URL: {test_key[:80]}...")
    
    try:
        parsed_key = VLESSKey(test_key)
        
        if parsed_key.is_valid:
            print_success("Ключ успешно распарсен")
            print(f"  UUID: {parsed_key.uuid}")
            print(f"  Host: {parsed_key.host}")
            print(f"  Port: {parsed_key.port}")
            print(f"  SNI: {parsed_key.sni}")
            print(f"  Public Key: {parsed_key.public_key[:30]}...")
            print(f"  Short ID: {parsed_key.short_id}")
            return True
        else:
            print_error("Ключ невалиден")
            missing = [f for f in ['uuid', 'host', 'port', 'security', 'sni', 'pbk'] if not parsed_key.parsed.get(f)]
            print(f"  Missing fields: {missing}")
            print(f"  Parsed: {parsed_key.parsed}")
            return False
            
    except Exception as e:
        print_error(f"Ошибка парсинга: {e}")
        return False


def test_vless_key_generation():
    """Тест генерации VLESS ключа"""
    print_header("ТЕСТ 2: Генерация VLESS ключа")
    
    try:
        from client.vless_protocol import VLESSKey, generate_reality_keys, generate_short_id, generate_uuid
        
        uuid_key = generate_uuid()
        private_key, public_key = generate_reality_keys()
        short_id = generate_short_id()
        
        key = VLESSKey()
        vless_url = key.generate(
            uuid_key=uuid_key,
            host="proxy.test.local",
            port=443,
            sni="gosuslugi.ru",
            public_key=public_key,
            short_id=short_id,
            label="TestKey"
        )
        
        print_success("Ключ сгенерирован")
        print(f"  URL: {vless_url[:80]}...")
        print(f"  UUID: {uuid_key}")
        print(f"  Public Key: {public_key[:30]}...")
        print(f"  Short ID: {short_id}")
        
        # Проверяем что сгенерированный ключ можно распарсить
        key2 = VLESSKey(vless_url)
        if key2.is_valid:
            print_success("Сгенерированный ключ валиден")
            return True
        else:
            print_error("Сгенерированный ключ невалиден")
            missing = [f for f in ['uuid', 'host', 'port', 'security', 'sni', 'pbk'] if not key2.parsed.get(f)]
            print(f"  Missing fields: {missing}")
            return False
            
    except Exception as e:
        print_error(f"Ошибка генерации: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_socks5_server():
    """Тест SOCKS5 сервера"""
    print_header("ТЕСТ 3: SOCKS5 сервер")
    
    server = None
    test_passed = False
    
    try:
        # Создаём сервер
        server = SOCKS5Server(host='127.0.0.1', port=19080)
        
        print_info("Запуск SOCKS5 сервера на 127.0.0.1:19080")
        
        async def dummy_handler(reader, writer, dst, port, label):
            print_info(f"Получен запрос: {dst}:{port}")
            writer.close()
        
        # Запускаем сервер в фоне
        server_task = asyncio.create_task(server.start(dummy_handler))
        
        # Даём серверу время запуститься
        await asyncio.sleep(1)
        
        if server.server is not None:
            print_success("SOCKS5 сервер запущен")
            test_passed = True
        else:
            print_error("Сервер не запустился")
        
        # Останавливаем
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
        
    except Exception as e:
        print_error(f"Ошибка: {e}")
    finally:
        if server:
            await server.stop()
    
    return test_passed


def test_config_load_save():
    """Тест сохранения/загрузки конфига"""
    print_header("ТЕСТ 4: Сохранение конфигурации")
    
    config_path = Path(__file__).parent / "client" / "test_config.json"
    
    test_config = {
        "vless_key": "vless://test-key",
        "socks5_port": 1080,
        "auto_start": True,
        "dpi_bypass": False
    }
    
    try:
        # Сохраняем
        with open(config_path, 'w') as f:
            json.dump(test_config, f, indent=2)
        print_success("Конфигурация сохранена")
        
        # Загружаем
        with open(config_path, 'r') as f:
            loaded = json.load(f)
        print_success("Конфигурация загружена")
        
        if loaded == test_config:
            print_success("Данные совпадают")
            config_path.unlink()
            return True
        else:
            print_error("Данные не совпадают")
            return False
            
    except Exception as e:
        print_error(f"Ошибка: {e}")
        return False


def test_imports():
    """Тест импорта всех модулей"""
    print_header("ТЕСТ 5: Импорт модулей")
    
    modules = [
        ("vless_protocol", "VLESSKey"),
        ("vless_client", "VLESSClient", "VLESSRealityClient"),
        ("socks5_server", "SOCKS5Server"),
        ("dpi_helper", "ZapretHelper", "GoodbyeDPIHelper"),
    ]
    
    all_ok = True
    
    for module_file, *classes in modules:
        try:
            if module_file == "vless_protocol":
                from vless_protocol import VLESSKey
            elif module_file == "vless_client":
                from vless_client import VLESSClient, VLESSRealityClient
            elif module_file == "socks5_server":
                from socks5_server import SOCKS5Server
            elif module_file == "dpi_helper":
                from dpi_helper import ZapretHelper, GoodbyeDPIHelper
            
            print_success(f"{module_file}.py - OK")
            
        except ImportError as e:
            print_error(f"{module_file}.py - Ошибка: {e}")
            all_ok = False
    
    return all_ok


async def run_all_tests():
    """Запуск всех тестов"""
    print_header("ALUFPROXY - ТЕСТИРОВАНИЕ")
    
    results = []
    
    # Тест 1: Парсинг ключа
    results.append(("Парсинг VLESS ключа", test_vless_key_parsing()))
    
    # Тест 2: Генерация ключа
    results.append(("Генерация VLESS ключа", test_vless_key_generation()))
    
    # Тест 3: Импорты
    results.append(("Импорт модулей", test_imports()))
    
    # Тест 4: Конфигурация
    results.append(("Сохранение конфигурации", test_config_load_save()))
    
    # Тест 5: SOCKS5 сервер
    results.append(("SOCKS5 сервер", await test_socks5_server()))
    
    # Итоги
    print_header("РЕЗУЛЬТАТЫ")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = f"{Colors.GREEN}✅ PASS{Colors.RESET}" if result else f"{Colors.RED}❌ FAIL{Colors.RESET}"
        print(f"  {status} - {name}")
    
    print(f"\n{Colors.BOLD}Итого: {passed}/{total} тестов пройдено{Colors.RESET}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 Все тесты пройдены!{Colors.RESET}\n")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}⚠️  Некоторые тесты не пройдены{Colors.RESET}\n")
        return 1


def main():
    """Основная функция"""
    print_info("Запуск тестов AlufProxy...")
    print_info(f"Python: {sys.version}")
    print_info(f"Путь: {Path(__file__).parent}")
    
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
