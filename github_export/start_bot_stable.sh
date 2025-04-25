#!/bin/bash

# Скрипт для запуска и поддержания работы бота Telegram
# Этот скрипт запускает бота в фоновом режиме и перезапускает его в случае сбоя

# Проверка наличия переменных окружения
if [ -z "$TELEGRAM_TOKEN" ]; then
    echo "ERROR: TELEGRAM_TOKEN environment variable is not set."
    echo "Please set it to your Telegram bot token from BotFather."
    exit 1
fi

# Идентификатор процесса бота
PID_FILE="bot.pid"

# Функция для остановки текущего процесса бота
stop_bot() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo "Stopping bot process with PID $PID..."
            kill $PID
            sleep 2
            # Проверяем, остановился ли процесс
            if ps -p $PID > /dev/null 2>&1; then
                echo "Process did not stop gracefully, forcing termination..."
                kill -9 $PID
            fi
        else
            echo "Bot process with PID $PID is not running."
        fi
        rm -f "$PID_FILE"
    else
        echo "No PID file found."
    fi
}

# Функция для запуска бота
start_bot() {
    echo "Starting Language Mirror Bot..."
    
    # Запускаем бота в фоновом режиме
    python run_bot_stable.py &
    
    # Сохраняем PID процесса
    BOT_PID=$!
    echo $BOT_PID > "$PID_FILE"
    
    echo "Bot started with PID $BOT_PID"
    return 0
}

# Проверка наличия процесса бота
check_bot() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            return 0  # Бот запущен
        else
            return 1  # Бот не запущен
        fi
    else
        return 1  # PID-файл не существует
    fi
}

# Обработка параметров командной строки
case "$1" in
    start)
        if check_bot; then
            echo "Bot already running with PID $(cat $PID_FILE)"
        else
            start_bot
        fi
        ;;
    stop)
        stop_bot
        ;;
    restart)
        stop_bot
        sleep 1
        start_bot
        ;;
    status)
        if check_bot; then
            echo "Bot is running with PID $(cat $PID_FILE)"
        else
            echo "Bot is not running"
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac

exit 0