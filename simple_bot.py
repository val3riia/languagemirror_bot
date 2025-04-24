#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Language Mirror Bot - A Telegram bot for interactive language learning.
"""

import os
import logging
from typing import Dict, List, Any, Optional
import json
import time
import asyncio
import random

# Import telegram libraries
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

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

# Define language levels with descriptions
LANGUAGE_LEVELS = {
    "A1": "Beginner - You're just starting with English",
    "A2": "Elementary - You can use simple phrases and sentences",
    "B1": "Intermediate - You can discuss familiar topics",
    "B2": "Upper Intermediate - You can interact with fluency",
    "C1": "Advanced - You can express yourself fluently and spontaneously",
    "C2": "Proficiency - You can understand virtually everything heard or read"
}

# A simple in-memory session storage 
user_sessions = {}

# Some example conversation topics for different levels
CONVERSATION_TOPICS = {
    "A1": [
        "What is your name?",
        "Where are you from?",
        "What do you like to eat?",
        "What color do you like?",
        "How old are you?"
    ],
    "A2": [
        "What is your favorite hobby?",
        "Tell me about your family.",
        "What's the weather like today?",
        "What did you do yesterday?",
        "What kind of movies do you like?"
    ],
    "B1": [
        "What are your plans for the weekend?",
        "Tell me about an interesting experience you had.",
        "What kind of music do you enjoy listening to?",
        "If you could travel anywhere, where would you go?",
        "What do you think about social media?"
    ],
    "B2": [
        "What are some environmental issues that concern you?",
        "How has technology changed the way we live?",
        "What are the advantages and disadvantages of working from home?",
        "Do you think artificial intelligence will change our future?",
        "What cultural differences have you noticed between countries?"
    ],
    "C1": [
        "How do you think education systems could be improved?",
        "What ethical considerations should be made when developing new technologies?",
        "How does media influence public opinion?",
        "What societal changes do you think will happen in the next decade?",
        "What are your thoughts on the work-life balance in modern society?"
    ],
    "C2": [
        "What philosophical questions do you find most intriguing?",
        "How do economic policies influence social inequality?",
        "In what ways might quantum computing revolutionize our approach to complex problems?",
        "How does language shape our perception of reality?",
        "What insights can literature offer us about human nature?"
    ]
}

# Responses for simulating a language learning conversation
SAMPLE_RESPONSES = {
    "greeting": [
        "Hello! How are you today?",
        "Hi there! What would you like to talk about?",
        "Welcome! What's on your mind?"
    ],
    "follow_up": [
        "That's interesting! Can you tell me more?",
        "I see. How does that make you feel?",
        "Interesting perspective. Why do you think that is?"
    ],
    "language_correction": [
        "I noticed you said '{}'. A more natural way to express that would be '{}'.",
        "That's good! Just a small suggestion: instead of '{}', you could say '{}'.",
        "You expressed that well! For even more fluency, you could try saying '{}' instead of '{}'."
    ],
    "encouragement": [
        "You're expressing yourself very well!",
        "Your English is improving nicely!",
        "I'm impressed with how you structured that thought!"
    ]
}

# Simple patterns that need correction (for demo purposes)
CORRECTION_PATTERNS = {
    "i am agree": "I agree",
    "i am interesting in": "I am interested in",
    "i went in": "I went to",
    "persons": "people",
    "informations": "information",
    "advices": "advice",
    "i am working since": "I have been working since",
    "yesterday i go": "yesterday I went",
    "i didn't went": "I didn't go",
    "i am here since": "I have been here since"
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
    user_sessions[user_id] = {
        "language_level": level,
        "messages": [],
        "last_active": time.time()
    }
    
    # Suggest a topic based on their level
    topics = CONVERSATION_TOPICS.get(level, CONVERSATION_TOPICS["B1"])
    suggested_topic = random.choice(topics)
    
    await query.edit_message_text(
        f"Great! I'll adapt to your {level} level. Let's start our conversation!\n\n"
        f"Here's a suggestion: {suggested_topic}\n\n"
        "But feel free to talk about anything that interests you!"
    )

async def start_discussion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start a discussion with the user."""
    user_id = update.effective_user.id
    
    # Check if user already has an active session
    if user_id in user_sessions:
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
    if user_id not in user_sessions:
        await update.message.reply_text(
            "Please use /discussion to start a conversation with me first."
        )
        return
    
    # Update session with new message
    user_sessions[user_id]["messages"].append({"role": "user", "content": user_message})
    user_sessions[user_id]["last_active"] = time.time()
    
    # Get language level from session
    language_level = user_sessions[user_id].get("language_level", "B1")
    
    # Simulate response processing time
    await context.bot.send_chat_action(chat_id=user_id, action="typing")
    await asyncio.sleep(1.5)  # Simulates thinking time
    
    # Generate a response based on the user's message
    response = generate_learning_response(user_message, language_level)
    
    # Save response to session
    user_sessions[user_id]["messages"].append({"role": "assistant", "content": response})
    
    # Send response to user
    await update.message.reply_text(response)

