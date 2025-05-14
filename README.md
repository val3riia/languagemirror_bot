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
- Telegram Bot API token
- OpenRouter API key (for accessing GPT models)
- Google service account credentials (for Google Sheets integration) - recommended
- PostgreSQL database (optional, legacy storage method)

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
# Required
TELEGRAM_TOKEN=your_telegram_bot_token
OPENROUTER_API_KEY=your_openrouter_api_key
ADMIN_USERNAME=admin_telegram_username (без символа @)
ADMIN_USER_ID=admin_telegram_user_id (числовое значение)

# Google Sheets (рекомендуется)
GOOGLE_CREDENTIALS_PATH=path/to/your/service-account-credentials.json
GOOGLE_SHEETS_KEY=your_spreadsheet_id
USE_GOOGLE_SHEETS=True

# PostgreSQL (опционально)
DATABASE_URL=your_postgresql_database_url

# Optional settings
BOT_AUTO_START=True
FEEDBACK_COMMENT_MIN_WORDS=3
MAX_DAILY_DISCUSSIONS=5
```

See `.env.example` for all available configuration options.

## Data Storage Setup

### Google Sheets (Recommended)

The bot now primarily uses Google Sheets for data storage, which simplifies hosting and eliminates the need for a database server.

To set up Google Sheets storage:

1. Create a Google Cloud project and enable the Google Sheets API
2. Create a service account and download the JSON credentials file
3. Create a new Google Sheets spreadsheet and share it with the service account email (with Editor permissions)
4. Set the following environment variables:
   ```
   GOOGLE_CREDENTIALS_PATH=path/to/your/service-account-credentials.json
   GOOGLE_SHEETS_KEY=your_spreadsheet_id
   USE_GOOGLE_SHEETS=True
   ```

The bot will automatically create the necessary sheets and structure when it first connects.

### PostgreSQL (Legacy)

Alternatively, the bot can use PostgreSQL for data storage. The database schema will be automatically created when the bot starts for the first time. This is the legacy storage method and is optional when Google Sheets is configured.

## Hosting Options

### UptimeBot Hosting (Recommended)

The bot is now designed to work seamlessly with UptimeBot for hosting. UptimeBot provides a simple and free way to keep your bot running 24/7 without requiring a dedicated server. With the Google Sheets integration, this is now the recommended hosting solution.

To set up hosting with UptimeBot:
1. Create a UptimeBot account
2. Create a new monitor pointing to your bot script (e.g., `run_bot_stable.py`)
3. Set the `BOT_AUTO_START=True` environment variable
4. Upload your credentials file for Google Sheets

### Render.com (Legacy)

The bot can still be hosted on Render.com using their web service. This was the previous recommended hosting method when using PostgreSQL, but requires a paid plan for reliable operation.

## Admin Features

Designated administrators can access additional features:
- View feedback from users via the `/admin_feedback` command
- Unlimited use of the `/discussion` command
- Export feedback reports in Excel format
- Download feedback data directly from the bot via Telegram

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.