#!/bin/bash

echo "=== Запуск Language Mirror Bot в режиме webhook ==="

# Сначала останавливаем все процессы бота и удаляем webhook
python fix_bot_conflicts.py

# Задаем переменные среды для webhook
export WEBHOOK_MODE="true"
echo "Установлен режим webhook: WEBHOOK_MODE=true"

# Если не указан WEBHOOK_URL, пытаемся получить из аргумента
if [ -z "$WEBHOOK_URL" ] && [ ! -z "$1" ]; then
    export WEBHOOK_URL="$1"
    echo "Установлен WEBHOOK_URL: $WEBHOOK_URL"
fi

# Если есть PORT в окружении (обычно предоставляется Render), используем его
if [ ! -z "$PORT" ]; then
    echo "Используется PORT из окружения: $PORT"
else
    # Иначе используем порт по умолчанию
    export PORT="8443"
    echo "Установлен порт по умолчанию: 8443"
fi

# Запускаем бота через скрипт webhook
echo "Запуск бота в режиме webhook..."
python run_webhook.py