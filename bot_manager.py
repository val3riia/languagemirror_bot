#!/usr/bin/env python3
"""
Bot Manager - обеспечивает запуск только одного экземпляра Telegram бота.
Использует файловую блокировку для предотвращения конфликтов.
"""

import os
import sys
import time
import fcntl
import signal
import logging
import threading
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BotManager:
    """Менеджер для управления единственным экземпляром бота"""
    
    def __init__(self, lock_file_path="bot.lock"):
        self.lock_file_path = Path(lock_file_path)
        self.lock_file = None
        self.bot_instance = None
        self.running = False
        
    def acquire_lock(self):
        """Получает эксклюзивную блокировку"""
        try:
            self.lock_file = open(self.lock_file_path, 'w')
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_file.write(str(os.getpid()))
            self.lock_file.flush()
            logger.info(f"Lock acquired by PID {os.getpid()}")
            return True
        except (IOError, OSError) as e:
            if self.lock_file:
                self.lock_file.close()
                self.lock_file = None
            logger.warning(f"Failed to acquire lock: {e}")
            return False
    
    def release_lock(self):
        """Освобождает блокировку"""
        if self.lock_file:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                self.lock_file = None
                if self.lock_file_path.exists():
                    self.lock_file_path.unlink()
                logger.info("Lock released")
            except Exception as e:
                logger.error(f"Error releasing lock: {e}")
    
    def cleanup_and_delete_webhook(self):
        """Очищает webhook перед запуском"""
        try:
            import requests
            token = os.environ.get("TELEGRAM_TOKEN")
            if token:
                response = requests.post(f"https://api.telegram.org/bot{token}/deleteWebhook")
                logger.info("Webhook deleted")
        except Exception as e:
            logger.warning(f"Failed to delete webhook: {e}")
    
    def start_bot(self):
        """Запускает бота в защищенном режиме"""
        if not self.acquire_lock():
            logger.error("Another bot instance is already running")
            return False
        
        try:
            # Очищаем webhook
            self.cleanup_and_delete_webhook()
            time.sleep(1)
            
            # Импортируем и запускаем бота
            from language_mirror_telebot import main as bot_main
            
            self.running = True
            logger.info("Starting Language Mirror Bot with singleton protection...")
            
            # Настраиваем обработчик сигналов
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
            
            # Запускаем бота
            bot_main()
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot error: {e}")
        finally:
            self.running = False
            self.release_lock()
            
        return True
    
    def _signal_handler(self, signum, frame):
        """Обработчик сигналов для корректного завершения"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        self.release_lock()
        sys.exit(0)

def main():
    """Основная функция запуска"""
    manager = BotManager()
    
    if not manager.start_bot():
        logger.error("Failed to start bot")
        sys.exit(1)

if __name__ == "__main__":
    main()