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
from openrouter_client import OpenRouterClient

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

# Шаблоны ответов для симуляции разговора с обучением языку (резервный вариант)
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

# Создаем клиент OpenRouter для генерации ответов AI
openrouter_client = OpenRouterClient()

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
    
    # Создаем клавиатуру с командами
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    start_button = types.KeyboardButton('/discussion')
    stop_button = types.KeyboardButton('/stop_discussion')
    help_button = types.KeyboardButton('/help')
    markup.add(start_button, stop_button, help_button)
    
    # Отправляем приветственное сообщение с клавиатурой
    welcome_text = (
        f"Hello {user_name}! 👋\n\n"
        "I'm Language Mirror, an AI assistant that helps you learn English through topics "
        "that genuinely interest you – your thoughts, experiences, and feelings.\n\n"
        "🔹 Функции бота:\n\n"
        "• Разговорная практика - общайтесь со мной на любые темы, чтобы улучшить свой английский\n"
        "• Адаптация к уровню - я подстраиваюсь под ваш уровень владения языком (от A1 до C2)\n"
        "• Корректировка ошибок - я мягко исправляю ваши ошибки, помогая улучшить языковые навыки\n"
        "• Персонализированные темы - я предлагаю темы для обсуждения, основываясь на вашем уровне\n"
        "• Обратная связь - после завершения разговора вы можете оставить отзыв\n\n"
        "🔹 Основные команды:\n\n"
        "• /discussion - начать обсуждение на английском\n"
        "• /stop_discussion - завершить текущее обсуждение\n"
        "• /help - получить справку о работе бота\n\n"
        "Используйте кнопки ниже или введите команду вручную, чтобы начать!"
    )
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=markup
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

def generate_learning_response(user_message: str, language_level: str, conversation_history=None) -> str:
    """
    Генерирует ответ для обучения языку на основе сообщения пользователя и уровня.
    
    Использует OpenRouter API для генерации естественных ответов с учетом уровня владения языком.
    В случае недоступности API использует резервный режим с шаблонами.
    
    Args:
        user_message: Сообщение пользователя
        language_level: Уровень владения языком (A1-C2)
        conversation_history: История сообщений для сохранения контекста
    
    Returns:
        Ответ с обучающим контентом
    """
    # Попробуем использовать OpenRouter для генерации более естественного ответа
    try:
        # Создаем системное сообщение в зависимости от уровня
        system_messages = {
            "A1": """You are an English language tutor helping a beginner (A1 level) student. 
                    Use very simple vocabulary and basic grammar structures. 
                    Keep sentences short (5-7 words) and use present simple tense mostly.
                    Gently correct obvious mistakes in their English.
                    Speak like you're talking to a child, but respectfully.""",
                    
            "A2": """You are an English language tutor helping an elementary (A2 level) student.
                    Use simple vocabulary and basic grammar structures including present, past, and future tenses.
                    Keep sentences relatively short and avoid complex clauses.
                    Offer corrections for common mistakes while being supportive.""",
                    
            "B1": """You are an English language tutor helping an intermediate (B1 level) student.
                    Use a wider range of vocabulary and include some idioms.
                    Use various tenses appropriately but avoid overly complex grammatical structures.
                    Correct errors that interfere with understanding while acknowledging good use of language.""",
                    
            "B2": """You are an English language tutor helping an upper-intermediate (B2 level) student.
                    Use a wide vocabulary including some academic words and phrasal verbs.
                    Use complex grammatical structures when appropriate.
                    Focus on nuanced corrections and improving fluency rather than basic errors.""",
                    
            "C1": """You are an English language tutor helping an advanced (C1 level) student.
                    Use sophisticated vocabulary, idioms, and colloquialisms appropriately.
                    Use a full range of grammatical structures including complex and compound-complex sentences.
                    Focus on subtle improvements in expression and style rather than obvious errors.""",
                    
            "C2": """You are an English language tutor helping a proficient (C2 level) student.
                    Use sophisticated vocabulary, cultural references, and nuanced expressions.
                    Focus on very specific feedback about style, register, and tone.
                    Treat the student as a near-native speaker and engage in high-level discussion."""
        }
        
        # Получаем системное сообщение для данного уровня или используем B1 по умолчанию
        system_message = system_messages.get(language_level, system_messages["B1"])
        
        # Если история сообщений не передана, создаем новый список только с текущим сообщением
        if not conversation_history:
            messages = [{"role": "user", "content": user_message}]
        else:
            # Ограничиваем историю до 10 последних сообщений, чтобы не превышать лимиты токенов
            messages = conversation_history[-10:]
            # Убедимся, что последнее сообщение - текущий запрос пользователя
            if messages and messages[-1]["role"] != "user":
                messages.append({"role": "user", "content": user_message})
        
        # Получаем ответ от OpenRouter
        response = openrouter_client.get_completion(system_message, messages)
        
        # Если получили пустой ответ, используем резервный режим
        if not response or response.strip() == "":
            raise Exception("Empty response from OpenRouter")
            
        return response
        
    except Exception as e:
        # Логируем ошибку
        logger.error(f"Error using OpenRouter API: {e}. Falling back to template mode.")
        
        # Резервный режим - используем шаблоны
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
    
    # Получаем историю сообщений для контекста
    conversation_history = []
    if 'session_manager' in globals():
        conversation_history = session_manager.get_messages(user_id)
    elif user_id in user_sessions and "messages" in user_sessions[user_id]:
        conversation_history = user_sessions[user_id]["messages"]
    
    # Генерируем ответ на основе сообщения пользователя и истории
    response = generate_learning_response(user_message, language_level, conversation_history)
    
    # Сохраняем ответ бота в сессии
    if 'session_manager' in globals():
        session_manager.add_message_to_session(user_id, "assistant", response)
    else:
        user_sessions[user_id]["messages"].append({"role": "assistant", "content": response})
    
    # Отправляем ответ пользователю
    bot.send_message(message.chat.id, response)

