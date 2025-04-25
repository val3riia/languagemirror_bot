#!/bin/bash

# Стабильный скрипт запуска Language Mirror Bot
# Выполняет:
# 1. Проверку переменных окружения
# 2. Остановку других экземпляров бота
# 3. Запуск бота через стабильный launcher в фоновом режиме с записью логов

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

# Проверка прямого доступа к API Telegram
echo "🔍 Проверка подключения к Telegram API..."
python test_bot_connection.py >/dev/null 2>&1

# В случае ошибки доступа к API
if [ $? -ne 0 ]; then
    echo "❌ Ошибка подключения к Telegram API"
    echo "Запуск бота невозможен. Проверьте подключение к сети и токен."
    exit 1
fi

# Создаем папку для логов, если не существует
mkdir -p logs

# Создаем имя файла лога с текущей датой и временем
LOG_FILE="logs/bot_$(date +%Y%m%d_%H%M%S).log"

# Запуск бота в фоновом режиме с записью логов
echo "🚀 Запуск Language Mirror Bot..."
echo "Логи будут записаны в файл: $LOG_FILE"
echo "---------------------------------------------------"
nohup python language_mirror_telebot.py > "$LOG_FILE" 2>&1 &

# Запоминаем PID процесса
BOT_PID=$!
echo $BOT_PID > bot.pid

# Проверяем, запустился ли процесс
sleep 3
if ps -p $BOT_PID > /dev/null; then
    echo "✅ Бот успешно запущен в фоновом режиме (PID: $BOT_PID)"
    echo "Логи доступны в файле: $LOG_FILE"
    echo "Для остановки бота выполните: kill -9 $BOT_PID"
else
    echo "❌ Ошибка при запуске бота"
    echo "Проверьте логи в файле: $LOG_FILE"
    exit 1
fi