#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Launcher script for Language Mirror Bot.
This script is designed to run the Telegram bot independently.
"""

import os
import sys
import logging

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)
    
    # Check for TELEGRAM_TOKEN environment variable
    if not os.environ.get("TELEGRAM_TOKEN"):
        logger.error("TELEGRAM_TOKEN environment variable is not set")
        print("ERROR: TELEGRAM_TOKEN environment variable is not set")
        print("Please set it to your Telegram bot token from BotFather")
        print("Example: export TELEGRAM_TOKEN='your_token_here'")
        sys.exit(1)
    
    try:
        # Import the bot module
        from language_mirror_bot import main
        
        # Start the bot
        logger.info("Starting Language Mirror Bot...")
        main()
    except ImportError as e:
        logger.error(f"Error importing bot module: {e}")
        print(f"ERROR: Could not import bot module: {e}")
        print("Make sure all required packages are installed.")
        print("Try: pip install python-telegram-bot")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        print(f"ERROR: Failed to start bot: {e}")
        sys.exit(1)