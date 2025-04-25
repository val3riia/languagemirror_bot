# Language Mirror Bot

An intelligent Telegram bot for personalized English language learning, powered by advanced AI technologies to create adaptive and engaging language experiences.

## Overview

Language Mirror Bot помогает пользователям практиковать английский язык через интерактивные диалоги с AI-ассистентом, который адаптируется к уровню владения языком пользователя (от A1 до C2). Бот также предлагает статьи по интересующим пользователя темам и собирает обратную связь для улучшения качества обучения.

## Features

- **Адаптивные диалоги**: Бот подстраивается под уровень владения языком пользователя
- **Рекомендации статей**: Поиск и предложение релевантных статей по темам, интересующим пользователя
- **Обратная связь**: Система сбора и анализа обратной связи от пользователей
- **Административная панель**: Мониторинг использования и анализ обратной связи
- **База данных**: Хранение данных о пользователях, сессиях и взаимодействиях

## Tech Stack

- Telegram Bot API
- Python/Flask backend
- OpenRouter AI (GPT-4o mini)
- PostgreSQL
- Advanced NLP и machine learning

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/language-mirror-bot.git
   cd language-mirror-bot
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create `.env` file from the template:
   ```
   cp .env.example .env
   ```

5. Edit the `.env` file with your credentials:
   - Add your Telegram Bot Token (`TELEGRAM_TOKEN`)
   - Configure database connection (`DATABASE_URL`)
   - Add your OpenRouter API key (`OPENROUTER_API_KEY`)
   - Set admin credentials if needed

## Running the Bot

Start the bot:
```
python run_bot_stable.py
```

For development or testing:
```
python language_mirror_telebot.py
```

## Admin Dashboard

The project includes a simple web dashboard for viewing user feedback:
```
python main.py
```
Then navigate to `http://localhost:5000/admin/feedback`

## Project Structure

- `language_mirror_telebot.py` - Main bot implementation
- `models.py` - Database models
- `db_session_manager.py` - Session management with database persistence
- `openrouter_client.py` - Client for OpenRouter API (GPT models)
- `excel_report.py` - Report generation utilities
- `main.py` - Web dashboard for admin
- `run_bot_stable.py` - Stable bot runner with error handling

## License

This project is licensed under the MIT License - see the LICENSE file for details.