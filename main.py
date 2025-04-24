from app import app  # noqa: F401

# Import only when explicitly running the bot
if __name__ == "__main__":
    # The bot will be started manually using the "bot.py" script
    # The Flask app runs via gunicorn for the admin interface
    pass
