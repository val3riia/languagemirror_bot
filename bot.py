import os
import logging
import requests
import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    filters, 
    ContextTypes
)
from openrouter_client import OpenRouterClient
from session_manager import SessionManager

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get Telegram token from environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable is not set")

# Create OpenRouter client
openrouter_client = OpenRouterClient()

# Create session manager
session_manager = SessionManager()

# Admin user IDs (for /admin_feedback command)
ADMIN_IDS = [int(id) for id in os.environ.get("ADMIN_IDS", "").split(",") if id]

# Custom language level definitions
LANGUAGE_LEVELS = {
    "A1": "Beginner - You're just starting with English",
    "A2": "Elementary - You can use simple phrases and sentences",
    "B1": "Intermediate - You can discuss familiar topics",
    "B2": "Upper Intermediate - You can interact with fluency",
    "C1": "Advanced - You can express yourself fluently and spontaneously",
    "C2": "Proficiency - You can understand virtually everything heard or read"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_text(
        f"Hello {user.first_name}! 👋\n\n"
        "I'm Language Mirror, an AI assistant that helps you learn English through topics "
        "that genuinely interest you – your thoughts, experiences, and feelings.\n\n"
        "I'm not a traditional language teacher. I help you express yourself in English "
        "with confidence and emotional accuracy through natural conversation.\n\n"
        "Use /discussion to start a conversation with me!"
    )

async def ask_language_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask the user about their English proficiency level."""
    keyboard = []
    for level, description in LANGUAGE_LEVELS.items():
        keyboard.append([InlineKeyboardButton(f"{level} - {description}", callback_data=f"level_{level}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Before we begin, I'd like to know your English proficiency level "
        "so I can adapt to your needs. Please select your level:",
        reply_markup=reply_markup
    )

async def handle_language_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the user's language level selection."""
    query = update.callback_query
    await query.answer()
    
    # Extract level from callback data
    level = query.data.split('_')[1]
    user_id = update.effective_user.id
    
    # Initialize user session
    session_manager.create_session(user_id, {"language_level": level})
    
    await query.edit_message_text(
        f"Great! I'll adapt to your {level} level. Let's start our conversation!\n\n"
        "What would you like to talk about today? Feel free to share any thoughts, "
        "questions, or topics that interest you."
    )

async def start_discussion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start a discussion with the user."""
    user_id = update.effective_user.id
    
    # Check if user already has an active session
    if session_manager.get_session(user_id):
        await update.message.reply_text(
            "You're already in a discussion with me. You can continue talking or "
            "use /stop_discussion to end our current conversation."
        )
        return
    
    # Ask for language level if not already in a session
    await ask_language_level(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user messages and continue the discussion."""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Check if user has an active session
    user_session = session_manager.get_session(user_id)
    if not user_session:
        await update.message.reply_text(
            "Please use /discussion to start a conversation with me first."
        )
        return
    
    # Update session with new message
    session_manager.add_message_to_session(user_id, "user", user_message)
    
    # Get language level from session
    language_level = user_session.get("language_level", "B1")
    
    # Prepare context for AI
    messages = session_manager.get_messages(user_id)
    
    # Add system message for AI context
    system_message = (
        f"You are Language Mirror, an AI language learning assistant focused on helping users express "
        f"their thoughts in English naturally. You're talking with a {language_level} level English speaker. "
        f"Your goal is to help them become fluent through emotionally alive, idiomatic conversation.\n\n"
        f"Guidelines:\n"
        f"1. Use natural, idiomatic language appropriate for {language_level} level\n"
        f"2. Introduce vocabulary and expressions gradually in context, not as lists\n"
        f"3. Help with grammar through function, not abstract rules\n"
        f"4. If the user uses words in a different language, suggest English equivalents\n"
        f"5. Maintain dialogue flow, ask questions, and respond to emotions\n"
        f"6. Don't overwhelm with vocabulary or corrections\n"
        f"7. Teach through conversation, not lectures"
    )
    
    try:
        # Send typing indication
        await context.bot.send_chat_action(chat_id=user_id, action="typing")
        
        # Get response from AI
        ai_response = openrouter_client.get_completion(system_message, messages)
        
        # Save AI response to session
        session_manager.add_message_to_session(user_id, "assistant", ai_response)
        
        # Send response to user
        await update.message.reply_text(ai_response)
    except Exception as e:
        logger.error(f"Error getting AI response: {e}")
        await update.message.reply_text(
            "I'm sorry, I encountered an error processing your message. "
            "Please try again in a moment."
        )

async def stop_discussion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """End the current discussion and ask for feedback."""
    user_id = update.effective_user.id
    
    # Check if user has an active session
    if not session_manager.get_session(user_id):
        await update.message.reply_text(
            "You don't have an active discussion session. "
            "Use /discussion to start one."
        )
        return
    
    # Create feedback keyboard
    keyboard = [
        [
            InlineKeyboardButton("👍 Helpful", callback_data="feedback_helpful"),
            InlineKeyboardButton("🤔 Okay", callback_data="feedback_okay"),
            InlineKeyboardButton("👎 Not helpful", callback_data="feedback_not_helpful")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Thank you for our conversation! I hope it was helpful for your English learning journey.\n\n"
        "How would you rate our discussion?",
        reply_markup=reply_markup
    )

async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user feedback."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    feedback_type = query.data.split('_')[1]
    
    # Map feedback types to ratings
    rating_map = {
        "helpful": "👍 Helpful",
        "okay": "🤔 Okay",
        "not_helpful": "👎 Not helpful"
    }
    
    # Save feedback
    feedback = {
        "rating": rating_map.get(feedback_type, "Unknown"),
        "user_id": user_id,
        "timestamp": json.dumps({"$date": {"$numberLong": str(int(query.message.date.timestamp() * 1000))}})
    }
    
    # Send feedback to the Flask app API
    try:
        requests.post("http://localhost:5000/api/feedback", json=feedback)
    except Exception as e:
        logger.error(f"Failed to save feedback: {e}")
    
    # Ask for additional comment
    await query.edit_message_text(
        f"Thank you for your feedback: {rating_map.get(feedback_type)}!\n\n"
        "Would you like to add any comments about our conversation? "
        "Please reply to this message with your comments or type /skip to finish."
    )
    
    # Store feedback type in context for the next handler
    context.user_data["feedback_type"] = feedback_type
    
    # Clear session
    session_manager.end_session(user_id)

async def handle_feedback_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle feedback comments."""
    user_id = update.effective_user.id
    comment = update.message.text
    
    if comment.lower() == "/skip":
        await update.message.reply_text(
            "Thanks again for your feedback! Use /discussion anytime you want to practice English."
        )
        return
    
    # Get feedback type from context
    feedback_type = context.user_data.get("feedback_type", "unknown")
    rating_map = {
        "helpful": "👍 Helpful",
        "okay": "🤔 Okay",
        "not_helpful": "👎 Not helpful",
        "unknown": "Rating not provided"
    }
    
    # Update feedback with comment
    feedback = {
        "rating": rating_map.get(feedback_type, "Unknown"),
        "comment": comment,
        "user_id": user_id,
        "timestamp": json.dumps({"$date": {"$numberLong": str(int(update.message.date.timestamp() * 1000))}})
    }
    
    # Send feedback to the Flask app API
    try:
        requests.post("http://localhost:5000/api/feedback", json=feedback)
    except Exception as e:
        logger.error(f"Failed to save feedback comment: {e}")
    
    await update.message.reply_text(
        "Thank you for your additional comments! Your feedback helps me improve.\n\n"
        "Feel free to use /discussion anytime you want to practice English again."
    )
    
    # Clear feedback data from context
    if "feedback_type" in context.user_data:
        del context.user_data["feedback_type"]

async def admin_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to view feedback data."""
    user_id = update.effective_user.id
    
    # Check if user is an admin
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Sorry, this command is only available to administrators.")
        return
    
    # Get feedback data from the Flask app API
    try:
        response = requests.get("http://localhost:5000/api/feedback")
        feedback_data = response.json()
        
        if not feedback_data:
            await update.message.reply_text("No feedback data available.")
            return
        
        # Format feedback data for display
        feedback_text = "📊 User Feedback Report:\n\n"
        for idx, feedback in enumerate(feedback_data, 1):
            rating = feedback.get("rating", "Not provided")
            comment = feedback.get("comment", "No comment")
            user_id = feedback.get("user_id", "Unknown")
            timestamp = feedback.get("timestamp", "Unknown time")
            
            feedback_text += f"{idx}. User: {user_id}\n"
            feedback_text += f"   Rating: {rating}\n"
            feedback_text += f"   Comment: {comment}\n"
            feedback_text += f"   Time: {timestamp}\n\n"
            
            # Telegram messages have a 4096 character limit
            if len(feedback_text) > 3500:
                await update.message.reply_text(feedback_text)
                feedback_text = "Continued...\n\n"
        
        if feedback_text:
            await update.message.reply_text(feedback_text)
            
    except Exception as e:
        logger.error(f"Error retrieving feedback: {e}")
        await update.message.reply_text(
            "Error retrieving feedback data. Please make sure the web server is running."
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the telegram bot."""
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "I encountered an error processing your request. Please try again later."
            )
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

def start_bot():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("discussion", start_discussion))
    application.add_handler(CommandHandler("stop_discussion", stop_discussion))
    application.add_handler(CommandHandler("admin_feedback", admin_feedback))
    
    # Add callback query handlers
    application.add_handler(CallbackQueryHandler(handle_language_level, pattern="^level_"))
    application.add_handler(CallbackQueryHandler(handle_feedback, pattern="^feedback_"))
    
    # Add message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the Bot asynchronously
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    return application

if __name__ == "__main__":
    start_bot()
