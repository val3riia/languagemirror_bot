#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Launcher for Language Mirror Telegram Bot.
This script imports and runs the main bot function.
"""

import sys
import logging
import os

def main():
    # Configure logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)
    
    # Check if TELEGRAM_TOKEN is set
    if not os.environ.get("TELEGRAM_TOKEN"):
        logger.error("TELEGRAM_TOKEN not set. Please set it to your Telegram bot token.")
        print("ERROR: TELEGRAM_TOKEN environment variable is not set.")
        print("Please set it to your Telegram bot token from BotFather.")
        sys.exit(1)
    
    # Try to import the bot code
    try:
        logger.info("Starting Language Mirror Telegram Bot...")
        
        # Import and run the bot
        from language_mirror_telebot import main as run_bot
        run_bot()
        
    except ImportError as e:
        logger.error(f"Failed to import bot: {e}")
        print(f"ERROR: Failed to import bot code. {e}")
        print("Make sure pytelegrambotapi is installed:")
        print("  pip install pytelegrambotapi")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        print(f"ERROR: Failed to run bot. {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()