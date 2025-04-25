#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Language Mirror Bot - A Telegram bot for interactive language learning.
This version is adapted to work with the telebot (PyTelegramBotAPI) library.

The bot helps users practice language skills through natural conversation,
provides corrections, and offers topic-based discussions with article recommendations.
"""

import os
import sys
import time
import random
import logging
import json
import requests
import threading
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Union, Tuple
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Try to import telebot
try:
    import telebot
    from telebot import types
except ImportError:
    logger.error("telebot (PyTelegramBotAPI) library is not installed.")
    print("ERROR: telebot (PyTelegramBotAPI) library is not installed.")
    print("Please install it using: pip install pyTelegramBotAPI")
    sys.exit(1)

# Get Telegram token from environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN environment variable is not set")
    print("ERROR: TELEGRAM_TOKEN environment variable is not set")
    print("Please set it to your Telegram bot token from BotFather")
    sys.exit(1)

# Create bot instance with better error handling
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# List of admin users (usernames and IDs)
# Format: {"username": user_id}
ADMIN_USERS = {
    # Add your admin users here, for example:
    # "admin_username": 123456789,
}

# Import OpenRouter client for AI completions
from openrouter_client import OpenRouterClient
ai_client = OpenRouterClient()

# Import session manager for user state tracking
from session_manager import SessionManager
session_manager = SessionManager(session_timeout=1800)  # 30 minutes timeout

# Import database session manager if available
try:
    from flask import Flask
    from db_session_manager import DatabaseSessionManager
    
    # Create a minimal Flask app for database context
    app = Flask(__name__)
    database_url = os.environ.get("DATABASE_URL")
    
    if database_url:
        # Fix potential postgres:// vs postgresql:// URLs
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
            
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
        }
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        
        # Initialize database session manager with app
        db_session_manager = DatabaseSessionManager(app, session_timeout=1800)
        logger.info("Database session manager initialized")
    else:
        db_session_manager = None
        logger.warning("DATABASE_URL not set. Using in-memory session manager only.")
        
except ImportError:
    logger.warning("Flask or database components not available. Using in-memory session manager only.")
    db_session_manager = None

# Define language levels and their descriptions
LANGUAGE_LEVELS = {
    "A1": "Beginner - Can understand and use basic phrases",
    "A2": "Elementary - Can communicate in simple and routine tasks",
    "B1": "Intermediate - Can deal with most situations while traveling",
    "B2": "Upper Intermediate - Can interact with native speakers with fluency",
    "C1": "Advanced - Can express ideas fluently and spontaneously",
    "C2": "Proficiency - Can understand virtually everything heard or read"
}

# System prompts for different conversation contexts
SYSTEM_PROMPTS = {
    "conversation": """You are a friendly, helpful language learning assistant called Language Mirror Bot. 
Your goal is to help the user practice and improve their {language_level} English through natural conversation.

Guidelines:
1. Keep responses conversational, friendly, and natural (avoid walls of text)
2. Use vocabulary and grammar appropriate for a {language_level} English learner
3. If the user makes language errors, provide subtle corrections by restating correctly
4. Ask open-ended questions to keep the conversation flowing
5. Be patient, supportive, and adapt to the user's needs

When responding:
- Keep messages short and engaging (2-3 sentences max)
- Be conversational, as if chatting with a friend
- Use natural language with appropriate contractions (e.g., "I'm", "don't")
- Include occasional questions to encourage further discussion
- Avoid overly formal language that would sound unnatural in conversation

Remember you're helping someone practice English at {language_level} level.""",

    "discussion": """You are a friendly and helpful language learning assistant called Language Mirror Bot. 
Your purpose is to recommend reading materials on specific topics for a {language_level} English learner.

Guidelines:
1. The user has asked for recommendations on the topic: "{topic}"
2. Provide EXACTLY THREE article or reading suggestions relevant to this topic
3. Each recommendation should be appropriate for their {language_level} English level
4. For each suggestion, provide:
   - A clear, specific title (not generic)
   - A brief description of what they'll learn (1-2 sentences)
   - Why it's suitable for their level
5. Format each recommendation clearly with numbering and spacing

Your response should be friendly but focused on providing these three specific recommendations.
After giving recommendations, briefly encourage the user to read one of these articles and tell you what they think about it.""",

    "feedback": """You are Language Mirror Bot, helping gather user feedback.
The user is providing feedback on their experience with you as a language learning assistant.
 
Respond briefly and gratefully to their feedback. If their feedback includes a comment, thank them specifically for their detailed feedback.

Keep your response very short, warm, and friendly. No more than two sentences.
Do not ask follow-up questions or try to continue the conversation."""
}

