#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Launcher for Language Mirror Telegram Bot.
This script imports and runs the main bot function.
"""

import os
import sys
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    # Проверка наличия TELEGRAM_TOKEN
    if not os.environ.get("TELEGRAM_TOKEN"):
        logger.error("TELEGRAM_TOKEN environment variable is not set")
        print("ERROR: TELEGRAM_TOKEN environment variable is not set")
        print("Please get a token from @BotFather and set it as an environment variable")
        print("Example: export TELEGRAM_TOKEN=your_token_here")
        sys.exit(1)
    
    # Принудительно удаляем webhook перед запуском
    import telebot
    try:
        token = os.environ.get("TELEGRAM_TOKEN")
        bot = telebot.TeleBot(token)
        bot.remove_webhook()
        logger.info("Webhook removed successfully")
    except Exception as e:
        logger.error(f"Error removing webhook: {e}")
    
    # Проверка, какая версия бота доступна
    try:
        import telebot
        import time
        # Даем Telegram API время закрыть предыдущие соединения
        time.sleep(3)
        
        # Запускаем бота напрямую
        from language_mirror_telebot import bot
        logger.info("Starting Language Mirror bot using telebot (PyTelegramBotAPI)")
        
        # Запускаем bot.polling напрямую
        logger.info("Starting bot polling...")
        bot.polling(none_stop=True, interval=1, timeout=60)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()