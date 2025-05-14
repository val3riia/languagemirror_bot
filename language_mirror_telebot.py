#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Language Mirror Bot - A Telegram bot for interactive language learning.
Эта версия использует Google Sheets для хранения данных и UptimeBot для хостинга.
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
    level=logging.DEBUG  # Уровень DEBUG для более подробных логов
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

# Список администраторов (имена пользователей и ID)
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "")
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID", "")

# Словарь администраторов
ADMIN_USERS = {}

# Принудительно добавляем администратора для отладки при необходимости
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_USER_ID = 123456789  # Замените на свой ID при тестировании

# Обрабатываем основные переменные окружения
if ADMIN_USERNAME and ADMIN_USER_ID:
    try:
        ADMIN_USERS[ADMIN_USERNAME.lower()] = int(ADMIN_USER_ID)
        logger.info(f"Администратор добавлен из переменных окружения: {ADMIN_USERNAME}")
    except ValueError:
        logger.error(f"ADMIN_USER_ID ({ADMIN_USER_ID}) не является числом")

# Делаем валидацию менее строгой для администраторов
if not ADMIN_USERS and (ADMIN_USERNAME or ADMIN_USER_ID):
    # Если указано только имя пользователя
    if ADMIN_USERNAME and not ADMIN_USER_ID:
        ADMIN_USERS[ADMIN_USERNAME.lower()] = 0  # Любой ID
        logger.info(f"Администратор (только по имени): {ADMIN_USERNAME}")
    
    # Если указан только ID
    if ADMIN_USER_ID and not ADMIN_USERNAME:
        try:
            ADMIN_USER_ID_INT = int(ADMIN_USER_ID)
            ADMIN_USERS[""] = ADMIN_USER_ID_INT  # Любое имя пользователя
            logger.info(f"Администратор (только по ID): {ADMIN_USER_ID}")
        except ValueError:
            logger.error(f"ADMIN_USER_ID ({ADMIN_USER_ID}) не является числом")

# В режиме отладки добавляем тестового администратора для тестирования
DEBUG_ADMIN = os.environ.get("DEBUG_ADMIN", "False").lower() in ["true", "1", "yes", "y"]

# Принудительно включаем режим отладки с администратором для текущей отладки проблем
FORCE_DEBUG_ADMIN = True

if (DEBUG_ADMIN or FORCE_DEBUG_ADMIN) and not ADMIN_USERS:
    # Используем пустую строку как имя пользователя, чтобы проверять только по ID
    ADMIN_USERS[""] = DEFAULT_ADMIN_USER_ID
    
    # Также добавляем конкретного администратора для отладки
    ADMIN_USERS[DEFAULT_ADMIN_USERNAME] = DEFAULT_ADMIN_USER_ID
    
    # И администратора с любым ID (только по имени)
    ADMIN_USERS["admin"] = 0
    
    logger.warning(f"⚠️ Добавлены тестовые администраторы для отладки")

# Проверяем наличие администраторов в системе
if ADMIN_USERS:
    logger.info(f"Настройки администратора загружены успешно: {list(ADMIN_USERS.keys())}")
else:
    logger.warning("Не настроен ни один администратор, команды управления будут недоступны")

# Отладочный режим (можно включить в .env)
DEBUG_MODE = os.environ.get("DEBUG", "False").lower() == "true"

# Дополнительные настройки из переменных окружения
FEEDBACK_COMMENT_MIN_WORDS = int(os.environ.get("FEEDBACK_COMMENT_MIN_WORDS", "3"))
MAX_DAILY_DISCUSSIONS = int(os.environ.get("MAX_DAILY_DISCUSSIONS", "5"))
ENABLE_ARTICLE_SEARCH = os.environ.get("ENABLE_ARTICLE_SEARCH", "True").lower() == "true"

# Уровни владения языком с описаниями
LANGUAGE_LEVELS = {
    "A1": "Beginner - You're just starting with English",
    "A2": "Elementary - You can use simple phrases and sentences",
    "B1": "Intermediate - You can discuss familiar topics",
    "B2": "Upper Intermediate - You can interact with fluency",
    "C1": "Advanced - You can express yourself fluently and spontaneously",
    "C2": "Proficiency - You can understand virtually everything heard or read"
}

# Импортируем менеджер сессий с поддержкой Google Sheets
try:
    from sheets_session_manager import SheetSessionManager
    from sheets_manager import SheetsManager
    
    # Проверяем наличие необходимых переменных окружения
    google_creds_path = os.environ.get("GOOGLE_CREDENTIALS_PATH")
    google_sheets_key = os.environ.get("GOOGLE_SHEETS_KEY")
    
    if google_creds_path and google_sheets_key:
        # Создаем экземпляр менеджера Google Sheets
        sheets_manager = SheetsManager(
            creds_path=google_creds_path, 
            spreadsheet_key=google_sheets_key
        )
        
        # Создаем экземпляр менеджера сессий
        session_manager = SheetSessionManager(sheets_manager)
        logger.info("Используется менеджер сессий с Google Sheets")
    else:
        # Если переменные окружения не настроены, используем словарь в памяти
        logger.warning("GOOGLE_CREDENTIALS_PATH или GOOGLE_SHEETS_KEY не найдены. Используются сессии в памяти")
        user_sessions = {}
        