# Start a periodic thread to clean up expired sessions
def session_cleanup_thread():
    """Thread that periodically cleans up expired sessions."""
    while True:
        try:
            # Clean in-memory sessions
            session_manager.clean_expired_sessions()
            
            # Clean database sessions if available
            if db_session_manager:
                db_session_manager.clean_expired_sessions()
                
            logger.debug("Cleaned up expired sessions")
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
        
        # Sleep for 5 minutes
        time.sleep(300)

# Check if user is admin
def is_admin_user(message):
    """Check if the user is an admin based on username or user ID."""
    if not message.from_user:
        return False
    
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Check by user ID (most reliable)
    for admin_username, admin_id in ADMIN_USERS.items():
        if user_id == admin_id:
            return True
    
    # Also check by username as fallback
    if username and username in ADMIN_USERS:
        return True
    
    return False

# Check if user has reached daily limit for discussions
def check_discussion_limit(user_id):
    """Check if user has reached their daily discussion limit."""
    # Admin users have unlimited usage
    if user_id in ADMIN_USERS.values():
        return True
    
    user_session = None
    
    # Try to get user data from database first
    if db_session_manager:
        try:
            with app.app_context():
                from models import User
                user = User.query.filter_by(telegram_id=user_id).first()
                if user:
                    # Check if user has used their discussion today
                    if user.last_discussion_date == date.today():
                        # Check if they have bonus discussions available
                        if user.discussions_count > 1 and not user.feedback_bonus_used:
                            return True
                        return False
                    return True
        except Exception as e:
            logger.error(f"Error checking discussion limit from database: {e}")
    
    # Fallback to in-memory session
    user_session = session_manager.get_session(user_id)
    if not user_session:
        return True
    
    last_discussion_date = user_session.get("last_discussion_date")
    if last_discussion_date and last_discussion_date == date.today().isoformat():
        # Check if they have bonus discussions available
        if user_session.get("discussions_count", 0) > 1 and not user_session.get("feedback_bonus_used", False):
            return True
        return False
    
    return True

# Load system prompts from external files if available
def load_system_prompts():
    """Load system prompts from attached_assets directory if available."""
    try:
        # Try to load conversation prompt
        conversation_path = "attached_assets/Pasted-Language-Mirror-AI--1745468550323.txt"
        if os.path.exists(conversation_path):
            with open(conversation_path, "r", encoding="utf-8") as f:
                SYSTEM_PROMPTS["conversation"] = f.read().strip()
            logger.info("Loaded conversation prompt from file")
            
        # Try to load natural phrasing prompt
        natural_path = "attached_assets/Pasted-System-Prompt-natural-phrasing-AI--1745557433318.txt"
        if os.path.exists(natural_path):
            with open(natural_path, "r", encoding="utf-8") as f:
                natural_prompt = f.read().strip()
                # Append to conversation prompt
                SYSTEM_PROMPTS["conversation"] += "\n\n" + natural_prompt
            logger.info("Loaded natural phrasing prompt from file")
            
    except Exception as e:
        logger.error(f"Error loading system prompts from files: {e}")

# Load prompts at startup
load_system_prompts()

# Start background thread for session cleanup
cleanup_thread = threading.Thread(target=session_cleanup_thread, daemon=True)
cleanup_thread.start()

# Remove any existing webhook to avoid conflicts
bot.remove_webhook()
time.sleep(0.5)

