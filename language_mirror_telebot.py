#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Language Mirror Bot - A Telegram bot for interactive language learning.
This version is adapted to work with the telebot (PyTelegramBotAPI) library.
"""

import os
import sys
import time
import random
import logging
import json
import requests
import threading
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Пробуем импортировать telebot
try:
    import telebot
    from telebot import types
except ImportError:
    logger.error("telebot (PyTelegramBotAPI) library is not installed.")
    print("ERROR: telebot (PyTelegramBotAPI) library is not installed.")
    print("Please install it using: pip install pyTelegramBotAPI")
    sys.exit(1)

# Получение токена Telegram из переменных окружения
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN environment variable is not set")
    print("ERROR: TELEGRAM_TOKEN environment variable is not set")
    print("Please set it to your Telegram bot token from BotFather")
    sys.exit(1)

# Создаем экземпляр бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Уровни владения языком с описаниями
LANGUAGE_LEVELS = {
    "A1": "Beginner - You're just starting with English",
    "A2": "Elementary - You can use simple phrases and sentences",
    "B1": "Intermediate - You can discuss familiar topics",
    "B2": "Upper Intermediate - You can interact with fluency",
    "C1": "Advanced - You can express yourself fluently and spontaneously",
    "C2": "Proficiency - You can understand virtually everything heard or read"
}

# Импортируем менеджер сессий с поддержкой базы данных
try:
    from db_session_manager import DatabaseSessionManager
    from flask import Flask
    import os
    
    # Пробуем использовать базу данных, если доступна
    if os.environ.get("DATABASE_URL"):
        # Создаем Flask приложение для инициализации БД
        app = Flask(__name__)
        database_url = os.environ.get("DATABASE_URL")
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_recycle": 300, "pool_pre_ping": True,
        }
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        
        # Используем сессии с базой данных
        session_manager = DatabaseSessionManager(app)
        logger.info("Используется менеджер сессий с базой данных")
    else:
        # Используем in-memory сессии
        session_manager = DatabaseSessionManager()
        logger.warning("База данных недоступна. Используются сессии в памяти")
        
except ImportError:
    logger.warning("Модуль db_session_manager не найден. Используются сессии в памяти")
    # Простое хранилище сессий в памяти (для обратной совместимости)
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

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Обрабатывает команду /start."""
    user_name = message.from_user.first_name
    bot.send_message(
        message.chat.id,
        f"Hello {user_name}! 👋\n\n"
        "I'm Language Mirror, an AI assistant that helps you learn English through topics "
        "that genuinely interest you – your thoughts, experiences, and feelings.\n\n"
        "I'm not a traditional language teacher. I help you express yourself in English "
        "with confidence and emotional accuracy through natural conversation.\n\n"
        "Use /discussion to start a conversation with me!"
    )

@bot.message_handler(commands=['discussion'])
def handle_discussion(message):
    """Обрабатывает команду /discussion."""
    user_id = message.from_user.id
    
    # Определяем, какую систему хранения сессий использовать
    if 'session_manager' in globals():
        # Проверяем, есть ли у пользователя активная сессия через менеджер
        session = session_manager.get_session(user_id)
        if session:
            bot.send_message(
                message.chat.id,
                "You're already in a discussion with me. You can continue talking or "
                "use /stop_discussion to end our current conversation."
            )
            return
    else:
        # Используем старую систему хранения в памяти
        if user_id in user_sessions:
            bot.send_message(
                message.chat.id,
                "You're already in a discussion with me. You can continue talking or "
                "use /stop_discussion to end our current conversation."
            )
            return
    
    # Создаем клавиатуру для выбора уровня языка
    markup = types.InlineKeyboardMarkup()
    for level, description in LANGUAGE_LEVELS.items():
        markup.add(types.InlineKeyboardButton(
            f"{level} - {description}", 
            callback_data=f"level_{level}"
        ))
    
    bot.send_message(
        message.chat.id,
        "Before we begin, I'd like to know your English proficiency level "
        "so I can adapt to your needs. Please select your level:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('level_'))
def handle_language_level(call):
    """Обрабатывает выбор уровня владения языком."""
    # Извлекаем уровень из callback_data
    level = call.data.split('_')[1]
    user_id = call.from_user.id
    
    # Получаем дополнительную информацию о пользователе
    user_info = {
        "language_level": level,
        "username": call.from_user.username,
        "first_name": call.from_user.first_name,
        "last_name": call.from_user.last_name
    }
    
    # Инициализируем сессию пользователя
    if 'session_manager' in globals():
        # Используем менеджер сессий с поддержкой БД
        session_manager.create_session(user_id, user_info)
    else:
        # Используем старую систему хранения в памяти
        user_sessions[user_id] = {
            "language_level": level,
            "messages": [],
            "last_active": time.time()
        }
    
    # Предлагаем тему на основе уровня
    topics = CONVERSATION_TOPICS.get(level, CONVERSATION_TOPICS["B1"])
    suggested_topic = random.choice(topics)
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Great! I'll adapt to your {level} level. Let's start our conversation!\n\n"
        f"Here's a suggestion: {suggested_topic}\n\n"
        "But feel free to talk about anything that interests you!"
    )

