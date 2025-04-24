#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Language Mirror Bot - A Telegram bot for interactive language learning.
This version uses python-telegram-bot library and implements basic language learning features.
"""

import os
import logging
import time
import random
import json
import asyncio
from typing import Dict, Any

# Проверяем, установлена ли библиотека python-telegram-bot
try:
    from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
    from telegram.ext import (
        Application, 
        CommandHandler, 
        MessageHandler, 
        CallbackQueryHandler,
        filters, 
        ContextTypes
    )
except ImportError:
    # Если библиотека не установлена, выводим сообщение и завершаем программу
    print("ERROR: python-telegram-bot library is not installed.")
    print("Please install it using: pip install python-telegram-bot")
    exit(1)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получение токена Telegram из переменных окружения
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN environment variable is not set")
    print("ERROR: TELEGRAM_TOKEN environment variable is not set")
    print("Please set it to your Telegram bot token from BotFather")
    exit(1)

# Уровни владения языком с описаниями
LANGUAGE_LEVELS = {
    "A1": "Beginner - You're just starting with English",
    "A2": "Elementary - You can use simple phrases and sentences",
    "B1": "Intermediate - You can discuss familiar topics",
    "B2": "Upper Intermediate - You can interact with fluency",
    "C1": "Advanced - You can express yourself fluently and spontaneously",
    "C2": "Proficiency - You can understand virtually everything heard or read"
}

# Простое хранилище сессий в памяти
user_sessions = {}

# Примеры тем для обсуждения разного уровня
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

# Шаблоны ответов для симуляции разговора с обучением языку
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

# Простые шаблоны для исправления (для демонстрации)
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
    """Отправляет приветственное сообщение при команде /start."""
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
    """Спрашивает у пользователя его уровень владения английским."""
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
    """Обрабатывает выбор уровня владения языком."""
    query = update.callback_query
    await query.answer()
    
    # Извлекаем уровень из callback_data
    level = query.data.split('_')[1]
    user_id = update.effective_user.id
    
    # Инициализируем сессию пользователя
    user_sessions[user_id] = {
        "language_level": level,
        "messages": [],
        "last_active": time.time()
    }
    
    # Предлагаем тему на основе уровня
    topics = CONVERSATION_TOPICS.get(level, CONVERSATION_TOPICS["B1"])
    suggested_topic = random.choice(topics)
    
    await query.edit_message_text(
        f"Great! I'll adapt to your {level} level. Let's start our conversation!\n\n"
        f"Here's a suggestion: {suggested_topic}\n\n"
        "But feel free to talk about anything that interests you!"
    )

async def start_discussion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начинает обсуждение с пользователем."""
    user_id = update.effective_user.id
    
    # Проверяем, есть ли у пользователя активная сессия
    if user_id in user_sessions:
        await update.message.reply_text(
            "You're already in a discussion with me. You can continue talking or "
            "use /stop_discussion to end our current conversation."
        )
        return
    
    # Спрашиваем уровень владения языком, если пользователь не в сессии
    await ask_language_level(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает сообщения пользователя и продолжает обсуждение."""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Проверяем, есть ли у пользователя активная сессия
    if user_id not in user_sessions:
        await update.message.reply_text(
            "Please use /discussion to start a conversation with me first."
        )
        return
    
    # Обновляем сессию новым сообщением
    if "messages" not in user_sessions[user_id]:
        user_sessions[user_id]["messages"] = []
    user_sessions[user_id]["messages"].append({"role": "user", "content": user_message})
    user_sessions[user_id]["last_active"] = time.time()
    
    # Получаем уровень языка из сессии
    language_level = user_sessions[user_id].get("language_level", "B1")
    
    # Имитируем время обработки ответа
    await context.bot.send_chat_action(chat_id=user_id, action="typing")
    await asyncio.sleep(1.5)  # Имитация времени обдумывания
    
    # Генерируем ответ на основе сообщения пользователя
    response = generate_learning_response(user_message, language_level)
    
    # Сохраняем ответ в сессии
    user_sessions[user_id]["messages"].append({"role": "assistant", "content": response})
    
    # Отправляем ответ пользователю
    await update.message.reply_text(response)

def generate_learning_response(user_message: str, language_level: str) -> str:
    """
    Генерирует ответ для обучения языку на основе сообщения пользователя и уровня.
    
    Это упрощенная симуляция того, что обычно обрабатывается моделью ИИ.
    """
    # Проверяем возможности для исправления
    correction = None
    for pattern, correction_text in CORRECTION_PATTERNS.items():
        if pattern.lower() in user_message.lower():
            correction = (pattern, correction_text)
            break
    
    # Формируем ответ
    response_parts = []
    
    # Добавляем уточняющий вопрос или комментарий
    response_parts.append(random.choice(SAMPLE_RESPONSES["follow_up"]))
    
    # Добавляем языковую коррекцию, если применимо
    if correction and language_level not in ["C1", "C2"]:  # Меньше исправлений для продвинутых пользователей
        response_parts.append(
            random.choice(SAMPLE_RESPONSES["language_correction"]).format(
                correction[0], correction[1]
            )
        )
    
    # Добавляем подбадривание
    if random.random() < 0.3:  # 30% шанс добавить подбадривание
        response_parts.append(random.choice(SAMPLE_RESPONSES["encouragement"]))
    
    # Добавляем предложение темы для уровней A1-B1
    if language_level in ["A1", "A2", "B1"] and random.random() < 0.4:
        topics = CONVERSATION_TOPICS.get(language_level, [])
        if topics:
            response_parts.append(f"By the way, {random.choice(topics)}")
    
    return " ".join(response_parts)

async def stop_discussion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Завершает текущее обсуждение и запрашивает обратную связь."""
    user_id = update.effective_user.id
    
    # Проверяем, есть ли у пользователя активная сессия
    if user_id not in user_sessions:
        await update.message.reply_text(
            "You don't have an active discussion session. "
            "Use /discussion to start one."
        )
        return
    
    # Создаем клавиатуру для обратной связи
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
    """Обрабатывает обратную связь пользователя."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    feedback_type = query.data.split('_')[1]
    
    # Сопоставляем типы обратной связи с оценками
    rating_map = {
        "helpful": "👍 Helpful",
        "okay": "🤔 Okay",
        "not_helpful": "👎 Not helpful"
    }
    
    # Сохраняем обратную связь (в реальном приложении сохранялось бы в базу данных)
    logger.info(f"User {user_id} gave feedback: {rating_map.get(feedback_type)}")
    
    # Запрашиваем дополнительный комментарий
    await query.edit_message_text(
        f"Thank you for your feedback: {rating_map.get(feedback_type)}!\n\n"
        "Would you like to add any comments about our conversation? "
        "Please reply to this message with your comments or type /skip to finish."
    )
    
    # Сохраняем тип обратной связи в контексте для следующего обработчика
    context.user_data["feedback_type"] = feedback_type
    
    # Очищаем сессию
    if user_id in user_sessions:
        del user_sessions[user_id]

async def handle_feedback_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает комментарии к обратной связи."""
    user_id = update.effective_user.id
    comment = update.message.text
    
    if comment.lower() == "/skip":
        await update.message.reply_text(
            "Thanks again for your feedback! Use /discussion anytime you want to practice English."
        )
        return
    
    # Получаем тип обратной связи из контекста
    feedback_type = context.user_data.get("feedback_type", "unknown")
    rating_map = {
        "helpful": "👍 Helpful",
        "okay": "🤔 Okay",
        "not_helpful": "👎 Not helpful",
        "unknown": "Rating not provided"
    }
    
    # Сохраняем обратную связь с комментарием (в реальном приложении сохранялось бы в базу данных)
    logger.info(f"User {user_id} feedback {rating_map.get(feedback_type)} with comment: {comment}")
    
    await update.message.reply_text(
        "Thank you for your additional comments! Your feedback helps me improve.\n\n"
        "Feel free to use /discussion anytime you want to practice English again."
    )
    
    # Очищаем данные обратной связи из контекста
    if "feedback_type" in context.user_data:
        del context.user_data["feedback_type"]

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает ошибки в telegram боте."""
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "I encountered an error processing your request. Please try again later."
            )
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

def main():
    """Запускает бота."""
    logger.info("Starting Language Mirror bot...")
    
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("discussion", start_discussion))
    application.add_handler(CommandHandler("stop_discussion", stop_discussion))
    
    # Добавляем обработчики callback query
    application.add_handler(CallbackQueryHandler(handle_language_level, pattern="^level_"))
    application.add_handler(CallbackQueryHandler(handle_feedback, pattern="^feedback_"))
    
    # Добавляем обработчики сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота асинхронно
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    return application

if __name__ == "__main__":
    main()