# Message handlers
@bot.message_handler(commands=['start'])
def handle_start(message):
    """Handle the /start command."""
    user = message.from_user
    user_id = user.id
    username = user.username
    first_name = user.first_name
    last_name = user.last_name
    
    logger.info(f"User {user_id} ({username}) started the bot")
    
    # Create a new session for the user
    initial_data = {
        "username": username,
        "first_name": first_name,
        "last_name": last_name
    }
    
    # Try to create session in database first
    if db_session_manager:
        db_session_manager.create_session(user_id, initial_data)
    else:
        # Fallback to in-memory session
        session_manager.create_session(user_id, initial_data)
    
    # Send welcome message with language level selection
    welcome_text = (
        f"👋 Hello, {first_name or username or 'there'}! I'm Language Mirror Bot.\n\n"
        "I'll help you practice and improve your English through natural conversation. "
        "I can chat with you, provide gentle corrections, and suggest topics.\n\n"
        "To get started, please select your English level:"
    )
    
    # Create keyboard with language level buttons
    markup = types.InlineKeyboardMarkup(row_width=2)
    level_buttons = []
    
    for level, description in LANGUAGE_LEVELS.items():
        button = types.InlineKeyboardButton(
            text=f"{level} - {description.split(' - ')[1][:20]}...",
            callback_data=f"level_{level}"
        )
        level_buttons.append(button)
    
    # Add buttons to markup in pairs
    for i in range(0, len(level_buttons), 2):
        if i + 1 < len(level_buttons):
            markup.add(level_buttons[i], level_buttons[i + 1])
        else:
            markup.add(level_buttons[i])
    
    bot.send_message(user_id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('level_'))
def handle_language_level(call):
    """Handle the user's language level selection."""
    user_id = call.from_user.id
    selected_level = call.data.split('_')[1]  # Extract level from callback data
    
    # Update user language level in session
    if db_session_manager:
        db_session_manager.update_session(user_id, {"language_level": selected_level})
    else:
        session_manager.update_session(user_id, {"language_level": selected_level})
    
    logger.info(f"User {user_id} selected language level: {selected_level}")
    
    # Edit message to remove keyboard
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"✅ Your language level is set to {selected_level} - {LANGUAGE_LEVELS[selected_level].split(' - ')[1]}.\n\n"
             f"Now you can start chatting with me! Just send a message or use one of these commands:\n\n"
             f"/chat - Start a free conversation\n"
             f"/discussion - Get reading recommendations on a topic\n"
             f"/level - Change your language level\n"
             f"/help - Show available commands"
    )
    
    # Send follow-up message to start conversation
    bot.send_message(
        user_id,
        "Let's start our conversation! Tell me about yourself or what you're interested in learning."
    )

@bot.message_handler(commands=['level'])
def change_language_level(message):
    """Handle the /level command to change language level."""
    user_id = message.from_user.id
    
    # Send language level selection again
    level_text = "Please select your English level:"
    
    # Create keyboard with language level buttons
    markup = types.InlineKeyboardMarkup(row_width=2)
    level_buttons = []
    
    for level, description in LANGUAGE_LEVELS.items():
        button = types.InlineKeyboardButton(
            text=f"{level} - {description.split(' - ')[1][:20]}...",
            callback_data=f"level_{level}"
        )
        level_buttons.append(button)
    
    # Add buttons to markup in pairs
    for i in range(0, len(level_buttons), 2):
        if i + 1 < len(level_buttons):
            markup.add(level_buttons[i], level_buttons[i + 1])
        else:
            markup.add(level_buttons[i])
    
    bot.send_message(user_id, level_text, reply_markup=markup)

@bot.message_handler(commands=['chat'])
def start_chat(message):
    """Handle the /chat command to start a conversation."""
    user_id = message.from_user.id
    
    # Get or create user session
    session = None
    if db_session_manager:
        session = db_session_manager.get_session(user_id)
        if not session:
            db_session_manager.create_session(user_id, {
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name
            })
            session = db_session_manager.get_session(user_id)
    else:
        session = session_manager.get_session(user_id)
        if not session:
            session_manager.create_session(user_id, {
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name
            })
            session = session_manager.get_session(user_id)
    
    # Check if language level is set
    language_level = session.get("language_level") if session else None
    if not language_level:
        return change_language_level(message)
    
    # Clear any existing messages in session
    if db_session_manager:
        db_session_manager.update_session(user_id, {"messages": []})
    else:
        session_manager.update_session(user_id, {"messages": []})
    
    # Send confirmation message
    bot.send_message(
        user_id,
        "Let's chat! Tell me about yourself or what you're interested in learning."
    )