except Exception as e:
    logger.warning(f"Ошибка инициализации Google Sheets: {e}. Используются сессии в памяти")
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
    start_button = types.KeyboardButton('/start')
    discussion_button = types.KeyboardButton('/discussion')
    stop_button = types.KeyboardButton('/stop_discussion')
    
    # Добавляем основные кнопки
    markup.add(start_button)
    markup.add(discussion_button, stop_button)
    
    # Проверяем, является ли пользователь администратором
    username = message.from_user.username if hasattr(message.from_user, 'username') else None
    user_id = message.from_user.id
    
    # Расширенная проверка на имя пользователя и ID администратора
    is_admin = False
    
    # Сначала проверяем наличие пользователя
    if not username:
        username = ""  # Для безопасного логирования
        logger.info(f"У пользователя нет имени пользователя, используется только ID: {user_id}")
    
    # Проверяем все возможные варианты
    # 1. Проверка по точному совпадению имени и ID
    if username.lower() in ADMIN_USERS and ADMIN_USERS.get(username.lower()) == user_id:
        is_admin = True
        logger.info(f"Пользователь {username} успешно авторизован как администратор (точное совпадение)")
    
    # 2. Проверка только по имени, если ID указан как 0 (любой ID)
    elif username.lower() in ADMIN_USERS and ADMIN_USERS.get(username.lower()) == 0:
        is_admin = True
        logger.info(f"Пользователь {username} успешно авторизован как администратор (только по имени)")
    
    # 3. Проверка только по ID, если имя указано как пустая строка (любое имя)
    elif "" in ADMIN_USERS and ADMIN_USERS.get("") == user_id:
        is_admin = True
        logger.info(f"Пользователь {username} (ID: {user_id}) успешно авторизован как администратор (только по ID)")
    
    # 4. Прямая проверка в словаре для других случаев
    for admin_name, admin_id in ADMIN_USERS.items():
        if admin_name and username and admin_name.lower() == username.lower():
            is_admin = True
            logger.info(f"Пользователь {username} успешно авторизован как администратор (по имени)")
            break
        elif admin_id and admin_id == user_id:
            is_admin = True
            logger.info(f"Пользователь (ID: {user_id}) успешно авторизован как администратор (по ID)")
            break
    
    # В отладочном режиме всегда разрешаем доступ
    if DEBUG_MODE:
        debug_admin_id = int(os.environ.get("DEBUG_ADMIN_ID", "0"))
        if debug_admin_id and user_id == debug_admin_id:
            is_admin = True
            logger.info(f"Пользователь (ID: {user_id}) авторизован как администратор в режиме отладки")
        
        # Отладочный лог
        logger.info(f"DEBUG: username={username}, user_id={user_id}, is_admin={is_admin}, admin_users={ADMIN_USERS}")
    
    if is_admin:
        # Добавляем кнопку администратора
        admin_button = types.KeyboardButton('/admin_feedback')
        markup.add(admin_button)
        logger.info(f"Добавлена кнопка администратора для пользователя {username}")
        
    # Формируем приветственное сообщение
    welcome_text = f"Hello {user_name}! 👋\n\n"
    welcome_text += "I'm Language Mirror, an AI assistant that helps you learn English through topics "
    welcome_text += "that genuinely interest you – your thoughts, experiences, and feelings.\n\n"
    welcome_text += "🔹 Bot Features:\n\n"
    welcome_text += "• Conversation Practice - chat with me on any topic to improve your English\n"
    welcome_text += "• Level Adaptation - I adjust to your language proficiency (from A1 to C2)\n"
    welcome_text += "• Error Correction - I gently correct your mistakes to help you improve\n"
    welcome_text += "• Personalized Topics - I suggest discussion topics based on your level\n"
    welcome_text += "• Article Recommendations - I can suggest reading materials on topics you're interested in\n"
    welcome_text += "• Feedback System - provide feedback after conversations to help improve the bot\n\n"
    welcome_text += "🔹 Main Commands:\n\n"
    welcome_text += "• /start - show this welcome message\n"
    welcome_text += "• /discussion - start an English conversation or get article recommendations (1 request per day)\n"
    welcome_text += "• /stop_discussion - end the current conversation\n\n"
    welcome_text += "Use the buttons below or type a command to get started!"
    
    # Отправляем сообщение
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)
    
    # Обновляем пользователя в базе данных или создаем нового
    try:
        from models import db, User
        from main import app
        
        with app.app_context():
            # Ищем пользователя в базе данных
            user_record = User.query.filter_by(telegram_id=message.from_user.id).first()
            
            if not user_record:
                # Создаем нового пользователя, если не существует
                user_record = User(
                    telegram_id=message.from_user.id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name
                )
                db.session.add(user_record)
                db.session.commit()
                logger.info(f"New user registered: {message.from_user.id} ({message.from_user.username})")
            else:
                # Обновляем дату последней активности
                user_record.last_activity = datetime.utcnow()
                db.session.commit()
    except Exception:
        logger.error("Error updating user in database")

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
    
    # Проверяем лимит на количество запросов в день
    from datetime import date
    today = date.today()
    
    # Ищем пользователя в базе данных
    from models import db, User
    from main import app
    user_record = None
    
    # Создаем контекст приложения Flask
    with app.app_context():
        user_record = User.query.filter_by(telegram_id=user_id).first()
        
        if not user_record:
            # Создаем новую запись пользователя, если его нет в базе
            user_record = User(
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )
            db.session.add(user_record)
            db.session.commit()
            
            # Пользователь новый, продолжаем без ограничений
            pass
        elif user_record.last_discussion_date == today:
            # Проверяем, является ли пользователь администратором
            username = message.from_user.username if hasattr(message.from_user, 'username') else None
            
            # Расширенная проверка на имя пользователя и ID администратора
            is_admin = False
            
            # Сначала проверяем наличие пользователя
            if not username:
                username = ""  # Для безопасного логирования
                logger.info(f"У пользователя нет имени пользователя, используется только ID: {user_id}")
            
            # Проверяем все возможные варианты
            # 1. Проверка по точному совпадению имени и ID
            if username.lower() in ADMIN_USERS and ADMIN_USERS.get(username.lower()) == user_id:
                is_admin = True
                logger.info(f"Пользователь {username} успешно авторизован как администратор (точное совпадение)")
            
            # 2. Проверка только по имени, если ID указан как 0 (любой ID)
            elif username.lower() in ADMIN_USERS and ADMIN_USERS.get(username.lower()) == 0:
                is_admin = True
                logger.info(f"Пользователь {username} успешно авторизован как администратор (только по имени)")
            
            # 3. Проверка только по ID, если имя указано как пустая строка (любое имя)
            elif "" in ADMIN_USERS and ADMIN_USERS.get("") == user_id:
                is_admin = True
                logger.info(f"Пользователь {username} (ID: {user_id}) успешно авторизован как администратор (только по ID)")
            
            # 4. Прямая проверка в словаре для других случаев
            for admin_name, admin_id in ADMIN_USERS.items():
                if admin_name and username and admin_name.lower() == username.lower():
                    is_admin = True
                    logger.info(f"Пользователь {username} успешно авторизован как администратор (по имени)")
                    break
                elif admin_id and admin_id == user_id:
                    is_admin = True
                    logger.info(f"Пользователь (ID: {user_id}) успешно авторизован как администратор (по ID)")
                    break
            
            # В отладочном режиме всегда разрешаем доступ
            if DEBUG_MODE:
                debug_admin_id = int(os.environ.get("DEBUG_ADMIN_ID", "0"))
                if debug_admin_id and user_id == debug_admin_id:
                    is_admin = True
                    logger.info(f"Пользователь (ID: {user_id}) авторизован как администратор в режиме отладки")
            
            # Для администратора не действуют ограничения
            if is_admin:
                logger.info(f"Администратор {username} (ID: {user_id}) получил безлимитный доступ")
                # Продолжаем выполнение без ограничений
                pass
            # Для обычных пользователей проверяем лимиты
            elif not user_record.feedback_bonus_used:
                # Предлагаем бонус-запрос за фидбек, если пользователь его еще не получал
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("👍 Get Bonus Request", callback_data="feedback_bonus"),
                    types.InlineKeyboardButton("❌ No Thanks", callback_data="feedback_skip")
                )
                
                bot.send_message(
                    message.chat.id,
                    "You've already used your article recommendation today!\n\n"
                    "Would you like to get a bonus request by providing feedback about our bot?",
                    reply_markup=markup
                )
                return
            else:
                # Пользователь уже использовал дневной лимит и бонус
                bot.send_message(
                    message.chat.id,
                    "You've already used your article recommendation today! Come back tomorrow for more inspiring content."
                )
                return
        
        # Если пользователь здесь, значит либо у него нет ограничений, либо он новый
        # Обновляем дату последнего запроса и увеличиваем счетчик
        if user_record:
            user_record.last_discussion_date = today
            user_record.discussions_count = (user_record.discussions_count or 0) + 1
            db.session.commit()
    
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
        "last_name": call.from_user.last_name,
        "mode": "articles" # Устанавливаем новый режим для поиска статей
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
            "last_active": time.time(),
            "mode": "articles"
        }
    
    # Запрашиваем тему у пользователя для поиска статей
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Great! I'll adapt to your {level} level.\n\nNow tell me — what topic is on your mind today? What would you like to explore?"
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

