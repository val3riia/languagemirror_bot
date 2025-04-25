#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Прямой запуск Telegram бота без Flask.
Это позволит боту работать независимо от веб-сервера.
"""

import os
import logging
import sys

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Проверяем наличие токена Telegram
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN не установлен в переменных окружения!")
    print("Ошибка: TELEGRAM_TOKEN не установлен!")
    sys.exit(1)

# Импортируем и запускаем бота напрямую
try:
    from language_mirror_telebot import main as run_bot
    logger.info("Запуск бота напрямую...")
    run_bot()
except Exception as e:
    logger.error(f"Ошибка при запуске бота: {e}")
    import traceback
    logger.error(traceback.format_exc())
    sys.exit(1)