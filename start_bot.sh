#!/bin/bash

# Скрипт для запуска Language Mirror Bot

echo "Starting Language Mirror Bot..."

# Проверяем наличие переменной окружения TELEGRAM_TOKEN
if [ -z "$TELEGRAM_TOKEN" ]; then
    echo "Error: TELEGRAM_TOKEN environment variable is not set."
    echo "Please set your Telegram bot token as an environment variable."
    echo "For example: export TELEGRAM_TOKEN=your_token_here"
    exit 1
fi

# Проверяем наличие Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH."
    exit 1
fi

# Запускаем бота
python3 language_mirror_telebot.py