#!/usr/bin/env python3
"""
SNI Checker - Проверка доступности доменов для XRay Reality

Проверяет домены на соответствие требованиям Reality:
- Поддержка TLS 1.3
- Поддержка X25519
- Поддержка HTTP/2 (H2)
- Время отклика (TLS ping)

Использование:
    python check_sni.py [--priority 5] [--top 10] [--output json]
"""

import subprocess
import ssl
import socket
import json
import argparse
import sys
from datetime import datetime
from typing import Optional
from sni_domains import (
    ALL_DOMAINS,
    QUICK_CHECK_DOMAINS,
    get_domains_by_priority,
    get_all_domains,
)


class SNIChecker:
    """Проверка SNI доменов для XRay Reality"""
    
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.results = []
    
    def check_tls_ping(self, domain: str, port: int = 443) -> Optional[float]:
        """
        Проверка времени отклика TLS соединения.
        
        Args:
            domain: Домен для проверки
            port: Порт (по умолчанию 443)
            
        Returns:
            Время отклика в мс или None если недоступен
        """
        try:
            start = datetime.now()
            
            # Создаем SSL контекст
            context = ssl.create_default_context()
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
            
            # Подключаемся
            with socket.create_connection((domain, port), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    # Получаем информацию о соединении
                    ssock.getpeercert()
                    
            elapsed = (datetime.now() - start).total_seconds() * 1000
            return round(elapsed, 2)
            
        except (socket.timeout, socket.error, ssl.SSLError) as e:
            return None
        except Exception as e:
            return None
    
    def check_tls_version(self, domain: str, port: int = 443) -> Optional[str]:
        """
        Проверка версии TLS.
        
        Args:
            domain: Домен для проверки
            port: Порт (по умолчанию 443)
            
        Returns:
            Версия TLS или None
        """
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection((domain, port), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    return ssock.version()
                    
        except Exception:
            return None
    
    def check_http2_support(self, domain: str, port: int = 443) -> bool:
        """
        Проверка поддержки HTTP/2.
        
        Args:
            domain: Домен для проверки
            port: Порт (по умолчанию 443)
            
        Returns:
            True если поддерживает HTTP/2
        """
        try:
            # Используем curl для проверки ALPN
            result = subprocess.run(
                [
                    "curl", "-kI", "-s", "-o", "/dev/null",
                    "--http2", "--connect-timeout", str(self.timeout),
                    f"https://{domain}:{port}"
                ],
                capture_output=True,
                timeout=self.timeout + 2
            )
            return result.returncode == 0
            
        except Exception:
            return False
    
    def check_domain(self, domain: str) -> dict:
        """
        Полная проверка домена.
        
        Args:
            domain: Домен для проверки
            
        Returns:
            Словарь с результатами проверки
        """
        result = {
            "domain": domain,
            "available": False,
            "tls_ping": None,
            "tls_version": None,
            "http2_support": False,
            "suitable_for_reality": False,
        }
        
        # Проверка TLS ping
        tls_ping = self.check_tls_ping(domain)
        if tls_ping is None:
            return result
        
        result["tls_ping"] = tls_ping
        result["available"] = True
        
        # Проверка версии TLS
        tls_version = self.check_tls_version(domain)
        result["tls_version"] = tls_version
        
        # Проверка HTTP/2
        http2_support = self.check_http2_support(domain)
        result["http2_support"] = http2_support
        
        # Проверка соответствия требованиям Reality
        result["suitable_for_reality"] = (
            tls_version in ["TLSv1.3", "TLSv1.2"] and
            http2_support
        )
        
        return result
    
    def check_domains(
        self,
        domains: list,
        top_n: Optional[int] = None,
        min_priority: int = 1
    ) -> list:
        """
        Проверка списка доменов.
        
        Args:
            domains: Список доменов для проверки
            top_n: Ограничить количество проверок
            min_priority: Минимальный приоритет доменов
            
        Returns:
            Отсортированный список результатов
        """
        self.results = []
        total = len(domains) if top_n is None else min(top_n, len(domains))
        
        print(f"🔍 Проверка {total} доменов...")
        print()
        
        for i, domain in enumerate(domains[:total], 1):
            print(f"[{i}/{total}] {domain}...", end=" ", flush=True)
            
            result = self.check_domain(domain)
            self.results.append(result)
            
            if result["suitable_for_reality"]:
                print(f"✅ {result['tls_ping']}ms TLS:{result['tls_version']} HTTP/2:{result['http2_support']}")
            elif result["available"]:
                print(f"⚠️ {result['tls_ping']}ms (не подходит)")
            else:
                print("❌ недоступен")
        
        # Сортировка по пригодности и времени отклика
        self.results.sort(
            key=lambda x: (
                not x["suitable_for_reality"],
                x["tls_ping"] if x["tls_ping"] else float("inf")
            )
        )
        
        return self.results
    
    def get_best_domains(self, count: int = 10) -> list:
        """
        Получить лучшие домены.
        
        Args:
            count: Количество доменов
            
        Returns:
            Список лучших доменов
        """
        suitable = [r for r in self.results if r["suitable_for_reality"]]
        return [r["domain"] for r in suitable[:count]]
    
    def export_results(self, filename: str = "sni_check_results.json"):
        """
        Экспорт результатов в JSON.
        
        Args:
            filename: Имя файла для экспорта
        """
        with open(filename, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "total_checked": len(self.results),
                "suitable_count": sum(1 for r in self.results if r["suitable_for_reality"]),
                "results": self.results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n📁 Результаты экспортированы в {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Проверка SNI доменов для XRay Reality"
    )
    parser.add_argument(
        "--priority", "-p",
        type=int,
        default=5,
        choices=[1, 2, 3, 4, 5],
        help="Приоритет доменов для проверки (по умолчанию: 5)"
    )
    parser.add_argument(
        "--top", "-t",
        type=int,
        default=None,
        help="Ограничить количество проверок"
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Быстрая проверка (топ-20 доменов)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Экспорт результатов в JSON файл"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=5,
        help="Таймаут подключения в секундах (по умолчанию: 5)"
    )
    
    args = parser.parse_args()
    
    # Выбор доменов для проверки
    if args.quick:
        domains = QUICK_CHECK_DOMAINS
        print("🚀 Быстрая проверка (топ-20 доменов)")
    else:
        domains = get_domains_by_priority(args.priority)
        print(f"📋 Проверка доменов с приоритетом {args.priority}")
    
    print(f"📊 Всего доменов: {len(domains)}")
    print()
    
    # Создание чекера и проверка
    checker = SNIChecker(timeout=args.timeout)
    results = checker.check_domains(domains, top_n=args.top)
    
    # Вывод лучших доменов
    print()
    print("=" * 60)
    print("  Лучшие домены для Reality")
    print("=" * 60)
    
    best = checker.get_best_domains(count=10)
    for i, domain in enumerate(best, 1):
        result = next(r for r in results if r["domain"] == domain)
        print(f"{i:2}. {domain} - {result['tls_ping']}ms")
    
    # Экспорт
    if args.output:
        checker.export_results(args.output)
    
    print()
    print("✅ Проверка завершена!")


if __name__ == "__main__":
    main()