@bot.callback_query_handler(func=lambda call: call.data == "feedback_bonus" or call.data == "feedback_skip")
def handle_feedback_bonus(call):
    """Обрабатывает запрос на бонусный запрос статей за обратную связь."""
    user_id = call.from_user.id
    
    if call.data == "feedback_skip":
        # Пользователь отказался от бонуса
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="No problem! Come back tomorrow for your next article recommendation."
        )
        return
    
    # Пользователь хочет получить бонус
    # Обновляем информацию о пользователе в базе данных
    from models import db, User
    from main import app
    user_record = None
    
    # Создаем контекст приложения Flask
    with app.app_context():
        user_record = User.query.filter_by(telegram_id=user_id).first()
        
        if user_record and not user_record.feedback_bonus_used:
            # Обновляем флаг использования бонуса
            user_record.feedback_bonus_used = True
            db.session.commit()
            
    # Показываем клавиатуру выбора уровня языка, выносим это за контекст приложения
    if user_record:
        markup = types.InlineKeyboardMarkup()
        for level, description in LANGUAGE_LEVELS.items():
            markup.add(types.InlineKeyboardButton(
                f"{level} - {description}", 
                callback_data=f"level_{level}"
            ))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Thanks for providing feedback! You've received a bonus request for articles today.\n\n"
            "Before we begin, I'd like to know your English proficiency level so I can adapt to your needs. Please select your level:",
            reply_markup=markup
        )
    else:
        # Пользователь не найден в базе
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Sorry, there was an error processing your request. Please try again later."
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith('feedback_') and not (call.data == "feedback_bonus" or call.data == "feedback_skip"))
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
    
    # Сохраняем обратную связь в базу данных через API
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
        
        # Также сохраняем обратную связь напрямую в БД через SQLAlchemy
        from models import db, User, Feedback
        from main import app
        
        # Выполняем в отдельном потоке, чтобы не блокировать бота
        def save_to_db():
            with app.app_context():
                # Ищем пользователя по id
                user = User.query.filter_by(telegram_id=user_id).first()
                
                if user:
                    # Создаем запись обратной связи
                    new_feedback = Feedback(
                        user_id=user.id,
                        rating=feedback_type,
                        comment=comment
                    )
                    db.session.add(new_feedback)
                    db.session.commit()
                    
                    # Проверяем, содержит ли комментарий минимум 3 слова для предоставления бонуса
                    words = comment.split()
                    if len(words) >= 3:
                        # Обновляем статус обратной связи пользователя, предоставляя бонус
                        user.feedback_bonus_used = False  # Разрешаем использовать бонусный запрос
                        db.session.commit()
                        
                        # Отправляем уведомление о бонусном запросе
                        bot.send_message(
                            user.telegram_id,
                            "🎁 Thank you for your detailed feedback! You've received a bonus article request. "
                            "Use /discussion to use it anytime today!"
                        )
                    else:
                        bot.send_message(
                            user.telegram_id,
                            "Thank you for your feedback! For more detailed comments (at least 3 words) "
                            "you can receive bonus article requests in the future."
                        )
        
        # Запускаем сохранение в отдельном потоке
        threading.Thread(target=save_to_db, daemon=True).start()
    except Exception as e:
        logger.error("Error saving feedback to database")
    
    # В любом случае логируем обратную связь
    logger.info(f"User {user_id} feedback {rating_map.get(feedback_type)} with comment: {comment}")
    
    bot.send_message(
        message.chat.id,
        "Thank you for your comments! Your feedback helps me improve.\n\n"
        "Feel free to use /discussion anytime you want to practice English again."
    )
    
    # Очищаем данные обратной связи из временного хранилища
    if 'session_manager' in globals():
        session_manager.end_session(user_id)
    elif user_id in user_sessions:
        del user_sessions[user_id]

