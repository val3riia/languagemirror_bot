#!/usr/bin/env python
"""
Скрипт для запуска Telegram бота в standalone режиме.
Этот скрипт запускает бота без запуска веб-приложения Flask.
"""
import logging
import time
import os
import sys

# Настраиваем логгирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Основная функция для запуска бота"""
    logger.info("=== Запуск Telegram бота ===")
    
    # Проверяем наличие токена Telegram
    if not os.environ.get("TELEGRAM_TOKEN"):
        logger.error("TELEGRAM_TOKEN не найден в переменных окружения!")
        return False
    
    try:
        # Импортируем модуль с ботом и запускаем его
        from language_mirror_telebot import bot, main as run_bot
        
        # Принудительно удаляем webhook перед запуском
        bot.remove_webhook()
        logger.info("Webhook успешно удален")
        
        # Ждем немного для завершения удаления webhook
        time.sleep(2)
        
        # Запускаем бота
        logger.info("Запускаем бота...")
        run_bot()
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    main()