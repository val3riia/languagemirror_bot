#!/usr/bin/env python3
"""
Чистый запуск Telegram бота без конфликтов.
Этот скрипт останавливает все существующие экземпляры и запускает один новый.
"""

import os
import sys
import time
import signal
import subprocess
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def stop_all_bots():
    """Останавливает все запущенные экземпляры бота"""
    try:
        # Останавливаем все процессы, содержащие bot в команде
        subprocess.run(['pkill', '-f', 'python.*bot'], check=False)
        logger.info("Остановлены все процессы ботов")
        time.sleep(2)
    except Exception as e:
        logger.warning(f"Не удалось остановить процессы ботов: {e}")

def delete_webhook():
    """Удаляет webhook в Telegram API"""
    try:
        token = os.environ.get("TELEGRAM_TOKEN")
        if token:
            import requests
            url = f"https://api.telegram.org/bot{token}/deleteWebhook"
            response = requests.post(url)
            if response.status_code == 200:
                logger.info("Webhook успешно удален")
            else:
                logger.warning(f"Не удалось удалить webhook: {response.text}")
        else:
            logger.error("TELEGRAM_TOKEN не найден")
    except Exception as e:
        logger.error(f"Ошибка при удалении webhook: {e}")

def run_bot():
    """Запускает бота"""
    try:
        # Импортируем и запускаем основной бот
        from language_mirror_telebot import main
        logger.info("Запуск Language Mirror Bot...")
        main()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise

def main():
    """Основная функция"""
    logger.info("=== Запуск чистого бота ===")
    
    # Проверяем токен
    if not os.environ.get("TELEGRAM_TOKEN"):
        logger.error("TELEGRAM_TOKEN не установлен")
        return
    
    # Останавливаем все существующие боты
    stop_all_bots()
    
    # Удаляем webhook
    delete_webhook()
    
    # Ждем немного
    time.sleep(1)
    
    # Запускаем бота
    run_bot()

if __name__ == "__main__":
    main()