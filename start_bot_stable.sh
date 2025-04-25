#!/bin/bash

# Стабильный скрипт запуска Language Mirror Bot
# Выполняет:
# 1. Проверку переменных окружения
# 2. Остановку других экземпляров бота
# 3. Запуск бота через стабильный launcher

# Отображаем приветствие
echo "====================================================="
echo "🤖 Language Mirror Bot - Стабильный запуск"
echo "====================================================="

# Проверка TELEGRAM_TOKEN
if [ -z "$TELEGRAM_TOKEN" ]; then
    echo "❌ ОШИБКА: Переменная окружения TELEGRAM_TOKEN не установлена"
    echo "Получите токен у @BotFather и установите его, например:"
    echo "export TELEGRAM_TOKEN=your_token_here"
    exit 1
else
    echo "✅ TELEGRAM_TOKEN найден"
fi

# Проверка OpenRouter API (опционально)
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "⚠️ ПРЕДУПРЕЖДЕНИЕ: Переменная OPENROUTER_API_KEY не установлена"
    echo "Бот будет работать в режиме резервных шаблонов, без AI"
else
    echo "✅ OpenRouter API ключ найден"
fi

# Остановка других экземпляров бота
echo "🔄 Остановка предыдущих экземпляров бота..."
pkill -f 'python.*language_mirror' || true
pkill -f 'python.*run_bot' || true
pkill -f 'python.*telebot' || true
sleep 2

# Запуск бота
echo "🚀 Запуск Language Mirror Bot..."
echo "---------------------------------------------------"
python run_bot_stable.py

# В случае ошибки
if [ $? -ne 0 ]; then
    echo "❌ Ошибка при запуске бота"
    echo "Проверьте логи выше для поиска причины"
    exit 1
fi