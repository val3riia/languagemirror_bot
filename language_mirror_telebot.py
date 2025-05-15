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
from datetime import datetime, date
from openrouter_client import OpenRouterClient
from sheets_excel_report import create_temp_excel_for_telegram

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

# Глобальные переменные для хранения менеджера сессий
session_manager = None
sheets_manager = None
user_sessions = {}

# Импортируем менеджер сессий с поддержкой Google Sheets
try:
    from sheets_session_manager import SheetSessionManager
    from sheets_manager import SheetsManager
    
    # Проверяем наличие необходимых переменных окружения
    google_creds_path = os.environ.get("GOOGLE_CREDENTIALS_PATH")
    google_sheets_key = os.environ.get("GOOGLE_SHEETS_KEY")
    google_service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    
    if google_sheets_key and (google_creds_path or google_service_account_json):
        try:
            # Импортируем функцию для получения готового экземпляра
            from sheets_manager import get_sheets_manager
            
            # Получаем готовый инициализированный экземпляр
            sheets_manager = get_sheets_manager()
            
            if sheets_manager:
                # Создаем экземпляр менеджера сессий
                session_manager = SheetSessionManager(sheets_mgr=sheets_manager)
                logger.info("Используется менеджер сессий с Google Sheets")
            else:
                # Если sheets_manager не инициализирован, используем словарь в памяти
                logger.warning("Не удалось инициализировать sheets_manager. Используются сессии в памяти")
        except Exception as e:
            logger.warning(f"Ошибка при получении экземпляра sheets_manager: {e}. Используются сессии в памяти")
    else:
        # Если переменные окружения не настроены, используем словарь в памяти
        logger.warning("GOOGLE_CREDENTIALS_PATH или GOOGLE_SHEETS_KEY не найдены. Используются сессии в памяти")
        