def find_articles_by_topic(topic: str, language_level: str) -> list:
    """
    Использует OpenRouter API для поиска релевантных статей по заданной теме.
    
    Args:
        topic: Тема для поиска статей
        language_level: Уровень владения языком пользователя (A1-C2)
        
    Returns:
        Список словарей с информацией о статьях (title, url)
    """
    try:
        # Получаем клиент OpenRouter API
        if 'openrouter_client' in globals() and openrouter_client is not None:
            system_message = f"""You are a helpful assistant that finds relevant English articles for language learners. 
The user's English level is {language_level}. Generate 3 specific, diverse, and credible article recommendations about the topic.
Respond with exactly 3 articles, no more, no less.
Format your response as a JSON array with "title" and "url" for each article. Generate real URLs to existing English articles.
Each article should be from a different source. Focus on educational, news, or blog articles that would be interesting and appropriate 
for an English learner at the {language_level} level."""

            # Создаем запрос для поиска статей
            response = openrouter_client.get_completion(
                system_message=system_message,
                messages=[
                    {"role": "user", "content": f"Please recommend 3 good articles about '{topic}' for me to read and improve my English."}
                ]
            )
            
            # Пробуем распарсить JSON ответ
            try:
                # Вначале пытаемся распарсить как есть
                articles_data = json.loads(response)
            except:
                # Если не удалось, ищем JSON в тексте ответа
                import re
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    try:
                        articles_data = json.loads(json_match.group(0))
                    except:
                        # Если и это не сработало, создаем дефолтные статьи
                        return default_articles_for_topic(topic)
                else:
                    return default_articles_for_topic(topic)
            
            # Проверяем корректность формата
            if isinstance(articles_data, list) and len(articles_data) > 0:
                # Убеждаемся, что у нас ровно 3 статьи
                articles = articles_data[:3]
                if len(articles) < 3:
                    # Дополняем до 3
                    default = default_articles_for_topic(topic)
                    articles.extend(default[len(articles):])
                return articles
            else:
                return default_articles_for_topic(topic)
                
        else:
            # Если клиент не доступен, используем стандартные статьи
            return default_articles_for_topic(topic)
            
    except Exception:
        logger.error("Error finding articles")
        # Возвращаем дефолтные статьи при ошибке
        return default_articles_for_topic(topic)

