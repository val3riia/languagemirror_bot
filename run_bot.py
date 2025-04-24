#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Launcher for Language Mirror Bot - A Telegram bot for interactive language learning.
"""

import logging
from simple_bot import start_bot

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Language Mirror Bot...")
    start_bot()