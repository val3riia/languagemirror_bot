# Инструкция по развертыванию Language Mirror Bot на Render

## Предварительные условия

Для успешного развертывания Language Mirror Bot на Render вам понадобится:

1. Аккаунт на [Render](https://render.com)
2. Аккаунт на [GitHub](https://github.com) (опционально, для настройки автоматического деплоя)
3. Токен для Telegram бота (получается через [@BotFather](https://t.me/BotFather))
4. Ключ API для OpenRouter (получается на [OpenRouter](https://openrouter.ai))
5. URL для базы данных PostgreSQL (можно создать базу данных на Render или использовать внешнюю, например, Neon)

## Варианты развертывания

### Вариант 1: Через render.yaml (рекомендуется)

1. Форкните репозиторий на GitHub
2. В Render перейдите в "Blueprint" и выберите "New Blueprint Instance"
3. Укажите ссылку на ваш репозиторий
4. Render автоматически найдет файл render.yaml и предложит создать сервисы
5. Заполните необходимые переменные окружения:
   - `DATABASE_URL`: URL для подключения к базе данных PostgreSQL
   - `TELEGRAM_TOKEN`: Токен вашего Telegram бота
   - `WEBHOOK_URL`: URL вашего сервиса на Render (обычно https://language-mirror-bot.onrender.com)
   - `ADMIN_USERNAME`: Имя пользователя администратора
   - `ADMIN_USER_ID`: ID пользователя администратора
   - `OPENROUTER_API_KEY`: Ключ API для OpenRouter

### Вариант 2: Ручная настройка

1. В Render перейдите в раздел "Web Services" и нажмите "New Web Service"
2. Подключите ваш репозиторий
3. Настройте следующие параметры:
   - **Name**: Language Mirror Bot
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python run_webhook.py`

4. Добавьте переменные окружения:
   - `PYTHON_VERSION`: 3.11.0
   - `DATABASE_URL`: URL для подключения к базе данных PostgreSQL
   - `TELEGRAM_TOKEN`: Токен вашего Telegram бота
   - `WEBHOOK_URL`: URL вашего сервиса на Render (обычно https://language-mirror-bot.onrender.com)
   - `WEBHOOK_MODE`: true
   - `ADMIN_USERNAME`: Имя пользователя администратора
   - `ADMIN_USER_ID`: ID пользователя администратора
   - `OPENROUTER_API_KEY`: Ключ API для OpenRouter

## Проверка работоспособности

После успешного развертывания:

1. Откройте URL вашего сервиса в браузере — вы должны увидеть сообщение "Language Mirror Bot is running in webhook mode"
2. Отправьте боту команду `/start` в Telegram

## Дополнительные инструкции

### Создание базы данных на Render

1. В Render перейдите в раздел "PostgreSQL" и нажмите "New PostgreSQL"
2. Заполните необходимые поля и создайте базу данных
3. После создания вы получите `Internal Database URL` — используйте его как значение для переменной `DATABASE_URL`

### Настройка администраторов

1. Узнайте свой Telegram ID (можно использовать бота [@userinfobot](https://t.me/userinfobot))
2. Укажите ваш Telegram ID в переменной окружения `ADMIN_USER_ID` и ваше имя пользователя в `ADMIN_USERNAME`

### Обновление бота

При использовании автоматического деплоя через GitHub, бот будет обновляться автоматически при пуше изменений в репозиторий.

### Логи и отладка

1. В Render перейдите на страницу вашего сервиса
2. Выберите вкладку "Logs" для просмотра логов
3. При возникновении проблем проверьте логи на наличие ошибок