def default_articles_for_topic(topic: str) -> list:
    """
    Создает стандартный набор статей по теме при недоступности API.
    
    Args:
        topic: Тема для статей
        
    Returns:
        Список словарей с информацией о статьях
    """
    # Преобразуем тему для URL
    topic_slug = topic.lower().replace(' ', '-')
    
    return [
        {
            "title": f"Understanding {topic}: A Comprehensive Guide",
            "url": f"https://en.wikipedia.org/wiki/{topic_slug}"
        },
        {
            "title": f"The Complete Introduction to {topic}",
            "url": f"https://www.britannica.com/search?query={topic_slug}"
        },
        {
            "title": f"5 Ways to Master {topic} Quickly",
            "url": f"https://www.bbc.com/news/topics/{topic_slug}"
        }
    ]

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
        # Единый системный промпт для всех уровней с адаптацией
        system_message = """You are a friendly, thoughtful AI language coach. You talk to the user in short, natural, supportive messages. You avoid sounding robotic or overly academic. Your job is to guide the user through meaningful, real conversations in English while helping them learn new vocabulary and expressions in context.

When the user says something, respond with:
– a short, thoughtful reply;
– if needed, explain 1–2 useful words or phrases (briefly, like a real person would do);
– if appropriate, ask a follow-up question to keep the conversation flowing;
– do NOT give long essays or summaries;
– do NOT include links unless explicitly asked;
– do NOT talk like a tutor. You're a peer who speaks great English and helps naturally;
– be casual, warm, and clear — not scripted.

How to explain words (Word Card Format):
When you explain or introduce a new word, use this format:
- Part of speech
- Definition
- Example (in the same context as the user's)
- Synonyms with: preposition + something/somebody + part of speech + connotation
- Antonyms with: preposition + something/somebody + part of speech + connotation
- Common collocations
- Connotation (semantic or emotional weight)

If a phrase sounds unnatural, explain why and offer real alternatives in this format:

----------------
Sounds off?

[original user sentence]
→ [explanation why it sounds unnatural]
Instead:
• [natural option 1]
• [natural option 2]
Also avoid:
• [incorrect option]
Instead:
• [correct option with explanation]
----------------

Important guidelines:
• Never give words without context - always explain usage, grammar, prepositions, and situations
• Never say "this sounds fine" if something sounds unnatural - explain why it sounds strange, even if grammatically correct
• Never use artificial examples - your phrases should sound like a native speaker wrote them for a real situation
• Help the user express themselves, even if they write in a mix of their language and English

Your goal is to help the user grow their English by expressing real thoughts and emotions — not just learning textbook phrases. Think like a language mirror — reflecting the user's ideas in better English.

Adapt your style to the user's level ({}) if they specify it.""".format(language_level)
        
        # Словарь системных сообщений для обратной совместимости
        system_messages = {
            "A1": system_message,
            "A2": system_message,
            "B1": system_message,
            "B2": system_message,
            "C1": system_message,
            "C2": system_message
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
        
    except Exception:
        # Логируем ошибку
        logger.error("Error using OpenRouter API. Falling back to template mode.")
        
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
    session_mode = "conversation"  # Режим по умолчанию - обычная беседа
    
    if 'session_manager' in globals():
        # Проверка через менеджер сессий с БД
        session = session_manager.get_session(user_id)
        if session and "language_level" in session:
            session_exists = True
            language_level = session.get("language_level", "B1")
            session_mode = session.get("mode", "conversation")
    elif user_id in user_sessions and "language_level" in user_sessions[user_id]:
        # Проверка через старую систему хранения в памяти
        session_exists = True
        language_level = user_sessions[user_id].get("language_level", "B1")
        session_mode = user_sessions[user_id].get("mode", "conversation")
    
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
    
    # Проверяем режим сессии
    if session_mode == "articles":
        # Режим статей - пользователь ввел тему для поиска статей
        topic = user_message
        
        # Используем OpenRouter API для поиска статей по теме
        articles = find_articles_by_topic(topic, language_level)
        
        # Формируем ответ со списком статей
        articles_text = f"Here are some great pieces to reflect on your topic – \"{topic}\":\n\n"
        for i, article in enumerate(articles, 1):
            articles_text += f"{i}. [{article['title']}]({article['url']})\n"
        
        # Формируем клавиатуру для обратной связи
        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            types.InlineKeyboardButton("👍 Useful", callback_data="feedback_helpful"),
            types.InlineKeyboardButton("🤔 Okay", callback_data="feedback_okay"),
            types.InlineKeyboardButton("👎 Not really", callback_data="feedback_not_helpful")
        )
        
        # Отправляем ответ со статьями и завершаем беседу
        bot.send_message(message.chat.id, articles_text, parse_mode="Markdown")
        bot.send_message(
            message.chat.id,
            "Hope that gave you something to think about! Want to explore another topic? Just type /discussion.\n\nHow was that for you?",
            reply_markup=markup
        )
        
        # Заканчиваем сессию
        if 'session_manager' in globals():
            session_manager.end_session(user_id)
        else:
            if user_id in user_sessions:
                # Сохраняем только информацию для получения обратной связи
                user_sessions[user_id] = {
                    "last_active": time.time(),
                    "waiting_for_feedback": True
                }
    else:
        # Стандартный режим разговора
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

# При необходимости переадресуем /help на /start для совместимости
@bot.message_handler(commands=['help'])
def handle_help(message):
    """Переадресует команду /help на /start."""
    handle_start(message)

