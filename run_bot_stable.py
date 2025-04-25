#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Стабильный запуск Telegram бота для Language Mirror.
Этот скрипт:
1. Проверяет переменные окружения
2. Удаляет webhook
3. Запускает бота с надежными настройками
"""

import os
import sys
import time
import logging
import telebot

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    # Проверка наличия TELEGRAM_TOKEN
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN не установлен в переменных окружения!")
        print("Ошибка: TELEGRAM_TOKEN не установлен!")
        sys.exit(1)
    
    # Проверка OpenRouter API (не критично)
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if not openrouter_key:
        logger.warning("OPENROUTER_API_KEY не установлен. Бот будет работать в режиме базовых шаблонов.")
        print("Предупреждение: Бот будет работать без AI функционала.")
    
    # Удаление webhook перед запуском
    logger.info("Удаление webhook перед запуском polling...")
    try:
        test_bot = telebot.TeleBot(token)
        test_bot.remove_webhook()
        logger.info("Webhook успешно удален")
        
        # Даем API время на обработку изменений
        time.sleep(3)
    except Exception as e:
        logger.error(f"Ошибка при удалении webhook: {e}")
    
    # Импорт и запуск бота
    try:
        from language_mirror_telebot import bot
        logger.info("Запуск бота в режиме polling...")
        
        # Запуск в устойчивом режиме
        bot.polling(none_stop=True, interval=1, timeout=60)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()