@bot.message_handler(commands=['discussion'])
def start_discussion(message):
    """Handle the /discussion command to start a topic-based discussion."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Check if user has reached daily limit
    if not check_discussion_limit(user_id):
        bot.send_message(
            chat_id,
            "You've reached your daily limit for discussions. Each user can request one topic per day.\n\n"
            "💡 Tip: Give feedback after conversations to earn bonus discussions!"
        )
        return
    
    # Get user session
    session = None
    if db_session_manager:
        session = db_session_manager.get_session(user_id)
    else:
        session = session_manager.get_session(user_id)
    
    # Check if language level is set
    language_level = session.get("language_level") if session else None
    if not language_level:
        return change_language_level(message)
    
    # Update user's discussion usage
    if db_session_manager:
        try:
            with app.app_context():
                from models import User
                user = User.query.filter_by(telegram_id=user_id).first()
                if user:
                    user.last_discussion_date = date.today()
                    user.discussions_count += 1
                    from models import db
                    db.session.commit()
        except Exception as e:
            logger.error(f"Error updating discussion usage in database: {e}")
    
    # Also update in session
    if session:
        session_data = {
            "last_discussion_date": date.today().isoformat(),
            "discussions_count": session.get("discussions_count", 0) + 1
        }
        
        if db_session_manager:
            db_session_manager.update_session(user_id, session_data)
        else:
            session_manager.update_session(user_id, session_data)
    
    # Ask user for a topic
    bot.send_message(
        chat_id,
        "I'll help you find articles to read and practice your English.\n\n"
        "What topic are you interested in learning about?\n"
        "(For example: technology, history, cooking, science, etc.)"
    )
    
    # Set user's next step
    next_step = {
        "waiting_for": "discussion_topic",
        "messages": []
    }
    
    if db_session_manager:
        db_session_manager.update_session(user_id, next_step)
    else:
        session_manager.update_session(user_id, next_step)

@bot.message_handler(commands=['help'])
def show_help(message):
    """Handle the /help command to show available commands."""
    help_text = (
        "🤖 *Language Mirror Bot Commands*\n\n"
        "*/start* - Restart the bot\n"
        "*/chat* - Start a new conversation\n"
        "*/discussion* - Get reading recommendations on a topic\n"
        "*/level* - Change your language level\n"
        "*/stop* - End current conversation and give feedback\n"
        "*/help* - Show this help message\n\n"
        
        "📝 *How to use the bot*\n"
        "1. Set your English level\n"
        "2. Start chatting or request a topic discussion\n"
        "3. Practice your English naturally\n"
        "4. Get gentle corrections as you chat\n"
        "5. When finished, use /stop and give feedback\n\n"
        
        "💡 *Daily Limits*\n"
        "Each user can request one topic discussion per day. Give feedback after "
        "conversations to earn bonus discussions!"
    )
    
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['stop'])
def stop_discussion(message):
    """Handle the /stop command to end the current discussion."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Get session
    session = None
    if db_session_manager:
        session = db_session_manager.get_session(user_id)
    else:
        session = session_manager.get_session(user_id)
    
    if not session:
        bot.send_message(chat_id, "There's no active conversation to end.")
        return
    
    # Create feedback buttons
    markup = types.InlineKeyboardMarkup(row_width=3)
    helpful_btn = types.InlineKeyboardButton("👍 Helpful", callback_data="feedback_helpful")
    okay_btn = types.InlineKeyboardButton("🤔 Okay", callback_data="feedback_okay")
    not_helpful_btn = types.InlineKeyboardButton("👎 Not Helpful", callback_data="feedback_not_helpful")
    markup.add(helpful_btn, okay_btn, not_helpful_btn)
    
    # Send feedback request
    bot.send_message(
        chat_id,
        "Thank you for chatting with me today! How was your experience?",
        reply_markup=markup
    )
    
    # Update session
    next_step = {"waiting_for": "feedback"}
    if db_session_manager:
        db_session_manager.update_session(user_id, next_step)
    else:
        session_manager.update_session(user_id, next_step)

