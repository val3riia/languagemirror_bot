#!/usr/bin/env python3
"""
Скрипт для запуска Language Mirror Bot в режиме webhook.
Этот скрипт используется для запуска бота на платформах типа Render,
где webhook более предпочтителен, чем polling.
"""

import os
import logging
import sys

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    """
    Основная функция для запуска бота в режиме webhook.
    Устанавливает необходимые переменные окружения и запускает функцию run_webhook из language_mirror_telebot.py.
    """
    # Устанавливаем режим webhook
    os.environ["WEBHOOK_MODE"] = "true"
    
    # Если не задан WEBHOOK_URL, пытаемся составить его из других переменных
    if not os.environ.get("WEBHOOK_URL"):
        # Проверяем, есть ли переменная RENDER_EXTERNAL_URL (предоставляется Render)
        render_url = os.environ.get("RENDER_EXTERNAL_URL")
        if render_url:
            os.environ["WEBHOOK_URL"] = render_url
            logger.info(f"Using RENDER_EXTERNAL_URL as webhook URL: {render_url}")
        else:
            logger.warning("WEBHOOK_URL not set and couldn't construct one. Please set it manually.")
            logger.warning("Webhook URL should be like: https://your-app-name.onrender.com")
            logger.warning("Falling back to polling mode")
            os.environ["WEBHOOK_MODE"] = "false"
    
    # Импортируем функцию main из language_mirror_telebot
    from language_mirror_telebot import main
    
    # Запускаем бота
    logger.info("Starting Language Mirror Bot in webhook mode")
    main()

if __name__ == "__main__":
    main()