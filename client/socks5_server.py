"""
SOCKS5 прокси сервер для AlufProxy Client
На базе tg-ws-proxy с упрощениями
Интеграция с VLESS Reality клиентом
"""

import asyncio
import logging
import socket
import struct
from typing import Optional, Tuple, Any

logger = logging.getLogger(__name__)


class SOCKS5Server:
    """
    SOCKS5 прокси сервер с поддержкой VLESS Reality
    """
    
    def __init__(
        self, 
        host: str = '127.0.0.1', 
        port: int = 1080,
        vless_config: Optional[dict] = None,
        mode: str = 'auto',  # 'auto', 'vless', 'direct', 'hybrid'
        dpi_bypass: bool = False
    ):
        self.host = host
        self.port = port
        self.vless_config = vless_config  # Конфигурация VLESS
        self.mode = mode  # Режим работы
        self.dpi_bypass = dpi_bypass  # Включить DPI-обход
        self.server = None
        self.clients = set()
        self.stats = {
            'connections': 0,
            'bytes_sent': 0,
            'bytes_received': 0
        }
        
        # DPI helper
        self.dpi_helper = None
        if dpi_bypass:
            from dpi_helper import ZapretHelper
            self.dpi_helper = ZapretHelper()
    
    async def start(self, handler=None):
        """Запуск SOCKS5 сервера"""
        # Сохраняем handler для использования в _handle_client
        self._handler = handler
        
        # Автозапуск DPI-обхода
        if self.dpi_bypass and self.dpi_helper:
            if self.dpi_helper.is_available():
                if self.dpi_helper.start():
                    logger.info("DPI-обход (winws) запущен автоматически")
                else:
                    logger.warning("Не удалось запустить DPI-обход")
            else:
                logger.warning("winws.exe не найден, DPI-обход недоступен")
        
        self.server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port
        )
        logger.info(f"SOCKS5 сервер запущен на {self.host}:{self.port}")
        
        if self.vless_config:
            logger.info(f"VLESS сервер: {self.vless_config.get('host')}:{self.vless_config.get('port')}")
        
        logger.info(f"Режим работы: {self.mode}" + (" + DPI-обход" if self.dpi_bypass else ""))
        
        async with self.server:
            await self.server.serve_forever()
    
    async def stop(self):
        """Остановка сервера"""
        # Останавливаем DPI-обход
        if self.dpi_helper and self.dpi_helper.running:
            self.dpi_helper.stop()
            logger.info("DPI-обход остановлен")
        
        # Закрываем все клиентские соединения
        for client in self.clients:
            try:
                client.close()
            except Exception:
                pass
        self.clients.clear()
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        logger.info("SOCKS5 сервер остановлен")
    
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Обработка клиентского соединения"""
        peer = writer.get_extra_info('peername')
        label = f"{peer[0]}:{peer[1]}" if peer else "?"
        self.clients.add(writer)
        self.stats['connections'] += 1
        
        try:
            # SOCKS5 greeting
            hdr = await asyncio.wait_for(reader.readexactly(2), timeout=10)
            if hdr[0] != 5:
                logger.debug(f"[{label}] Не SOCKS5 (ver={hdr[0]})")
                writer.close()
                return
            
            nmethods = hdr[1]
            await reader.readexactly(nmethods)
            writer.write(b'\x05\x00')  # no-auth
            await writer.drain()
            
            # SOCKS5 CONNECT request
            req = await asyncio.wait_for(reader.readexactly(4), timeout=10)
            _ver, cmd, _rsv, atyp = req
            
            if cmd != 1:  # Только CONNECT
                writer.write(self._socks5_reply(0x07))
                await writer.drain()
                writer.close()
                return
            
            # Читаем адрес назначения
            if atyp == 1:  # IPv4
                raw = await reader.readexactly(4)
                dst = socket.inet_ntoa(raw)
            elif atyp == 3:  # domain
                dlen = (await reader.readexactly(1))[0]
                dst = (await reader.readexactly(dlen)).decode()
            elif atyp == 4:  # IPv6
                raw = await reader.readexactly(16)
                dst = socket.inet_ntop(socket.AF_INET6, raw)
            else:
                writer.write(self._socks5_reply(0x08))
                await writer.drain()
                writer.close()
                return
            
            port = struct.unpack('!H', await reader.readexactly(2))[0]
            
            logger.info(f"[{label}] Запрос подключения к {dst}:{port}")
            
            # Отправляем успех
            writer.write(self._socks5_reply(0x00))
            await writer.drain()
            
            # Выбор режима работы
            if self.mode == 'direct':
                # Прямое подключение (DPI-обход)
                await self._handle_direct(reader, writer, dst, port, label)
            elif self.mode == 'vless' and self.vless_config:
                # Только VLESS
                await self._handle_vless(reader, writer, dst, port, label)
            elif self.mode == 'hybrid' and self.vless_config:
                # Гибридный режим: Telegram через VLESS, остальное напрямую
                if self._is_telegram_ip(dst):
                    logger.debug(f"[{label}] Telegram IP → VLESS")
                    await self._handle_vless(reader, writer, dst, port, label)
                else:
                    logger.debug(f"[{label}] Не Telegram IP → Direct")
                    await self._handle_direct(reader, writer, dst, port, label)
            elif self.mode == 'auto':
                # Автоматический выбор
                if self.vless_config:
                    # Пробуем VLESS, если не получилось — прямое
                    if await self._try_vless(reader, writer, dst, port, label):
                        pass  # VLESS успешно
                    else:
                        await self._handle_direct(reader, writer, dst, port, label)
                else:
                    # Нет VLESS конфига — прямое подключение
                    await self._handle_direct(reader, writer, dst, port, label)
            else:
                # По умолчанию — прямое подключение
                await self._handle_direct(reader, writer, dst, port, label)
            
        except asyncio.TimeoutError:
            logger.debug(f"[{label}] Timeout")
        except asyncio.IncompleteReadError:
            logger.debug(f"[{label}] Клиент отключился")
        except ConnectionResetError:
            logger.debug(f"[{label}] Connection reset")
        except Exception as e:
            logger.error(f"[{label}] Ошибка: {e}")
        finally:
            self.clients.discard(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
    
    async def _handle_direct(
        self, 
        reader: asyncio.StreamReader, 
        writer: asyncio.StreamWriter,
        dst: str,
        port: int,
        label: str
    ):
        """Прямое подключение к целевому серверу"""
        try:
            remote_reader, remote_writer = await asyncio.wait_for(
                asyncio.open_connection(dst, port),
                timeout=10
            )
            
            logger.info(f"[{label}] Прямое подключение к {dst}:{port}")
            
            # Запускаем переадресацию в обе стороны
            await self._bridge(reader, remote_writer, "client→server")
            await self._bridge(remote_reader, writer, "server→client")
            
        except Exception as e:
            logger.error(f"[{label}] Ошибка прямого подключения: {e}")
    
    async def _handle_vless(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        dst: str,
        port: int,
        label: str
    ):
        """
        Подключение через VLESS Reality
        Все запросы идут через VLESS сервер
        """
        from vless_client import VLESSRealityClient
        
        try:
            # Создаём VLESS клиент
            vless = VLESSRealityClient(
                uuid=self.vless_config['uuid'],
                host=self.vless_config['host'],
                port=self.vless_config['port'],
                sni=self.vless_config.get('sni', ''),
                public_key=self.vless_config.get('public_key', ''),
                short_id=self.vless_config.get('short_id', ''),
                flow=self.vless_config.get('flow', 'xtls-rprx-vision')
            )
            
            # Подключаемся к VLESS серверу
            if not await vless.connect():
                logger.error(f"[{label}] Не удалось подключиться к VLESS серверу")
                return False
            
            logger.info(f"[{label}] VLESS туннель к {dst}:{port}")
            
            # Передаём трафик через VLESS
            await vless.forward(reader, writer)
            return True
            
        except ImportError:
            logger.error("VLESS клиент не импортирован")
            return False
        except Exception as e:
            logger.error(f"[{label}] Ошибка VLESS подключения: {e}")
            return False
    
    async def _try_vless(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        dst: str,
        port: int,
        label: str
    ) -> bool:
        """
        Попытка подключения через VLESS
        Возвращает True если успешно, False если нужно прямое подключение
        """
        from vless_client import VLESSRealityClient
        
        try:
            vless = VLESSRealityClient(
                uuid=self.vless_config['uuid'],
                host=self.vless_config['host'],
                port=self.vless_config['port'],
                sni=self.vless_config.get('sni', ''),
                public_key=self.vless_config.get('public_key', ''),
                short_id=self.vless_config.get('short_id', ''),
                flow=self.vless_config.get('flow', 'xtls-rprx-vision')
            )
            
            if await vless.connect():
                logger.info(f"[{label}] VLESS туннель к {dst}:{port}")
                await vless.forward(reader, writer)
                return True
            return False
            
        except Exception:
            logger.debug(f"[{label}] VLESS недоступен, переключаемся на direct")
            return False
    
    async def _bridge(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        direction: str
    ):
        """Передача данных между соединениями"""
        try:
            while True:
                data = await reader.read(65536)
                if not data:
                    break
                
                # Статистика
                if direction == "client→server":
                    self.stats['bytes_sent'] += len(data)
                else:
                    self.stats['bytes_received'] += len(data)
                
                writer.write(data)
                await writer.drain()
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"{direction} поток завершён: {e}")
    
    @staticmethod
    def _socks5_reply(status: int) -> bytes:
        """Создание SOCKS5 ответа"""
        return bytes([0x05, status, 0x00, 0x01]) + b'\x00' * 6
    
    def get_stats(self) -> dict:
        """Получение статистики"""
        return {
            **self.stats,
            'active_clients': len(self.clients)
        }
    
    @staticmethod
    def _is_telegram_ip(ip: str) -> bool:
        """
        Проверка, является ли IP адресом Telegram
        Telegram IP диапазоны:
        - 149.154.160.0/20
        - 91.108.0.0/16
        - 185.76.151.0/24
        - 91.105.192.0/23
        """
        try:
            import socket
            import struct
            
            ip_num = struct.unpack('!I', socket.inet_aton(ip))[0]
            
            ranges = [
                # 149.154.160.0/20
                (struct.unpack('!I', socket.inet_aton('149.154.160.0'))[0],
                 struct.unpack('!I', socket.inet_aton('149.154.175.255'))[0]),
                # 91.108.0.0/16
                (struct.unpack('!I', socket.inet_aton('91.108.0.0'))[0],
                 struct.unpack('!I', socket.inet_aton('91.108.255.255'))[0]),
                # 185.76.151.0/24
                (struct.unpack('!I', socket.inet_aton('185.76.151.0'))[0],
                 struct.unpack('!I', socket.inet_aton('185.76.151.255'))[0]),
                # 91.105.192.0/23
                (struct.unpack('!I', socket.inet_aton('91.105.192.0'))[0],
                 struct.unpack('!I', socket.inet_aton('91.105.193.255'))[0]),
            ]
            
            return any(lo <= ip_num <= hi for lo, hi in ranges)
        except Exception:
            return False


class SOCKS5Forwarder:
    """
    Пересылка трафика через SOCKS5
    """
    
    def __init__(self, proxy_host: str = '127.0.0.1', proxy_port: int = 1080):
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
    
    async def connect(self, dst_host: str, dst_port: int) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Подключение через SOCKS5 прокси"""
        reader, writer = await asyncio.open_connection(self.proxy_host, self.proxy_port)
        
        # SOCKS5 handshake
        writer.write(b'\x05\x01\x00')  # Версия 5, 1 метод, без аутентификации
        await writer.drain()
        
        response = await reader.readexactly(2)
        if response[0] != 5:
            raise ConnectionError("Не SOCKС5 прокси")
        
        # CONNECT запрос
        atyp = 1  # IPv4
        try:
            ip_bytes = socket.inet_aton(dst_host)
        except OSError:
            # Это домен, используем тип 3
            atyp = 3
            dst_encoded = dst_host.encode()
            ip_bytes = bytes([len(dst_encoded)]) + dst_encoded
        
        port_bytes = struct.pack('!H', dst_port)
        
        writer.write(bytes([0x05, 0x01, 0x00, atyp]) + ip_bytes + port_bytes)
        await writer.drain()
        
        # Ответ
        response = await reader.readexactly(4)
        if response[0] != 5 or response[1] != 0:
            raise ConnectionError(f"SOCKS5 ошибка: {response[1]}")
        
        # Читаем оставшийся адрес (IPv4: 6 байт, IPv6: 18 байт, домен: переменный)
        if atyp == 1:
            await reader.readexactly(6)
        elif atyp == 4:
            await reader.readexactly(18)
        else:
            dlen = (await reader.readexactly(1))[0]
            await reader.readexactly(dlen + 2)
        
        return reader, writer


async def test_socks5():
    """Тест SOCKS5 сервера"""
    async def handler(reader, writer, dst, port, label):
        logger.info(f"[{label}] Подключение к {dst}:{port}")
        # Здесь будет логика подключения к целевому серверу
        writer.close()
    
    server = SOCKS5Server()
    try:
        await server.start(handler)
    except KeyboardInterrupt:
        await server.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(test_socks5())