@bot.callback_query_handler(func=lambda call: call.data.startswith('feedback_'))
def handle_feedback(call):
    """Handle feedback button clicks."""
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    feedback_type = call.data.split('_')[1]
    
    # Map feedback type to human-readable form
    feedback_display = {
        "helpful": "👍 Helpful",
        "okay": "🤔 Okay",
        "not_helpful": "👎 Not Helpful"
    }.get(feedback_type, feedback_type)
    
    # Store feedback in session
    if db_session_manager:
        db_session_manager.update_session(user_id, {
            "feedback": feedback_type,
            "waiting_for": "feedback_comment"
        })
    else:
        session_manager.update_session(user_id, {
            "feedback": feedback_type,
            "waiting_for": "feedback_comment"
        })
    
    # Edit message to remove keyboard
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=f"Thank you for your feedback: {feedback_display}"
    )
    
    # Ask for optional comment
    bot.send_message(
        chat_id,
        "Would you like to add any comments about your experience? "
        "This helps me improve. (Type your comment or just send /skip)\n\n"
        "💡 Hint: Providing detailed feedback (more than 3 words) earns you a bonus discussion!"
    )

@bot.message_handler(commands=['skip'])
def skip_feedback_comment(message):
    """Handle skipping the feedback comment."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Get session
    session = None
    if db_session_manager:
        session = db_session_manager.get_session(user_id)
    else:
        session = session_manager.get_session(user_id)
    
    if not session or session.get("waiting_for") != "feedback_comment":
        return
    
    # Store feedback without comment
    feedback_type = session.get("feedback")
    store_feedback(user_id, feedback_type)
    
    # Thank the user
    bot.send_message(
        chat_id,
        "Thank you for your feedback! You can start a new conversation anytime."
    )
    
    # End session
    if db_session_manager:
        db_session_manager.end_session(user_id)
    else:
        session_manager.end_session(user_id)

@bot.message_handler(commands=['admin_feedback'])
def admin_feedback(message):
    """Admin command to view feedback data."""
    if not is_admin_user(message):
        bot.send_message(message.chat.id, "This command is only available to administrators.")
        return
    
    chat_id = message.chat.id
    bot.send_message(chat_id, "Generating feedback report... Please wait.")
    
    try:
        # Try to generate Excel report
        from excel_report import create_simple_feedback_excel
        
        with app.app_context():
            from models import Feedback, User
            
            # Query all feedback with user information
            feedback_records = []
            feedbacks = Feedback.query.order_by(Feedback.timestamp.desc()).all()
            
            for feedback in feedbacks:
                user = User.query.get(feedback.user_id)
                if user:
                    feedback_records.append((
                        feedback,
                        user.telegram_id,
                        user.username,
                        user.first_name,
                        user.last_name
                    ))
            
            # Generate Excel file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"feedback_report_{timestamp}.xlsx"
            filepath = create_simple_feedback_excel(feedback_records, filename)
            
            # Send Excel file
            with open(filepath, 'rb') as file:
                bot.send_document(
                    chat_id,
                    file,
                    caption=f"Feedback report with {len(feedback_records)} entries."
                )
    
    except Exception as e:
        logger.error(f"Error generating feedback report: {e}")
        bot.send_message(
            chat_id,
            f"Error generating feedback report: {str(e)}\n\nPlease check server logs for details."
        )

# Handler for discussion topics
@bot.message_handler(func=lambda message: get_waiting_for(message.from_user.id) == "discussion_topic")
def handle_discussion_topic(message):
    """Handle user's topic for discussion."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    topic = message.text.strip()
    
    if not topic:
        bot.send_message(chat_id, "Please provide a valid topic.")
        return
    
    # Get user session
    session = None
    language_level = "B1"  # Default level
    
    if db_session_manager:
        session = db_session_manager.get_session(user_id)
        if session:
            language_level = session.get("language_level", "B1")
    else:
        session = session_manager.get_session(user_id)
        if session:
            language_level = session.get("language_level", "B1")
    
    # Send typing indicator
    bot.send_chat_action(chat_id, "typing")
    
    # Format prompt with topic and language level
    system_prompt = SYSTEM_PROMPTS["discussion"].format(
        topic=topic,
        language_level=language_level
    )
    
    try:
        # Generate recommendations using OpenRouter
        response = ai_client.get_completion(
            system_prompt,
            [{"role": "user", "content": f"Please recommend articles about {topic} for my {language_level} level."}]
        )
        
        # Send recommendations
        bot.send_message(chat_id, response)
        
        # Ask for feedback
        markup = types.InlineKeyboardMarkup(row_width=3)
        helpful_btn = types.InlineKeyboardButton("👍 Helpful", callback_data="feedback_helpful")
        okay_btn = types.InlineKeyboardButton("🤔 Okay", callback_data="feedback_okay")
        not_helpful_btn = types.InlineKeyboardButton("👎 Not Helpful", callback_data="feedback_not_helpful")
        markup.add(helpful_btn, okay_btn, not_helpful_btn)
        
        bot.send_message(
            chat_id,
            "How were these recommendations? Your feedback helps me improve!",
            reply_markup=markup
        )
        
        # Update session
        next_step = {"waiting_for": "feedback"}
        if db_session_manager:
            db_session_manager.update_session(user_id, next_step)
        else:
            session_manager.update_session(user_id, next_step)
            
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        bot.send_message(
            chat_id,
            "I'm sorry, I couldn't generate recommendations at the moment. Please try again later."
        )

