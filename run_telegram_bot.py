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
    
    # Проверка, какая версия бота доступна
    try:
        from language_mirror_telebot import main as telebot_main
        logger.info("Starting Language Mirror bot using telebot (PyTelegramBotAPI)")
        telebot_main()
    except ImportError:
        try:
            from language_mirror_bot import main as ptb_main
            logger.info("Starting Language Mirror bot using python-telegram-bot")
            ptb_main()
        except ImportError:
            logger.error("Could not import either bot implementation")
            print("ERROR: No bot implementation found")
            print("Make sure either pytelegrambotapi or python-telegram-bot is installed")
            print("Run: pip install pytelegrambotapi")
            sys.exit(1)

if __name__ == "__main__":
    main()