def generate_learning_response(user_message: str, language_level: str) -> str:
    """
    Generate a language learning response based on the user's message and level.
    
    This is a simplified simulation of what would normally be handled by an AI model.
    """
    # Check for correction opportunities
    correction = None
    for pattern, correction_text in CORRECTION_PATTERNS.items():
        if pattern.lower() in user_message.lower():
            correction = (pattern, correction_text)
            break
    
    # Construct response
    response_parts = []
    
    # Add a follow-up question or comment
    response_parts.append(random.choice(SAMPLE_RESPONSES["follow_up"]))
    
    # Add a language correction if applicable
    if correction and language_level not in ["C1", "C2"]:  # Less corrections for advanced users
        response_parts.append(
            random.choice(SAMPLE_RESPONSES["language_correction"]).format(
                correction[0], correction[1]
            )
        )
    
    # Add encouragement
    if random.random() < 0.3:  # 30% chance to add encouragement
        response_parts.append(random.choice(SAMPLE_RESPONSES["encouragement"]))
    
    # Add topic suggestion for A1-B1 levels
    if language_level in ["A1", "A2", "B1"] and random.random() < 0.4:
        topics = CONVERSATION_TOPICS.get(language_level, [])
        if topics:
            response_parts.append(f"By the way, {random.choice(topics)}")
    
    return " ".join(response_parts)

async def stop_discussion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """End the current discussion and ask for feedback."""
    user_id = update.effective_user.id
    
    # Check if user has an active session
    if user_id not in user_sessions:
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
    
    # Store feedback (in a real app, this would be saved to a database)
    logger.info(f"User {user_id} gave feedback: {rating_map.get(feedback_type)}")
    
    # Ask for additional comment
    await query.edit_message_text(
        f"Thank you for your feedback: {rating_map.get(feedback_type)}!\n\n"
        "Would you like to add any comments about our conversation? "
        "Please reply to this message with your comments or type /skip to finish."
    )
    
    # Store feedback type in context for the next handler
    context.user_data["feedback_type"] = feedback_type
    
    # Clear session
    if user_id in user_sessions:
        del user_sessions[user_id]

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
    
    # Store feedback with comment (in a real app, this would be saved to a database)
    logger.info(f"User {user_id} feedback {rating_map.get(feedback_type)} with comment: {comment}")
    
    await update.message.reply_text(
        "Thank you for your additional comments! Your feedback helps me improve.\n\n"
        "Feel free to use /discussion anytime you want to practice English again."
    )
    
    # Clear feedback data from context
    if "feedback_type" in context.user_data:
        del context.user_data["feedback_type"]

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
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("discussion", start_discussion))
    application.add_handler(CommandHandler("stop_discussion", stop_discussion))
    
    # Add callback query handlers
    application.add_handler(CallbackQueryHandler(handle_language_level, pattern="^level_"))
    application.add_handler(CallbackQueryHandler(handle_feedback, pattern="^feedback_"))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    return application

if __name__ == "__main__":
    logger.info("Starting Language Mirror bot...")
    start_bot()