# Handler for feedback comments
@bot.message_handler(func=lambda message: get_waiting_for(message.from_user.id) == "feedback_comment")
def handle_feedback_comment(message):
    """Handle user's feedback comment."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    comment = message.text.strip()
    
    # Get session
    session = None
    if db_session_manager:
        session = db_session_manager.get_session(user_id)
    else:
        session = session_manager.get_session(user_id)
    
    if not session:
        return
    
    feedback_type = session.get("feedback")
    
    # Check if comment is substantial (more than 3 words)
    words = comment.split()
    is_substantial = len(words) > 3
    
    # Store feedback with comment
    store_feedback(user_id, feedback_type, comment)
    
    # Award bonus discussion if comment is substantial
    if is_substantial:
        # Update in database if available
        if db_session_manager:
            try:
                with app.app_context():
                    from models import User, db
                    user = User.query.filter_by(telegram_id=user_id).first()
                    if user and not user.feedback_bonus_used:
                        user.feedback_bonus_used = True
                        db.session.commit()
                        
                        # Notify user about bonus
                        bot.send_message(
                            chat_id,
                            "🎁 Thank you for your detailed feedback! You've earned a bonus discussion request."
                        )
            except Exception as e:
                logger.error(f"Error updating bonus status in database: {e}")
        
        # Also update in session
        if session:
            session_data = {"feedback_bonus_used": True}
            if db_session_manager:
                db_session_manager.update_session(user_id, session_data)
            else:
                session_manager.update_session(user_id, session_data)
    
    # Thank the user
    if not is_substantial:
        bot.send_message(
            chat_id,
            "Thank you for your feedback! You can start a new conversation anytime with /chat."
        )
    
    # Generate AI response to feedback
    try:
        system_prompt = SYSTEM_PROMPTS["feedback"]
        ai_response = ai_client.get_completion(
            system_prompt,
            [{"role": "user", "content": f"Rating: {feedback_type}, Comment: {comment}"}]
        )
        
        bot.send_message(chat_id, ai_response)
    except Exception as e:
        logger.error(f"Error generating feedback response: {e}")
    
    # End session
    if db_session_manager:
        db_session_manager.end_session(user_id)
    else:
        session_manager.end_session(user_id)

# General message handler
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Handle regular user messages."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_text = message.text
    
    # Get or create user session
    session = None
    if db_session_manager:
        session = db_session_manager.get_session(user_id)
        if not session:
            db_session_manager.create_session(user_id, {
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name
            })
            session = db_session_manager.get_session(user_id)
    else:
        session = session_manager.get_session(user_id)
        if not session:
            session_manager.create_session(user_id, {
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name
            })
            session = session_manager.get_session(user_id)
    
    # Check if waiting for specific input
    waiting_for = session.get("waiting_for") if session else None
    if waiting_for:
        # The message should be handled by one of the specific handlers
        return
    
    # Check if language level is set
    language_level = session.get("language_level") if session else None
    if not language_level:
        return change_language_level(message)
    
    # Add user message to session
    if db_session_manager:
        db_session_manager.add_message_to_session(user_id, "user", user_text)
    else:
        session_manager.add_message_to_session(user_id, "user", user_text)
    
    # Send typing indicator
    bot.send_chat_action(chat_id, "typing")
    
    # Get conversation history
    messages = []
    if db_session_manager:
        messages = db_session_manager.get_messages(user_id)
    else:
        messages = session_manager.get_messages(user_id)
    
    # Format system prompt with language level
    system_prompt = SYSTEM_PROMPTS["conversation"].format(language_level=language_level)
    
    try:
        # Generate response using OpenRouter
        response = ai_client.get_completion(system_prompt, messages)
        
        # Add assistant message to session
        if db_session_manager:
            db_session_manager.add_message_to_session(user_id, "assistant", response)
        else:
            session_manager.add_message_to_session(user_id, "assistant", response)
        
        # Send response
        bot.send_message(chat_id, response)
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        bot.send_message(
            chat_id,
            "I'm sorry, I couldn't generate a response at the moment. Please try again later."
        )

# Helper function to store feedback
def store_feedback(user_id, feedback_type, comment=None):
    """Store user feedback in database or API."""
    try:
        # Get user data
        user_data = None
        if db_session_manager:
            user_data = db_session_manager.get_session(user_id)
        else:
            user_data = session_manager.get_session(user_id)
        
        username = user_data.get("username") if user_data else None
        
        # Store in database if available
        if db_session_manager:
            try:
                with app.app_context():
                    from models import User, Feedback, db
                    
                    # Find user
                    user = User.query.filter_by(telegram_id=user_id).first()
                    if not user:
                        # Create user if not exists
                        user = User(
                            telegram_id=user_id,
                            username=username
                        )
                        db.session.add(user)
                        db.session.commit()
                    
                    # Create feedback
                    feedback = Feedback(
                        user_id=user.id,
                        rating=feedback_type,
                        comment=comment
                    )
                    
                    db.session.add(feedback)
                    db.session.commit()
                    logger.info(f"Stored feedback in database for user {user_id}")
                    return
            except Exception as e:
                logger.error(f"Error storing feedback in database: {e}")
        
        # Fallback to API if database not available
        try:
            # Prepare feedback data
            feedback_data = {
                "user_id": user_id,
                "username": username,
                "rating": feedback_type,
                "comment": comment or ""
            }
            
            # Send to API
            response = requests.post(
                "http://localhost:5000/api/feedback",
                json=feedback_data,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Stored feedback via API for user {user_id}")
            else:
                logger.warning(f"API returned status {response.status_code} when storing feedback")
        except Exception as e:
            logger.error(f"Error storing feedback via API: {e}")
            
    except Exception as e:
        logger.error(f"Error in store_feedback: {e}")

# Helper function to get waiting_for state
def get_waiting_for(user_id):
    """Get the waiting_for state from user session."""
    if db_session_manager:
        session = db_session_manager.get_session(user_id)
        return session.get("waiting_for") if session else None
    else:
        session = session_manager.get_session(user_id)
        return session.get("waiting_for") if session else None

# Main function to run the bot
def main():
    """Run the bot with proper error handling."""
    logger.info("Starting Language Mirror Bot")
    
    try:
        # Start polling (with retries on connection errors)
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        logger.error(f"Bot polling error: {e}")
        time.sleep(10)  # Wait before potential restart

if __name__ == "__main__":
    main()