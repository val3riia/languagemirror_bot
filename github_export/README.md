# Language Mirror Bot

Language Mirror is an intelligent Telegram bot designed for personalized English language learning. It provides an interactive conversational experience that helps users practice English through natural conversation on topics they're interested in.

## Features

- **Conversation Practice**: Chat on any topic to improve your English
- **Level Adaptation**: Adjusts to your language proficiency (A1 to C2)
- **Error Correction**: Gentle correction of mistakes to help you improve
- **Personalized Topics**: Suggests discussion topics based on your level
- **Article Recommendations**: Suggests reading materials on topics you're interested in
- **Feedback System**: Provide feedback after conversations to help improve the bot

## Commands

- `/start` - Show welcome message and bot information
- `/discussion` - Start an English conversation or get article recommendations (limited uses per day)
- `/stop_discussion` - End the current conversation
- `/admin_feedback` - Admin command to get feedback reports (requires admin privileges)

## Requirements

- Python 3.8+
- PostgreSQL database
- Telegram Bot API token
- OpenRouter API key (for accessing GPT models)

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up environment variables (see .env.example)
4. Run the bot:
   ```
   python run_bot_stable.py
   ```

## Environment Variables

Create a `.env` file with the following variables:

```
TELEGRAM_TOKEN=your_telegram_bot_token
DATABASE_URL=your_postgresql_database_url
OPENROUTER_API_KEY=your_openrouter_api_key
ADMIN_USERNAME=admin_telegram_username
ADMIN_USER_ID=admin_telegram_user_id
```

## Database Setup

The bot uses PostgreSQL for data storage. The database schema will be automatically created when the bot starts for the first time.

## Admin Features

Designated administrators can access additional features:
- View feedback from users via the `/admin_feedback` command
- Unlimited use of the `/discussion` command
- Export feedback reports in Excel format

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.