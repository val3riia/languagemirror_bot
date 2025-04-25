# Language Mirror Bot

Интеллектуальный Telegram-бот для персонализированного изучения английского языка, использующий искусственный интеллект для создания адаптивного и увлекательного языкового опыта.

## Основные функции

- Персонализированные диалоги для практики языка
- Определение уровня владения языком пользователя (A1-C2)
- Рекомендации статей по выбранным темам
- Система обратной связи с анализом в Excel-формате
- Административный интерфейс для мониторинга
- Хранение данных пользователей и сессий в PostgreSQL

## Технологии

- Python 3.11+
- Telegram Bot API (python-telegram-bot)
- OpenRouter API с GPT-4o mini
- PostgreSQL
- Flask
- Pandas и XlsxWriter для отчётов

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-username/language-mirror-bot.git
cd language-mirror-bot
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл .env с необходимыми переменными окружения:
```bash
cp .env.example .env
```

4. Отредактируйте файл .env, указав ваши значения для:
   - TELEGRAM_TOKEN (получите у @BotFather)
   - DATABASE_URL (строка подключения к PostgreSQL)
   - OPENROUTER_API_KEY (получите на openrouter.ai)
   - ADMIN_USERNAME и ADMIN_TELEGRAM_ID (администратор)

## Запуск бота

### Обычный запуск
```bash
python run_bot_stable.py
```

### Запуск в фоновом режиме
```bash
bash start_bot_stable.sh
```

### Веб-интерфейс администратора
```bash
python main.py
```

## Команды бота

- `/start` - Начало работы с ботом
- `/discussion` - Начать дискуссию для изучения языка
- `/stop_discussion` - Завершить текущий диалог
- `/help` - Получить справку
- `/admin_feedback` - Получить отчет по обратной связи (только для администраторов)

## Разработка

### Структура проекта
- `language_mirror_telebot.py` - Основной код бота
- `models.py` - Модели данных для SQLAlchemy
- `db_session_manager.py` - Менеджер сессий с базой данных
- `openrouter_client.py` - Взаимодействие с OpenRouter API
- `excel_report.py` - Генерация отчетов в Excel
- `add_test_feedback.py` - Добавление тестовых данных
- `test_admin_feedback.py` - Тестирование создания отчетов

### База данных
Бот использует PostgreSQL для хранения данных пользователей, сессий и обратной связи. Структура базы данных определена в файле `models.py`.

## Лицензия

MIT

## Автор

[Ваше имя]

## Благодарности

- OpenRouter за предоставление API для генерации текста
- Команде Telegram за Bot API