# Добавляем обработчик команды помощи
@bot.message_handler(commands=['help'])
def handle_help(message):
    """Обрабатывает команду /help."""
    help_text = (
        "🤖 Language Mirror Bot - Помощь\n\n"
        "Я помогаю вам практиковать английский язык через естественное общение. "
        "Я адаптируюсь к вашему уровню владения языком и предлагаю темы для обсуждения.\n\n"
        "🔹 Как начать:\n"
        "1. Используйте команду /discussion, чтобы начать разговор\n"
        "2. Выберите ваш уровень английского (A1-C2)\n"
        "3. Общайтесь со мной на английском на любую тему\n"
        "4. Когда закончите, используйте /stop_discussion\n"
        "5. Оставьте обратную связь о нашем разговоре\n\n"
        "🔹 Доступные команды:\n\n"
        "• /start - Начальное приветствие и информация о боте\n"
        "• /discussion - Начать новый разговор для практики английского\n"
        "• /stop_discussion - Завершить текущую беседу и оставить отзыв\n"
        "• /help - Показать это сообщение помощи\n\n"
        "🔹 Уровни английского:\n\n"
        "• A1 - Начальный (базовые фразы и слова)\n"
        "• A2 - Элементарный (простые предложения)\n"
        "• B1 - Средний (повседневные темы)\n"
        "• B2 - Средне-продвинутый (свободное общение)\n"
        "• C1 - Продвинутый (беглая речь)\n"
        "• C2 - Профессиональный (почти как носитель языка)\n\n"
        "Если у вас возникли проблемы или вопросы, пожалуйста, обратитесь к администратору."
    )
    
    bot.send_message(message.chat.id, help_text)

# Добавляем команду для получения отчета о обратной связи
@bot.message_handler(commands=['admin_feedback'])
def handle_admin_feedback(message):
    """
    Обрабатывает команду /admin_feedback.
    Эта команда доступна только администраторам и позволяет им получать отчет об обратной связи.
    """
    user_id = message.from_user.id
    
    # Список ID администраторов (в реальном проекте это должно храниться в базе данных или env)
    # Чтобы получить свой Telegram ID, отправьте команду /start боту @userinfobot и добавьте ID ниже
    # ВАЖНО: Добавьте сюда свой числовой Telegram ID, чтобы получить доступ к функции администратора
    # Например: admin_ids = [123456789, 987654321]
    admin_ids = []
    
    # Проверка является ли пользователь администратором
    if user_id not in admin_ids:
        bot.reply_to(message, "Извините, эта команда доступна только администраторам.")
        return
    
    try:
        # Используем requests для запроса данных обратной связи из базы данных
        # (предполагая, что API доступен и работает на localhost:5000)
        response = requests.get("http://localhost:5000/api/feedback")
        
        if response.status_code != 200:
            bot.reply_to(
                message,
                f"Ошибка при получении данных обратной связи: {response.status_code}\n"
                f"Сообщение: {response.text}"
            )
            return
        
        feedback_data = response.json()
        
        if not feedback_data:
            bot.reply_to(message, "Данные обратной связи отсутствуют.")
            return
        
        # Формируем отчет
        rating_counts = {
            "helpful": 0,
            "okay": 0,
            "not_helpful": 0
        }
        
        for item in feedback_data:
            rating = item.get('rating')
            if rating in rating_counts:
                rating_counts[rating] += 1
                
        # Отправляем отчет администратору
        report = "📊 Отчет по обратной связи\n\n"
        report += f"👍 Полезно: {rating_counts['helpful']}\n"
        report += f"🤔 Нормально: {rating_counts['okay']}\n"
        report += f"👎 Не полезно: {rating_counts['not_helpful']}\n\n"
        report += "Последние 5 комментариев:"
        
        # Добавляем последние 5 комментариев
        for i, item in enumerate(feedback_data[:5]):
            if item.get('comment'):
                report += f"\n{i+1}. {item.get('rating', 'unknown')}: \"{item.get('comment')}\""
        
        # Отправляем отчет
        bot.reply_to(message, report)
        
    except Exception as e:
        bot.reply_to(
            message, 
            f"Произошла ошибка при получении данных обратной связи: {str(e)}"
        )
        logger.error(f"Error in admin_feedback: {e}")

def main():
    """Запускает бота."""
    logger.info("Starting Language Mirror bot...")
    print("Bot is running! Press Ctrl+C to stop.")
    
    # Запускаем бота с использованием long polling
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

if __name__ == "__main__":
    main()