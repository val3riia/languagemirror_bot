#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script to run the Language Mirror Telegram bot in a stable way.
This script will loop indefinitely, restarting the bot if it crashes.
"""

import os
import sys
import time
import logging
import traceback
import subprocess
from datetime import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(f"bot_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_bot():
    """Run the bot with proper error handling and restart capability."""
    logger.info("Starting Language Mirror Bot stabilizer")
    
    # Check if TELEGRAM_TOKEN is set
    if not os.environ.get("TELEGRAM_TOKEN"):
        logger.error("TELEGRAM_TOKEN environment variable is not set")
        print("ERROR: TELEGRAM_TOKEN environment variable is not set")
        print("Please set it to your Telegram bot token from BotFather")
        sys.exit(1)
    
    while True:
        try:
            logger.info("Starting bot process...")
            
            # Import and run the bot module
            from language_mirror_telebot import main
            main()
            
            # If we reach here, the bot exited normally
            logger.info("Bot exited normally, restarting in 5 seconds...")
            time.sleep(5)
            
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
            break
            
        except Exception as e:
            logger.error(f"Bot crashed with error: {e}")
            logger.error(traceback.format_exc())
            logger.info("Restarting bot in 10 seconds...")
            time.sleep(10)

if __name__ == "__main__":
    run_bot()