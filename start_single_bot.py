#!/usr/bin/env python3
"""
Запуск единственного экземпляра Telegram бота.
"""

import os
import sys
import time
import requests
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_and_start():
    """Очистка и запуск бота"""
    try:
        # Останавливаем все процессы ботов
        subprocess.run(['pkill', '-f', 'python.*bot'], check=False)
        logger.info("Stopped existing bot processes")
        time.sleep(3)
        
        # Удаляем webhook
        token = os.environ.get("TELEGRAM_TOKEN")
        if token:
            response = requests.post(f"https://api.telegram.org/bot{token}/deleteWebhook")
            logger.info("Webhook deleted")
        
        # Запускаем основной модуль бота
        from language_mirror_telebot import main as bot_main
        logger.info("Starting Language Mirror Bot...")
        bot_main()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    cleanup_and_start()