except Exception as e:
    logger.warning(f"Ошибка инициализации Google Sheets: {e}. Используются сессии в памяти")

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
    # Создаем инлайн-клавиатуру для выбора уровня сложности
    inline_markup = types.InlineKeyboardMarkup(row_width=2)
    
    # Добавляем кнопки уровней языка
    beginner_button = types.InlineKeyboardButton("A1 - Beginner", callback_data="level_A1")
    elementary_button = types.InlineKeyboardButton("A2 - Elementary", callback_data="level_A2")
    intermediate_button = types.InlineKeyboardButton("B1 - Intermediate", callback_data="level_B1")
    upper_button = types.InlineKeyboardButton("B2 - Upper Intermediate", callback_data="level_B2")
    advanced_button = types.InlineKeyboardButton("C1 - Advanced", callback_data="level_C1")
    proficient_button = types.InlineKeyboardButton("C2 - Proficient", callback_data="level_C2")
    
    # Добавляем кнопки на инлайн-клавиатуру
    inline_markup.add(beginner_button, elementary_button)
    inline_markup.add(intermediate_button, upper_button)
    inline_markup.add(advanced_button, proficient_button)
    user_id = message.from_user.id
    chat_id = message.chat.id
    username = message.from_user.username if hasattr(message.from_user, 'username') else ""
    
    logger.info(f"Обработка команды /discussion от пользователя {username} (ID: {user_id})")
    
    # Проверяем, есть ли у пользователя активная сессия
    active_session = False
    
    if session_manager:
        # Используем Google Sheets через session_manager
        try:
            session = session_manager.get_session(user_id)
            if session:
                active_session = True
                bot.send_message(
                    chat_id,
                    "Вы уже ведете обсуждение со мной. Продолжайте общение или используйте /stop_discussion, чтобы завершить текущую беседу."
                )
                logger.info(f"Пользователь {username} (ID: {user_id}) уже имеет активную сессию")
                return
        except Exception as e:
            logger.error(f"Ошибка при проверке сессии: {str(e)}")
    else:
        # Используем локальное хранилище
        if user_id in user_sessions:
            active_session = True
            bot.send_message(
                chat_id,
                "Вы уже ведете обсуждение со мной. Продолжайте общение или используйте /stop_discussion, чтобы завершить текущую беседу."
            )
            return
    
    # Если сессия не активна, проверяем лимиты на использование
    if not active_session:
        # Проверяем лимит на количество запросов в день
        from datetime import date
        today = date.today()
        
        # Проверка на администратора (им доступно неограниченное количество запросов)
        is_admin = False
        
        # Проверяем все возможные варианты
        if username and username.lower() in ADMIN_USERS:
            is_admin = True
            logger.info(f"Пользователь {username} (ID: {user_id}) авторизован как администратор")
        elif str(user_id) in ADMIN_USERS.values():
            is_admin = True
            logger.info(f"Пользователь с ID {user_id} авторизован как администратор")
        
        # Переменная today объявлена выше, а is_admin определена здесь - проблем быть не должно
        
        # Проверяем лимиты только для не-администраторов
        if not is_admin and session_manager and session_manager.sheets_manager:
            try:
                # Проверяем данные пользователя
                user_data = session_manager.sheets_manager.get_user_by_telegram_id(user_id)
                
                if user_data:
                    # Проверяем дату последнего обсуждения
                    if user_data.get('last_discussion_date') == str(today):
                        if user_data.get('discussions_count', 0) >= 3:
                            bot.send_message(
                                chat_id,
                                "Вы достигли лимита запросов на сегодня. Попробуйте завтра или оставьте обратную связь с помощью /feedback, чтобы получить бонусные запросы."
                            )
                            logger.info(f"Пользователь {username} (ID: {user_id}) достиг лимита запросов")
                            return
                else:
                    # Создаем нового пользователя
                    session_manager.sheets_manager.create_user(
                        telegram_id=user_id,
                        username=username or '',
                        first_name=message.from_user.first_name or '',
                        last_name=message.from_user.last_name or ''
                    )
                    logger.info(f"Создан новый пользователь: {username} (ID: {user_id})")
            except Exception as e:
                logger.error(f"Ошибка при проверке данных пользователя: {str(e)}")
                # В случае ошибки разрешаем доступ
                pass
    
    # Словарь уровней владения языком
    LANGUAGE_LEVELS = {
        'A1': 'Beginner',
        'A2': 'Elementary',
        'B1': 'Intermediate',
        'B2': 'Upper Intermediate',
        'C1': 'Advanced',
        'C2': 'Proficient'
    }
    
    # Отправляем сообщение с выбором уровня языка, используя инлайн-клавиатуру, созданную выше
    bot.send_message(
        chat_id,
        "Пожалуйста, выберите ваш уровень владения английским языком:",
        reply_markup=inline_markup
    )
    
    # Если у нас есть менеджер сессий и пользователь не является администратором
    # Обновляем статистику использования
    # is_admin объявлен выше, today объявлен в этой же функции
    from datetime import date  # Повторно импортируем для гарантии
    the_today = date.today()  # Используем другую переменную для устранения предупреждения
    the_is_admin = False  # Инициализируем переменную повторно для устранения предупреждения
    
    # Проверяем значение is_admin, объявленное выше
    try:
        the_is_admin = is_admin
    except NameError:
        # Если переменная не объявлена, используем значение по умолчанию
        the_is_admin = False
    
    if session_manager and session_manager.sheets_manager and not the_is_admin:
        try:
            # Обновляем статистику использования в Google Sheets
            session_manager.sheets_manager.update_user_discussion_stats(
                telegram_id=user_id,
                date=str(the_today)
            )
            logger.info(f"Статистика пользователя {username} (ID: {user_id}) обновлена")
        except Exception as e:
            logger.error(f"Ошибка при обновлении статистики: {str(e)}")
    
    # Отправляем сообщение с выбором уровня языка
    bot.send_message(
        chat_id,
        "Прежде чем начать, я хотел бы узнать ваш уровень владения английским языком, "
        "чтобы адаптировать свои ответы к вашим потребностям. Пожалуйста, выберите ваш уровень:",
        reply_markup=markup
    )
    logger.info(f"Пользователю {username} (ID: {user_id}) предложен выбор уровня языка")

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
    if session_manager is not None:
        # Используем менеджер сессий с Google Sheets
        try:
            session_manager.create_session(user_id, user_info)
        except Exception as e:
            logger.error(f"Ошибка при создании сессии в session_manager: {e}")
            # В случае ошибки создаем сессию в памяти
            user_sessions[user_id] = {
                "language_level": level,
                "messages": [],
                "last_active": time.time(),
                "mode": "articles"
            }
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
    
    if session_manager is not None:
        try:
            session = session_manager.get_session(user_id)
            if session:
                session_exists = True
        except Exception as e:
            logger.error(f"Ошибка при получении сессии пользователя: {e}")
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
    bonus_available = False
    
    # Проверяем, доступен ли Google Sheets
    try:
        from sheets_manager import get_sheets_manager
        sheets_manager = get_sheets_manager()
        
        if sheets_manager:
            # Получаем пользователя
            sheet_user = sheets_manager.get_user_by_telegram_id(user_id)
            
            if sheet_user:
                # Проверяем, использовал ли пользователь бонус
                bonus_available = not sheet_user.get("feedback_bonus_used", False)
                
                if bonus_available:
                    # Обновляем данные пользователя
                    sheets_manager.update_user(sheet_user["id"], {
                        "feedback_bonus_used": True
                    })
                    logger.info(f"Бонус за обратную связь активирован для пользователя {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при проверке и обновлении бонуса: {e}")
            
    # Показываем клавиатуру выбора уровня языка
    if bonus_available:
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
    try:
        from sheets_session_manager import get_session_manager
        session_manager = get_session_manager()
        
        if session_manager:
            # Завершаем сессию в базе данных, но сохраняем информацию о feedback
            session = session_manager.get_session(user_id)
            if session:
                session_manager.end_session(user_id)
            
            # Создаем временную сессию только для хранения типа обратной связи
            session_manager.create_session(user_id, {"feedback_type": feedback_type})
            logger.info(f"Создана временная сессия для хранения обратной связи типа: {feedback_type}")
        else:
            # В случае недоступности Google Sheets используем локальное хранилище
            if user_id in user_sessions:
                user_sessions[user_id]["feedback_type"] = feedback_type
                # Очищаем сессию (сохраняем только feedback_type)
                user_sessions[user_id] = {
                    "feedback_type": feedback_type,
                    "last_active": time.time()
                }
                logger.info(f"Информация о feedback сохранена в локальном хранилище: {feedback_type}")
    except Exception as e:
        # В случае ошибки используем локальное хранилище
        logger.error(f"Ошибка при работе с session_manager: {e}")
        if user_id in user_sessions:
            user_sessions[user_id]["feedback_type"] = feedback_type
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
    
    # Минимальное количество слов для получения бонуса
    min_words_for_bonus = 3
    
    if comment.lower() == "/skip":
        bot.send_message(
            message.chat.id,
            "Thanks again for your feedback! Use /discussion anytime you want to practice English."
        )
        
        # Завершаем сессию
        if session_manager is not None:
            try:
                session_manager.end_session(user_id)
            except Exception as e:
                logger.error(f"Ошибка при завершении сессии: {e}")
        elif user_id in user_sessions:
            del user_sessions[user_id]
            
        return
    
    # Получаем тип обратной связи из временного хранилища
    feedback_type = "unknown"
    
    if session_manager is not None:
        try:
            session = session_manager.get_session(user_id)
            if session and "feedback_type" in session:
                feedback_type = session["feedback_type"]
        except Exception as e:
            logger.error(f"Ошибка при получении сессии для обратной связи: {e}")
    elif user_id in user_sessions and "feedback_type" in user_sessions[user_id]:
        feedback_type = user_sessions[user_id]["feedback_type"]
    
    rating_map = {
        "helpful": "👍 Helpful",
        "okay": "🤔 Okay",
        "not_helpful": "👎 Not helpful",
        "unknown": "Rating not provided"
    }
    
    # Сохраняем обратную связь в Google Sheets
    try:
        # Минимальное количество слов для бонуса
        min_words_for_bonus = int(os.environ.get("FEEDBACK_COMMENT_MIN_WORDS", "3"))
        
        # Получаем информацию о пользователе
        username = message.from_user.username or ""
        first_name = message.from_user.first_name or ""
        last_name = message.from_user.last_name or ""
        
        # Сохраняем обратную связь в Google Sheets
        if 'sheets_manager' in globals() and sheets_manager:
            # Выполняем в отдельном потоке, чтобы не блокировать бота
            def save_to_sheets():
                try:
                    # Получаем пользователя или создаем нового
                    from sheets_manager import get_sheets_manager
                    sheets_manager = get_sheets_manager()
                    
                    if sheets_manager:
                        # Получаем пользователя или создаем нового
                        sheet_user = sheets_manager.get_user_by_telegram_id(user_id)
                        if not sheet_user:
                            sheet_user = sheets_manager.create_user(
                                telegram_id=user_id,
                                username=username,
                                first_name=first_name,
                                last_name=last_name
                            )
                            
                        # Преобразуем rating в числовую оценку
                        rating_value = {
                            "helpful": 5,
                            "okay": 3,
                            "not_helpful": 1,
                            "unknown": 3
                        }.get(feedback_type, 3)
                        
                        # Добавляем запись обратной связи в Google Sheets
                        sheets_manager.add_feedback(
                            user_id=sheet_user["id"],
                            rating=rating_value,
                            comment=comment
                        )
                    
                    # Минимальное количество слов для получения бонуса
                    min_words_for_bonus = 3
                    
                    # Проверяем, содержит ли комментарий минимум слов для предоставления бонуса
                    words = comment.split()
                    logger.info(f"Комментарий содержит {len(words)} слов (минимум для бонуса: {min_words_for_bonus})")
                    
                    if len(words) >= min_words_for_bonus:
                        # Обновляем статус обратной связи пользователя, предоставляя бонус
                        sheets_manager.set_feedback_bonus_used(user_id, False)  # Разрешаем использовать бонусный запрос
                        
                        # Проверяем, что sheets_manager существует перед вызовом его методов
                        try:
                            if sheets_manager:
                                sheets_manager.set_feedback_bonus_used(user_id, False)  # Разрешаем использовать бонусный запрос
                        except Exception as e:
                            logger.error(f"Ошибка при установке бонуса: {e}")
                            
                        # Отправляем уведомление о бонусном запросе
                        bot.send_message(
                            user_id,
                            "🎁 Thank you for your detailed feedback! You've received a bonus article request. "
                            "Use /discussion to use it anytime today!"
                        )
                        return True
                    else:
                        bot.send_message(
                            user_id,
                            "Thank you for your feedback! For more detailed comments (at least 3 words) "
                            "you can receive bonus article requests in the future."
                        )
                        return False
                except Exception as e:
                    logger.error(f"Ошибка при сохранении обратной связи в Google Sheets: {str(e)}")
                    return False
            
            # Запускаем функцию сохранения в отдельном потоке
            threading.Thread(target=save_to_sheets, daemon=True).start()
        else:
            # Если Google Sheets недоступен, сохраняем только в логи
            logger.warning(f"Google Sheets недоступен, обратная связь только логируется: {user_id}, {feedback_type}, {comment}")
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
    if session_manager is not None:
        try:
            session_manager.end_session(user_id)
        except Exception as e:
            logger.error(f"Ошибка при завершении сессии после обратной связи: {e}")
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
– a short, thoughtful reply (2-3 sentences maximum);
– if needed, explain 1 useful word or phrase (briefly, like a real person would do);
– if appropriate, ask a follow-up question to keep the conversation flowing;
– do NOT give long essays, walls of text, or summaries;
– do NOT include links unless explicitly asked;
– do NOT talk like a tutor. You're a peer who speaks great English and helps naturally;
– be casual, warm, conversational, and clear — not scripted.

