#!/bin/bash
# Скрипт для запуска телеграм-бота
set -e

# Получаем текущий рабочий каталог
CWD=$(pwd)
echo "Текущий рабочий каталог: $CWD"

# Проверяем наличие переменных окружения
if [ -z "$TELEGRAM_TOKEN" ]; then
  echo "TELEGRAM_TOKEN не установлен!"
  exit 1
fi

if [ -z "$OPENROUTER_API_KEY" ]; then
  echo "OPENROUTER_API_KEY не установлен, бот будет работать в режиме базовых шаблонов."
fi

echo "Запуск Telegram бота..."
python run_bot_stable.py