# Добавляем команду для получения отчета о обратной связи
@bot.message_handler(commands=['admin_feedback'])
def handle_admin_feedback(message):
    """
    Обрабатывает команду /admin_feedback.
    Эта команда доступна только администраторам и позволяет им получать отчет об обратной связи
    прямо из базы данных.
    """
    # Принудительно включаем отладочный режим для этой функции
    debug_this_function = True
    
    # Печатаем в консоль для диагностики
    print("===================== ADMIN FEEDBACK COMMAND STARTED =====================")
    print(f"User ID: {message.from_user.id}, Username: {message.from_user.username}")
    print(f"ADMIN_USERS: {ADMIN_USERS}")
    print(f"DATABASE_URL настроен: {bool(os.environ.get('DATABASE_URL'))}")
    
    # Логируем начало выполнения команды
    logger.info(f"🔍 Начало обработки команды /admin_feedback")
    
    # Сначала сообщаем пользователю, что мы начали обработку
    bot.send_message(message.chat.id, "🔄 Начало обработки команды /admin_feedback...")
    
    user_id = message.from_user.id
    username = message.from_user.username if hasattr(message.from_user, 'username') else None
    
    # Расширенная проверка на имя пользователя и ID администратора
    is_admin = False
    
    # Сначала проверяем наличие пользователя
    if not username:
        username = ""  # Для безопасного логирования
        logger.info(f"У пользователя нет имени пользователя, используется только ID: {user_id}")
    
    # Проверяем все возможные варианты
    # 1. Проверка по точному совпадению имени и ID
    if username.lower() in ADMIN_USERS and ADMIN_USERS.get(username.lower()) == user_id:
        is_admin = True
        logger.info(f"Пользователь {username} успешно авторизован как администратор (точное совпадение)")
    
    # 2. Проверка только по имени, если ID указан как 0 (любой ID)
    elif username.lower() in ADMIN_USERS and ADMIN_USERS.get(username.lower()) == 0:
        is_admin = True
        logger.info(f"Пользователь {username} успешно авторизован как администратор (только по имени)")
    
    # 3. Проверка только по ID, если имя указано как пустая строка (любое имя)
    elif "" in ADMIN_USERS and ADMIN_USERS.get("") == user_id:
        is_admin = True
        logger.info(f"Пользователь {username} (ID: {user_id}) успешно авторизован как администратор (только по ID)")
    
    # 4. Прямая проверка в словаре для других случаев
    for admin_name, admin_id in ADMIN_USERS.items():
        if admin_name and username and admin_name.lower() == username.lower():
            is_admin = True
            logger.info(f"Пользователь {username} успешно авторизован как администратор (по имени)")
            break
        elif admin_id and admin_id == user_id:
            is_admin = True
            logger.info(f"Пользователь (ID: {user_id}) успешно авторизован как администратор (по ID)")
            break
    
    # В отладочном режиме всегда разрешаем доступ
    if DEBUG_MODE:
        debug_admin_id = int(os.environ.get("DEBUG_ADMIN_ID", "0"))
        if debug_admin_id and user_id == debug_admin_id:
            is_admin = True
            logger.info(f"Пользователь (ID: {user_id}) авторизован как администратор в режиме отладки")
    
    # Логгируем результат проверки (без чувствительных данных)
    logger.info(f"Проверка прав администратора завершена, результат: {is_admin}")
    
    # Отладочный вывод (только если включен отладочный режим)
    if DEBUG_MODE:
        bot.send_message(
            message.chat.id, 
            f"🔍 Отладка: Проверка прав администратора\nРезультат проверки: {is_admin}"
        )
    
    # Отказываем в доступе неадминистраторам
    if not is_admin:
        bot.reply_to(message, "Извините, эта команда доступна только администраторам.")
        return
    
    bot.send_message(message.chat.id, "🔄 Получение данных обратной связи...")
    
    try:
        # Проверяем наличие необходимых переменных окружения для Google Sheets
        google_creds_path = os.environ.get("GOOGLE_CREDENTIALS_PATH")
        google_sheets_key = os.environ.get("GOOGLE_SHEETS_KEY")
        
        if not google_creds_path or not google_sheets_key:
            error_msg = "❌ Ошибка: переменные окружения GOOGLE_CREDENTIALS_PATH или GOOGLE_SHEETS_KEY не найдены"
            logger.error(error_msg)
            bot.send_message(
                message.chat.id,
                error_msg + "\n\nНеобходимо настроить подключение к Google Sheets в переменных окружения."
            )
            
            # Создаем отчет без подключения к Google Sheets
            create_empty_report(message.chat.id)
            return
        
        # Отладочное сообщение
        logger.info("🔍 Подключение к Google Sheets...")
        bot.send_message(
            message.chat.id,
            "🔍 Подключение к Google Sheets..."
        )
        
        # Инициализируем список для записей обратной связи
        feedback_records = []
        
        # Подключаемся к Google Sheets и получаем данные
        try:
            # Импортируем модуль для работы с Google Sheets
            from sheets_manager import SheetsManager
            from sheets_excel_report import create_temp_excel_for_telegram
            
            # Создаем экземпляр менеджера Google Sheets
            sheets_manager = SheetsManager(
                creds_path=google_creds_path, 
                spreadsheet_key=google_sheets_key
            )
            
            # Получаем данные обратной связи
            feedback_data = sheets_manager.get_all_feedback()
            
            logger.info(f"📊 Найдено {len(feedback_data)} записей обратной связи")
            bot.send_message(
                message.chat.id, 
                f"📊 Найдено {len(feedback_data)} записей обратной связи"
            )
            
            # Формируем структуру, аналогичную той, что была при работе с PostgreSQL
            # для совместимости с кодом отчета
            for feedback in feedback_data:
                # Получаем информацию о пользователе
                user_id = feedback.get('user_id')
                timestamp = feedback.get('timestamp', datetime.now())
                rating = feedback.get('rating')
                comment = feedback.get('comment', '')
                
                # Создаем аналог записи Feedback для совместимости
                fb = type('Feedback', (), {
                    'rating': rating,
                    'comment': comment,
                    'timestamp': timestamp,
                    'user_id': user_id
                })
                
                # Получаем данные пользователя
                telegram_id = feedback.get('telegram_id', 0)
                username = feedback.get('username', 'unknown')
                first_name = feedback.get('first_name', 'Unknown')
                last_name = feedback.get('last_name', 'User')
                
                # Добавляем запись в список
                feedback_records.append((
                    fb,
                    telegram_id,
                    username,
                    first_name,
                    last_name
                ))
                
            # Отладочное сообщение
            logger.info(f"Получено и обработано {len(feedback_records)} записей обратной связи из Google Sheets")
            
        except Exception as sheets_error:
            error_msg = "❌ Ошибка при получении данных из Google Sheets"
            logger.error(f"{error_msg}: {str(sheets_error)}")
            
            # Сообщаем об ошибке пользователю
            bot.send_message(message.chat.id, error_msg)
            bot.send_message(message.chat.id, f"Детали ошибки: {str(sheets_error)}")
            
            # Создаем отчет без подключения
            create_empty_report(message.chat.id)
            return
        
        # Второй блок try - обработка полученных данных и формирование отчета
        try:
            if not feedback_records:
                # Отправляем сообщение с информацией при отсутствии данных
                bot.send_message(
                    message.chat.id, 
                    "📝 Данные обратной связи отсутствуют.\n\n"
                    "Обратная связь появится здесь, когда пользователи завершат диалоги "
                    "с ботом и оставят свои отзывы.\n\n"
                    "Вы можете добавить тестовые данные с помощью скрипта add_test_feedback.py."
                )
                return
            
            # Формируем отчет
            # Подсчитываем статистику рейтингов
            rating_counts = {"helpful": 0, "okay": 0, "not_helpful": 0}
            
            for record, _, _, _, _ in feedback_records:
                if record.rating in rating_counts:
                    rating_counts[record.rating] += 1
            
            # Отправляем отчет администратору
            report = "📊 *Отчет по обратной связи*\n\n"
            report += f"👍 Полезно: {rating_counts['helpful']}\n"
            report += f"🤔 Нормально: {rating_counts['okay']}\n"
            report += f"👎 Не полезно: {rating_counts['not_helpful']}\n\n"
            
            # Добавляем последние 5 комментариев с подробной информацией
            report += "*Последние комментарии:*\n"
            comment_count = 0
            
            for record, telegram_id, username, first_name, last_name in feedback_records:
                if record.comment:
                    comment_count += 1
                    
                    # Формируем имя пользователя для отображения
                    user_display = username or first_name or f"User {telegram_id}"
                    
                    # Преобразуем рейтинг в эмодзи
                    rating_emoji = {
                        "helpful": "👍",
                        "okay": "🤔",
                        "not_helpful": "👎"
                    }.get(record.rating, "❓")
                    
                    # Дата в формате ДД.ММ.ГГГГ
                    date_str = record.timestamp.strftime("%d.%m.%Y")
                    
                    # Экранируем специальные символы Markdown
                    comment = record.comment.replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")
                    
                    # Добавляем информацию о комментарии
                    report += f"{comment_count}. {rating_emoji} *{user_display}* ({date_str}):\n"
                    report += f"\"_{comment}_\"\n\n"
                    
                    if comment_count >= 5:
                        break
            
            if comment_count == 0:
                report += "_Комментариев пока нет._"
            
            # Общее количество отзывов
            total_feedback = sum(rating_counts.values())
            report += f"\n*Всего отзывов:* {total_feedback}"
            
            # Отправляем отчет с Markdown форматированием
            bot.send_message(
                message.chat.id, 
                report,
                parse_mode="Markdown"
            )
            
            # Сообщаем о создании Excel файла
            bot.send_message(
                message.chat.id,
                "📊 Создание Excel-отчета с полными данными..."
            )
            
            # Третий блок try - создание и отправка Excel файла
            try:
                # Проверяем, импортировали ли мы уже этот модуль
                if 'create_temp_excel_for_telegram' not in locals():
                    # Импортируем модуль для создания отчета
                    from sheets_excel_report import create_temp_excel_for_telegram
                
                # Генерируем файл отчета через Google Sheets
                excel_path, filename = create_temp_excel_for_telegram(sheets_manager)
                
                # Отправляем файл
                with open(excel_path, 'rb') as excel_file:
                    bot.send_document(
                        message.chat.id,
                        excel_file,
                        caption="📊 Полный отчет по обратной связи из Google Sheets"
                    )
                
                # Удаляем временный файл после отправки
                try:
                    os.remove(excel_path)
                    logger.info(f"Временный Excel-файл удален: {excel_path}")
                except Exception as e:
                    logger.warning(f"Не удалось удалить временный файл: {str(e)}")
                
                logger.info(f"Excel-отчет успешно отправлен: {filename}")
                
            except Exception as excel_error:
                logger.error(f"Ошибка при создании Excel-отчета: {str(excel_error)}")
                
                bot.send_message(
                    message.chat.id,
                    f"❌ Не удалось создать Excel-отчет: {str(excel_error)}"
                )
                
            # Отладочное сообщение для проверки, что мы дошли до этого места
            bot.send_message(
                message.chat.id,
                "✅ Отчёт по обратной связи сформирован успешно"
            )
            
        except Exception as e:
            error_msg = "❌ Ошибка при формировании отчета"
            logger.error(error_msg)
            # Закомментировано для безопасности на GitHub
            # import traceback
            # logger.error(traceback.format_exc())
            
            bot.send_message(message.chat.id, error_msg)
            
    except Exception:
        bot.send_message(
            message.chat.id, 
            "❌ Произошла ошибка при получении данных обратной связи. Проверьте подключение к базе данных."
        )
        logger.error("Error in admin_feedback function")