How to explain words (Word Card Format):
When you explain or introduce a new word, use this format:
- Part of speech
- Definition
- Example (in the same context as the user's)
- Synonyms with: preposition + something/somebody + part of speech + connotation
- Common collocations
- Connotation (semantic or emotional weight)

If a phrase sounds unnatural, explain why and offer real alternatives in this format:

⚠️ Sounds off?

❌ [original user sentence]
→ [explanation why it sounds unnatural]
✅ Instead:
• [natural option 1]
• [natural option 2]

Important guidelines:
• Always keep responses brief and conversational (max 3-4 sentences)
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
    
    if session_manager is not None:
        # Проверка через менеджер сессий с Google Sheets
        try:
            session = session_manager.get_session(user_id)
            if session and "language_level" in session:
                session_exists = True
                language_level = session.get("language_level", "B1")
                session_mode = session.get("mode", "conversation")
        except Exception as e:
            logger.error(f"Ошибка при получении сессии из session_manager: {e}")
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
    if session_manager is not None:
        try:
            session_manager.add_message_to_session(user_id, "user", user_message)
        except Exception as e:
            logger.error(f"Ошибка при добавлении сообщения в сессию: {e}")
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
        if session_manager is not None:
            try:
                session_manager.end_session(user_id)
            except Exception as e:
                logger.error(f"Ошибка при завершении сессии в session_manager: {e}")
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
        if session_manager is not None:
            try:
                conversation_history = session_manager.get_messages(user_id)
            except Exception as e:
                logger.error(f"Ошибка при получении сообщений из session_manager: {e}")
        elif user_id in user_sessions and "messages" in user_sessions[user_id]:
            conversation_history = user_sessions[user_id]["messages"]
        
        # Генерируем ответ на основе сообщения пользователя и истории
        response = generate_learning_response(user_message, language_level, conversation_history)
        
        # Сохраняем ответ бота в сессии
        if session_manager is not None:
            try:
                session_manager.add_message_to_session(user_id, "assistant", response)
            except Exception as e:
                logger.error(f"Ошибка при добавлении сообщения в session_manager: {e}")
                # В случае ошибки пытаемся использовать резервный способ хранения
                if user_id in user_sessions and "messages" in user_sessions[user_id]:
                    user_sessions[user_id]["messages"].append({"role": "assistant", "content": response})
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
                credentials_path=google_creds_path, 
                spreadsheet_key=google_sheets_key
            )
            
            # Получаем данные обратной связи
            feedback_data = sheets_manager.get_all_feedback()
            
            logger.info(f"📊 Найдено {len(feedback_data)} записей обратной связи")
            bot.send_message(
                message.chat.id, 
                f"📊 Найдено {len(feedback_data)} записей обратной связи"
            )
            
            # Адаптируем структуру данных из Google Sheets для работы с существующим кодом отчета
            for feedback in feedback_data:
                # Получаем необходимые данные
                telegram_id = feedback.get('telegram_id', '0')
                try:
                    telegram_id = int(telegram_id)
                except ValueError:
                    telegram_id = 0
                    
                username = feedback.get('username', '')
                first_name = feedback.get('first_name', '')
                last_name = feedback.get('last_name', '')
                
                # Значения по умолчанию для обязательных полей
                rating = feedback.get('rating', 'unknown')
                comment = feedback.get('comment', '')
                
                # Обрабатываем временную метку, которая может быть строкой
                created_at = feedback.get('created_at', '')
                try:
                    if created_at:
                        timestamp = datetime.fromisoformat(created_at)
                    else:
                        timestamp = datetime.now()
                except (ValueError, TypeError):
                    timestamp = datetime.now()
                
                # Создаем объект Feedback для совместимости со старым кодом
                fb = type('Feedback', (), {
                    'rating': rating,
                    'comment': comment,
                    'timestamp': timestamp,
                    'user_id': telegram_id  # Используем telegram_id вместо user_id
                })
                
                # Добавляем запись в список
                feedback_records.append((
                    fb,
                    telegram_id,
                    username or 'unknown',
                    first_name or 'Unknown',
                    last_name or 'User'
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
                
                # Преобразуем данные в формат для Excel
                excel_data = []
                for record, telegram_id, username, first_name, last_name in feedback_records:
                    # Создаем запись для Excel
                    excel_record = {
                        "Telegram ID": telegram_id,
                        "Username": username,
                        "First Name": first_name,
                        "Last Name": last_name,
                        "Rating": record.rating,
                        "Comment": record.comment,
                        "Date": record.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    excel_data.append(excel_record)
                
                # Генерируем файл отчета
                excel_path = create_temp_excel_for_telegram(excel_data, "feedback_report.xlsx")
                
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
                
                logger.info("Excel-отчет успешно отправлен")
                
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
        bot.send_message(
            chat_id,
            "📝 Создание пустого отчета, так как не удалось подключиться к базе данных."
        )
        
        # Создаем пустой Excel-файл
        empty_data = [{
            "Информация": "Нет данных обратной связи",
            "Причина": "Ошибка подключения к Google Sheets"
        }]
        
        # Генерируем временный файл
        excel_path = create_temp_excel_for_telegram(empty_data, "empty_report.xlsx")
        
        # Отправляем файл
        with open(excel_path, 'rb') as excel_file:
            bot.send_document(
                chat_id,
                excel_file,
                caption="📊 Пустой отчет (нет данных)"
            )
        
        # Удаляем временный файл
        try:
            os.remove(excel_path)
        except Exception as e:
            logger.error(f"Не удалось удалить временный файл: {str(e)}")
            
    except Exception as e:
        logger.error(f"Ошибка при создании пустого отчета: {str(e)}")
        bot.send_message(
            chat_id,
            f"❌ Ошибка при создании отчета: {str(e)}"
        )
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
        logger.info("Starting bot polling with none_stop=True...")
        
        # Проверяем настройки сессий перед запуском
        if session_manager is not None:
            logger.info("Using session_manager for bot")
        else:
            logger.info(f"Using user_sessions dictionary for bot, contains {len(user_sessions)} sessions")
        
        # Запускаем бота с улучшенной обработкой ошибок
        def polling_thread():
            try:
                bot.polling(none_stop=True, interval=2, timeout=60)
            except Exception as e:
                logger.error(f"Error in polling thread: {str(e)}")
                import traceback
                error_trace = traceback.format_exc()
                logger.error(f"Polling thread traceback: {error_trace}")
                
        # Запускаем в отдельном потоке, чтобы не блокировать основной поток
        polling_worker = threading.Thread(target=polling_thread, daemon=True)
        polling_worker.start()
        logger.info("Bot polling thread started successfully")
        return polling_worker
    except Exception as e:
        logger.error(f"Error setting up polling: {str(e)}")
        # Подробный лог ошибки для отладки
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Traceback: {error_trace}")
        return None

if __name__ == "__main__":
    main()