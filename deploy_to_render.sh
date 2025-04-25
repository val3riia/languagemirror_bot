#!/bin/bash

echo "=== Развертывание Language Mirror Bot на Render ==="

# Проверяем наличие изменений для коммита в git
if git status --porcelain | grep -q .; then
    # Если есть изменения, делаем commit и push (если настроен Git)
    read -p "Найдены незакоммиченные изменения. Хотите сделать commit и push? (y/n): " do_commit
    if [ "$do_commit" = "y" ]; then
        read -p "Введите сообщение коммита: " commit_message
        git add .
        git commit -m "$commit_message"
        git push
        echo "✅ Изменения отправлены в репозиторий"
    fi
fi

# Отправляем запрос на деплой в Render
echo "🚀 Инициирование деплоя на Render..."
python trigger_render_deploy.py

echo "⏱ Деплой запущен! Deployment URL: $WEBHOOK_URL"
echo "ℹ️ Полное обновление обычно занимает 1-2 минуты"