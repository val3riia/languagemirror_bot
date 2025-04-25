#!/bin/bash

# Скрипт для запуска бота в фоновом режиме

# Останавливаем старые процессы бота
pkill -f "python.*telebot|python.*bot.py" || echo "No running bot processes found"

# Удаляем webhook в Telegram (этот шаг нужен для надежности)
python -c "
import os
import requests
token = os.environ.get('TELEGRAM_TOKEN')
if token:
    response = requests.get(f'https://api.telegram.org/bot{token}/deleteWebhook')
    print('Webhook deletion response:', response.json())
else:
    print('TELEGRAM_TOKEN not found')
"

# Ждем немного для полного освобождения бота
sleep 2

# Запускаем бота в фоновом режиме с перенаправлением вывода в лог-файл
nohup python run_telegram_bot.py > bot_log.txt 2>&1 &

# Сохраняем PID процесса в файл
echo $! > bot.pid

echo "Бот запущен в фоновом режиме с PID $(cat bot.pid)"
echo "Логи сохраняются в файл bot_log.txt"