# Функция для создания пустого отчета при ошибке базы данных
def create_empty_report(chat_id):
    """
    Создает и отправляет пустой отчет по обратной связи при ошибке подключения к Google Sheets.
    
    Args:
        chat_id: ID чата для отправки отчета
    """
    try:
        # Отправляем статистический отчет с пустыми значениями
        logger.info("Создание пустого отчета из-за проблем с Google Sheets")
        
        # Текстовый отчет с информацией об ошибке
        report = "📊 *Отчет по обратной связи*\n\n"
        report += "⚠️ *Ошибка подключения к Google Sheets*\n\n"
        report += "Не удалось получить данные обратной связи из Google Sheets. "\
                "Пожалуйста, проверьте настройки и попробуйте снова.\n\n"
        report += "Возможные причины проблемы:\n"
        report += "- Отсутствуют или неверны переменные окружения для Google Sheets\n"
        report += "- Файл с учетными данными сервисного аккаунта отсутствует\n"
        report += "- Недостаточные права доступа к таблице\n"
        report += "- Проблемы с сетевым подключением\n\n"
        report += "Рекомендуется:\n"
        report += "- Проверить переменные окружения GOOGLE_CREDENTIALS_PATH и GOOGLE_SHEETS_KEY\n"
        report += "- Убедиться, что файл с учетными данными сервисного аккаунта существует\n"
        report += "- Проверить права доступа к таблице Google Sheets\n"
        
        # Отправляем отчет с форматированием Markdown
        bot.send_message(
            chat_id,
            report,
            parse_mode="Markdown"
        )
        
        # Создаем пустой Excel-отчет в случае ошибки
        try:
            import os
            import tempfile
            import xlsxwriter
            from datetime import datetime
            
            # Создаем временный файл
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            excel_path = os.path.join(tempfile.gettempdir(), f"feedback_report_empty_{timestamp}.xlsx")
            
            # Создаем Excel файл с информацией об ошибке
            workbook = xlsxwriter.Workbook(excel_path)
            worksheet = workbook.add_worksheet("Обратная связь")
            
            # Форматы для заголовков и текста
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D9EAD3',
                'border': 1,
                'align': 'center'
            })
            
            error_format = workbook.add_format({
                'bold': True,
                'fg_color': '#CC0000',
                'font_color': 'white',
                'align': 'center',
                'valign': 'vcenter'
            })
            
            # Заголовки
            headers = ["ID", "Пользователь", "Telegram ID", "Оценка", "Комментарий", "Дата"]
            for col_num, header in enumerate(headers):
                worksheet.write(0, col_num, header, header_format)
            
            # Сообщение об ошибке
            worksheet.merge_range('A2:F4', "ОШИБКА ПОДКЛЮЧЕНИЯ К GOOGLE SHEETS", error_format)
            
            # Устанавливаем ширину столбцов
            worksheet.set_column('A:A', 5)   # ID
            worksheet.set_column('B:B', 20)  # Пользователь
            worksheet.set_column('C:C', 15)  # Telegram ID
            worksheet.set_column('D:D', 10)  # Оценка
            worksheet.set_column('E:E', 40)  # Комментарий
            worksheet.set_column('F:F', 15)  # Дата
            
            workbook.close()
            
            # Отправляем файл
            with open(excel_path, 'rb') as excel_file:
                bot.send_document(
                    chat_id,
                    excel_file,
                    caption="📊 Отчет по обратной связи (пустой из-за ошибки Google Sheets)"
                )
            
            # Удаляем временный файл
            try:
                os.remove(excel_path)
            except:
                pass
                
        except Exception as excel_error:
            logger.error(f"Ошибка при создании пустого Excel-отчета: {str(excel_error)}")
            bot.send_message(
                chat_id,
                f"❌ Не удалось создать Excel-отчет: {str(excel_error)}"
            )
    
    except Exception as e:
        logger.error(f"Ошибка в функции create_empty_report: {str(e)}")
        bot.send_message(chat_id, f"❌ Ошибка при создании отчета: {str(e)}")


def main():
    """Запускает бота."""
    logger.info("Starting Language Mirror bot...")
    print("Bot is running! Press Ctrl+C to stop.")
    
    # Инициализируем user_sessions если необходимо
    global user_sessions, session_manager
    if 'session_manager' not in globals() and 'user_sessions' not in globals():
        logger.warning("No session manager available, initializing empty user_sessions")
        user_sessions = {}
    
    # Принудительно удаляем webhook перед запуском polling
    try:
        bot.remove_webhook()
        logger.info("Webhook removed successfully")
    except Exception:
        logger.error("Error removing webhook")
    
    # Добавляем паузу перед запуском polling
    import time
    time.sleep(1)
    
    # Запускаем бота с polling в non-threaded режиме с более строгими таймаутами
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception:
        logger.error("Error in polling")
        # При необходимости отладки раскомментируйте
        # import traceback
        # logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()