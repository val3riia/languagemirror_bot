#!/bin/bash

# Скрипт для запуска Telegram бота отдельно от веб-сервера

# Остановка других экземпляров бота
echo "Stopping any existing bot instances..."
pkill -f 'python.*language_mirror_telebot' || true
sleep 1

# Запуск бота напрямую
echo "Starting Language Mirror Telegram bot..."
python run_directly.py

# Если бот упал, выведем сообщение
if [ $? -ne 0 ]; then
    echo "Bot crashed. Check the logs for errors."
    exit 1
fi