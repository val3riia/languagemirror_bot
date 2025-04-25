#!/bin/bash

# Сценарий для стабильного запуска бота с проверкой на конфликты

echo "=== Стабильный запуск Language Mirror Bot ==="

# Запускаем скрипт для исправления конфликтов
python fix_bot_conflicts.py

# Проверяем успешность запуска
if [ $? -eq 0 ]; then
    echo "Бот успешно запущен без конфликтов"
    
    # Создаем файл с PID
    ps aux | grep "python run_telegram_bot.py" | grep -v grep | awk '{print $2}' > bot.pid
    
    echo "PID бота сохранен в файле bot.pid"
    echo "Логи бота можно проверить через команду: ps aux | grep run_telegram_bot.py"
else
    echo "ОШИБКА: Не удалось запустить бот без конфликтов"
    exit 1
fi

# Выводим инструкции
echo ""
echo "Чтобы проверить статус бота: python test_bot_connection.py"
echo "Чтобы остановить бот: kill $(cat bot.pid)"
echo ""