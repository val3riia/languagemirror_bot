#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Простой бот для проверки подключения к Telegram API.
Используется для диагностики проблем.
"""

import os
import sys
import logging
import telebot

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Проверяем наличие токена
token = os.environ.get('TELEGRAM_TOKEN')
if not token:
    logger.error("TELEGRAM_TOKEN не установлен!")
    sys.exit(1)

# Создаем простой бот
bot = telebot.TeleBot(token)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я тестовый бот для диагностики. Я работаю!")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"Вы написали: {message.text}")

if __name__ == '__main__':
    logger.info("Запуск диагностического бота...")
    
    # Сначала удаляем webhook
    try:
        bot.remove_webhook()
        logger.info("Webhook удален")
    except Exception as e:
        logger.error(f"Ошибка при удалении webhook: {e}")
    
    # Запускаем бота в простом режиме
    try:
        logger.info("Запуск polling...")
        bot.polling(none_stop=True, interval=1)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        import traceback
        logger.error(traceback.format_exc())