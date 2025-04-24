# Language Mirror - English Learning Telegram Bot

Language Mirror is a Telegram bot that helps users learn English through natural conversation, focusing on interests and emotions rather than formal language instruction.

## Features

- **Natural Conversation**: Practice English in a way that feels like chatting with a friend
- **Level Adaptation**: The bot adapts to your English level from A1 (beginner) to C2 (proficiency)
- **Contextual Corrections**: Gentle corrections within the flow of conversation
- **Topic Suggestions**: Conversation starters appropriate for your level
- **Feedback Collection**: Share your experience after each conversation

## Setup Instructions

### Prerequisites

- Python 3.7+
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))

### Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/language-mirror.git
   cd language-mirror
   ```

2. Install dependencies:
   ```
   pip install pytelegrambotapi
   ```

3. Set your Telegram bot token as an environment variable:
   ```
   export TELEGRAM_TOKEN="your_telegram_bot_token"
   ```

### Running the Bot

Start the bot using the shell script:
```
./start_bot.sh
```

Or run the Python file directly:
```
python language_mirror_telebot.py
```

## Bot Commands

- `/start` - Get an introduction to the bot
- `/discussion` - Start a new English learning conversation
- `/stop_discussion` - End the current conversation and provide feedback
- `/skip` - Skip providing feedback comment

## Usage Guide

1. Start the bot by sending `/start`
2. Begin a conversation with `/discussion`
3. Select your English proficiency level
4. Chat naturally in English
5. Receive gentle corrections and guidance
6. End the session with `/stop_discussion` when you're done
7. Provide feedback about your experience

## How It Works

The Language Mirror bot uses a simulated conversation system that:

1. Adapts to your stated English level
2. Recognizes common language errors
3. Provides corrections naturally in conversation
4. Suggests topics appropriate to your level
5. Maintains natural conversation flow with follow-up questions
6. Offers encouragement to keep you motivated

## Implementation Details

- Built using PyTelegramBotAPI (telebot)
- Session management for user conversation tracking
- Customized response generation based on language level
- Intelligent error detection and correction
- Feedback collection system

## Future Enhancements

- Voice message recognition for pronunciation practice
- Personalized vocabulary recommendations
- Progress tracking across sessions
- Grammar focus mode for targeted practice
- Integration with language learning APIs

## License

[MIT License](LICENSE)