@bot.message_handler(commands=['stop_discussion'])
def handle_stop_discussion(message):
    """Обрабатывает команду /stop_discussion."""
    user_id = message.from_user.id
    
    # Проверяем, есть ли у пользователя активная сессия
    session_exists = False
    
    if 'session_manager' in globals():
        session = session_manager.get_session(user_id)
        if session:
            session_exists = True
    elif user_id in user_sessions:
        session_exists = True
    
    if not session_exists:
        bot.send_message(
            message.chat.id,
            "You don't have an active discussion session. "
            "Use /discussion to start one."
        )
        return
    
    # Создаем клавиатуру для обратной связи
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("👍 Helpful", callback_data="feedback_helpful"),
        types.InlineKeyboardButton("🤔 Okay", callback_data="feedback_okay"),
        types.InlineKeyboardButton("👎 Not helpful", callback_data="feedback_not_helpful")
    )
    
    bot.send_message(
        message.chat.id,
        "Thank you for our conversation! I hope it was helpful for your English learning journey.\n\n"
        "How would you rate our discussion?",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('feedback_'))
def handle_feedback(call):
    """Обрабатывает обратную связь пользователя."""
    user_id = call.from_user.id
    feedback_type = call.data.split('_')[1]
    
    # Сопоставляем типы обратной связи с оценками
    rating_map = {
        "helpful": "👍 Helpful",
        "okay": "🤔 Okay",
        "not_helpful": "👎 Not helpful"
    }
    
    # Сохраняем обратную связь в лог
    logger.info(f"User {user_id} gave feedback: {rating_map.get(feedback_type)}")
    
    # Запрашиваем дополнительный комментарий
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Thank you for your feedback: {rating_map.get(feedback_type)}!\n\n"
        "Would you like to add any comments about our conversation? "
        "Please reply to this message with your comments or type /skip to finish."
    )
    
    # Сохраняем тип обратной связи во временном хранилище для следующего обработчика
    if 'session_manager' in globals():
        # Завершаем сессию в базе данных, но сохраняем информацию о feedback
        session = session_manager.get_session(user_id)
        if session:
            session_manager.end_session(user_id)
        
        # Создаем временную сессию только для хранения типа обратной связи
        session_manager.create_session(user_id, {"feedback_type": feedback_type})
    else:
        # В telebot нет user_data как в python-telegram-bot, поэтому используем сессии
        if user_id in user_sessions:
            user_sessions[user_id]["feedback_type"] = feedback_type
            # Очищаем сессию (сохраняем только feedback_type)
            user_sessions[user_id] = {
                "feedback_type": feedback_type,
                "last_active": time.time()
            }
        else:
            user_sessions[user_id] = {
                "feedback_type": feedback_type,
                "last_active": time.time()
            }
    
    # Устанавливаем следующий шаг - ожидание комментария
    bot.register_next_step_handler(call.message, handle_feedback_comment)

