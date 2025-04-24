#!/bin/bash

# Language Mirror Bot - скрипт запуска
# Этот скрипт проверяет наличие необходимых переменных окружения и запускает бота

# Проверка TELEGRAM_TOKEN
if [ -z "$TELEGRAM_TOKEN" ]; then
    echo "⚠️  ОШИБКА: Переменная окружения TELEGRAM_TOKEN не установлена"
    echo "Получите токен у @BotFather и установите его, например:"
    echo "export TELEGRAM_TOKEN=your_token_here"
    exit 1
fi

# Проверка OpenRouter API (опционально)
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "⚠️  ПРЕДУПРЕЖДЕНИЕ: Переменная OPENROUTER_API_KEY не установлена"
    echo "Бот будет работать в режиме резервных шаблонов, без AI"
    echo "Для использования AI получите ключ на https://openrouter.ai/keys"
    echo "Затем установите: export OPENROUTER_API_KEY=your_key_here"
    read -p "Продолжить без AI? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        exit 1
    fi
    echo "Продолжаем в режиме шаблонов..."
else
    echo "✅ OpenRouter API ключ найден"
fi

# Убедитесь, что у нас есть необходимые зависимости
pip install -q pytelegrambotapi

# Запуск бота
echo "🤖 Запуск Language Mirror Bot..."
echo "--------------------------------------"
python run_telegram_bot.py

# В случае ошибки, выводим сообщение
if [ $? -ne 0 ]; then
    echo "❌ Возникла ошибка при запуске бота"
    echo "Проверьте логи выше на наличие ошибок"
    exit 1
fi