def handle_feedback_comment(message):
    """Обрабатывает комментарии к обратной связи."""
    user_id = message.from_user.id
    comment = message.text
    
    if comment.lower() == "/skip":
        bot.send_message(
            message.chat.id,
            "Thanks again for your feedback! Use /discussion anytime you want to practice English."
        )
        
        # Завершаем сессию
        if 'session_manager' in globals():
            session_manager.end_session(user_id)
        elif user_id in user_sessions:
            del user_sessions[user_id]
            
        return
    
    # Получаем тип обратной связи из временного хранилища
    feedback_type = "unknown"
    
    if 'session_manager' in globals():
        session = session_manager.get_session(user_id)
        if session and "feedback_type" in session:
            feedback_type = session["feedback_type"]
    elif user_id in user_sessions and "feedback_type" in user_sessions[user_id]:
        feedback_type = user_sessions[user_id]["feedback_type"]
    
    rating_map = {
        "helpful": "👍 Helpful",
        "okay": "🤔 Okay",
        "not_helpful": "👎 Not helpful",
        "unknown": "Rating not provided"
    }
    
    # Сохраняем обратную связь в базу данных, если доступна
    try:
        # Пытаемся отправить HTTP запрос для сохранения обратной связи в БД
        feedback_data = {
            "user_id": user_id,
            "username": message.from_user.username or f"user_{user_id}",
            "rating": feedback_type,
            "comment": comment
        }
        
        # Используем requests.post в отдельном потоке, чтобы не блокировать бота
        threading.Thread(
            target=lambda: requests.post("http://localhost:5000/api/feedback", json=feedback_data),
            daemon=True
        ).start()
    except Exception as e:
        logger.error(f"Error saving feedback to database: {e}")
    
    # В любом случае логируем обратную связь
    logger.info(f"User {user_id} feedback {rating_map.get(feedback_type)} with comment: {comment}")
    
    bot.send_message(
        message.chat.id,
        "Thank you for your additional comments! Your feedback helps me improve.\n\n"
        "Feel free to use /discussion anytime you want to practice English again."
    )
    
    # Очищаем данные обратной связи из временного хранилища
    if 'session_manager' in globals():
        session_manager.end_session(user_id)
    elif user_id in user_sessions:
        del user_sessions[user_id]

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

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Обрабатывает все текстовые сообщения."""
    # Игнорируем команды
    if message.text.startswith('/'):
        return
    
    user_id = message.from_user.id
    user_message = message.text
    
    # Проверяем, есть ли у пользователя активная сессия
    session_exists = False
    language_level = "B1"  # Значение по умолчанию
    
    if 'session_manager' in globals():
        # Проверка через менеджер сессий с БД
        session = session_manager.get_session(user_id)
        if session and "language_level" in session:
            session_exists = True
            language_level = session.get("language_level", "B1")
    elif user_id in user_sessions and "language_level" in user_sessions[user_id]:
        # Проверка через старую систему хранения в памяти
        session_exists = True
        language_level = user_sessions[user_id].get("language_level", "B1")
    
    if not session_exists:
        bot.send_message(
            message.chat.id,
            "Please use /discussion to start a conversation with me first."
        )
        return
    
    # Имитируем "печатание" бота
    bot.send_chat_action(message.chat.id, 'typing')
    time.sleep(1.5)  # Имитация времени обдумывания
    
    # Добавляем сообщение пользователя в сессию
    if 'session_manager' in globals():
        session_manager.add_message_to_session(user_id, "user", user_message)
    else:
        # Используем старую систему хранения в памяти
        if "messages" not in user_sessions[user_id]:
            user_sessions[user_id]["messages"] = []
        user_sessions[user_id]["messages"].append({"role": "user", "content": user_message})
        user_sessions[user_id]["last_active"] = time.time()
    
    # Генерируем ответ на основе сообщения пользователя
    response = generate_learning_response(user_message, language_level)
    
    # Сохраняем ответ бота в сессии
    if 'session_manager' in globals():
        session_manager.add_message_to_session(user_id, "assistant", response)
    else:
        user_sessions[user_id]["messages"].append({"role": "assistant", "content": response})
    
    # Отправляем ответ пользователю
    bot.send_message(message.chat.id, response)

def main():
    """Запускает бота."""
    logger.info("Starting Language Mirror bot...")
    print("Bot is running! Press Ctrl+C to stop.")
    
    # Запускаем бота с использованием long polling
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

if __name__ == "__main__":
    main()