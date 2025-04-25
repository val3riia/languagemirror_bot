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
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

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
ADMIN_USERS = {
    "your_admin_username": 0  # Замените на реальное имя пользователя и ID
}

# Отладочный режим для отображения дополнительной информации об ошибках
DEBUG_MODE = os.environ.get("DEBUG_MODE", "True").lower() in ("true", "1", "yes")

# Фиксированный ID администратора для тестирования
# При любой проверке администратора данный ID будет автоматически считаться администратором
# Это нужно для отладки команды /admin_feedback
FORCE_ADMIN_ID = int(os.environ.get("ADMIN_TELEGRAM_ID", "0"))

# Уровни владения языком с описаниями
LANGUAGE_LEVELS = {
    "A1": "Beginner - You're just starting with English",
    "A2": "Elementary - You can use simple phrases and sentences",
    "B1": "Intermediate - You can discuss familiar topics",
    "B2": "Upper Intermediate - You can interact with fluency",
    "C1": "Advanced - You can express yourself fluently and spontaneously",
    "C2": "Proficiency - You can understand virtually everything heard or read"
}

# Лимит запросов в день по умолчанию
DEFAULT_DAILY_LIMIT = 1

# Формат системного запроса к языковой модели в виде файла-шаблона
try:
    from openrouter_client import OpenRouterClient
    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
    openrouter_client = OpenRouterClient(api_key=OPENROUTER_API_KEY) if OPENROUTER_API_KEY else None
except (ImportError, Exception) as e:
    logger.error(f"Failed to initialize OpenRouter client: {e}")
    openrouter_client = None

# Функция безопасного получения текста системного запроса из файла
def get_system_prompt(language_level="B1"):
    try:
        # Путь к файлу с системным запросом
        prompt_file = "attached_assets/Pasted-System-Prompt-natural-phrasing-AI--1745557433318.txt"
        
        # Проверяем существование файла
        if not os.path.exists(prompt_file):
            logger.warning(f"System prompt file not found: {prompt_file}")
            return f"You are a friendly language coach for {language_level} level English. Keep responses concise and use natural conversation style."
        
        # Читаем содержимое файла
        with open(prompt_file, "r", encoding="utf-8") as file:
            prompt_template = file.read()
            
        # Вставляем уровень языка в шаблон
        prompt = prompt_template.replace("{language_level}", language_level)
        return prompt
    except Exception as e:
        logger.error(f"Error reading system prompt file: {e}")
        return f"You are a friendly language coach for {language_level} level English. Keep responses concise and use natural conversation style."

# Хранилище пользовательских сессий
user_sessions = {}

# Выбираем менеджер сессий
try:
    # Пробуем импортировать менеджер сессий базы данных
    from db_session_manager import DatabaseSessionManager
    from flask import Flask
    from main import app
    
    # Создаем экземпляр менеджера сессий с существующим приложением Flask
    session_manager = DatabaseSessionManager(app)
    logger.info("Using database session manager")
except ImportError:
    # Если импорт не удался, используем сессии в памяти
    from session_manager import SessionManager
    session_manager = SessionManager()
    logger.warning("Using in-memory session manager (no database)")
except Exception as e:
    # В случае любой другой ошибки, выводим предупреждение и используем сессии в памяти
    logger.error(f"Error initializing database session manager: {e}")
    try:
        from session_manager import SessionManager
        session_manager = SessionManager()
        logger.warning("Using in-memory session manager due to database error")
    except ImportError:
        logger.error("Session manager not available!")
        session_manager = None

# Отдельный поток для очистки устаревших сессий
def cleanup_thread():
    """Поток для периодической очистки устаревших сессий."""
    while True:
        try:
            if hasattr(session_manager, 'clean_expired_sessions'):
                session_manager.clean_expired_sessions()
                logger.debug("Cleaned expired sessions")
        except Exception as e:
            logger.error(f"Error in cleanup thread: {e}")
        
        # Ждем 10 минут перед следующей очисткой
        time.sleep(600)

# Запускаем поток очистки
cleanup_thread_instance = threading.Thread(target=cleanup_thread, daemon=True)
cleanup_thread_instance.start()

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Обрабатывает команду /start."""
    user_id = message.from_user.id
    
    try:
        # Создаем новую сессию для пользователя
        if session_manager:
            session_manager.create_session(user_id)
        
        # Создаем клавиатуру
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        btn_discussion = types.KeyboardButton('💬 Discussion')
        
        # Добавляем кнопки
        markup.add(btn_discussion)
        
        # Отправляем приветственное сообщение
        welcome_message = (
            "👋 Welcome to Language Mirror Bot!\n\n"
            "I'm here to help you practice and improve your English through natural conversations.\n\n"
            "You can:\n"
            "• Start a discussion with me on any topic (/discussion)\n"
            "• Tell me your interests and I'll suggest relevant articles\n"
            "• Practice your language skills at your own pace\n\n"
            "Let's get started! Click the Discussion button or type /discussion to begin."
        )
        
        bot.send_message(message.chat.id, welcome_message, reply_markup=markup)
        
    except Exception as e:
        logger.error(f"Error in handle_start: {e}")
        error_message = "Sorry, an error occurred. Please try again or contact support."
        bot.reply_to(message, error_message)

@bot.message_handler(commands=['discussion'])
def handle_discussion(message):
    """Обрабатывает команду /discussion."""
    user_id = message.from_user.id
    
    try:
        # Проверка ограничения на количество запросов в день
        # Администраторы могут использовать бота без ограничений
        username = message.from_user.username if hasattr(message.from_user, 'username') else None
        is_admin = (username == "your_admin_username" or user_id == ADMIN_USERS.get("your_admin_username"))
        
        # Если пользователь не админ, проверяем лимит запросов
        if not is_admin:
            # Получаем текущую сессию
            session = session_manager.get_session(user_id) if session_manager else {}
            
            # Проверяем, не израсходован ли лимит на сегодня
            today = datetime.now().strftime("%Y-%m-%d")
            session_today = session.get("last_discussion_date", "") == today
            discussions_today = session.get("discussions_today", 0) if session_today else 0
            
            # Проверка на бонусные запросы за обратную связь
            bonus_requests = session.get("bonus_requests", 0)
            
            # Если лимит исчерпан и нет бонусных запросов
            if discussions_today >= DEFAULT_DAILY_LIMIT and bonus_requests <= 0:
                limit_message = (
                    "⚠️ You've reached your daily limit of discussion requests.\n\n"
                    "Each user can start 1 discussion per day. You can get bonus "
                    "discussion requests by providing feedback after your conversations!\n\n"
                    "Come back tomorrow for more learning."
                )
                bot.reply_to(message, limit_message)
                return
        
        # Создаем клавиатуру для выбора уровня владения языком
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        # Добавляем кнопки для каждого уровня
        for level, description in LANGUAGE_LEVELS.items():
            btn = types.InlineKeyboardButton(text=f"{level} - {description.split(' - ')[0]}", 
                                            callback_data=f"level_{level}")
            markup.add(btn)
        
        # Отправляем сообщение с просьбой выбрать уровень
        level_message = (
            "👩‍🏫 Please select your English proficiency level:\n\n"
            "This helps me adapt my language to your needs."
        )
        
        bot.send_message(message.chat.id, level_message, reply_markup=markup)
        
    except Exception as e:
        logger.error(f"Error in handle_discussion: {e}")
        error_message = "Sorry, an error occurred. Please try again or contact support."
        bot.reply_to(message, error_message)

@bot.callback_query_handler(func=lambda call: call.data.startswith('level_'))
def handle_language_level(call):
    """Обрабатывает выбор уровня владения языком."""
    try:
        # Получаем выбранный уровень из callback_data
        level = call.data.split('_')[1]
        user_id = call.from_user.id
        
        # Записываем уровень в сессию пользователя
        if session_manager:
            session = session_manager.get_session(user_id) or {}
            session["language_level"] = level
            
            # Обновляем счетчик дискуссий
            today = datetime.now().strftime("%Y-%m-%d")
            session_today = session.get("last_discussion_date", "") == today
            discussions_today = session.get("discussions_today", 0) if session_today else 0
            
            # Проверка на бонусные запросы за обратную связь
            bonus_requests = session.get("bonus_requests", 0)
            
            # Если у пользователя есть бонусные запросы, используем их
            if discussions_today >= DEFAULT_DAILY_LIMIT and bonus_requests > 0:
                bonus_requests -= 1
                session["bonus_requests"] = bonus_requests
            else:
                # Увеличиваем счетчик дискуссий на сегодня
                session["discussions_today"] = discussions_today + 1
                session["last_discussion_date"] = today
            
            session_manager.update_session(user_id, session)
        
        # Отправляем сообщение о выборе уровня и запрашиваем тему для обсуждения
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"✅ Language level set to {level}."
        )
        
        # Запрашиваем у пользователя тему для обсуждения
        topic_message = (
            "🔍 What topic would you like to discuss or learn about?\n\n"
            "For example:\n"
            "• Travel to Spain\n"
            "• Business negotiations\n"
            "• Climate change\n"
            "• Technology trends\n\n"
            "Just type your topic of interest!"
        )
        
        # Сохраняем, что бот ожидает тему от пользователя
        if session_manager:
            session = session_manager.get_session(user_id) or {}
            session["state"] = "waiting_for_topic"
            session_manager.update_session(user_id, session)
        
        bot.send_message(call.message.chat.id, topic_message)
        
    except Exception as e:
        logger.error(f"Error in handle_language_level: {e}")
        error_message = "Sorry, an error occurred. Please try again or contact support."
        bot.send_message(call.message.chat.id, error_message)

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
        if not openrouter_client:
            return default_articles_for_topic(topic)
        
        # Формируем запрос к AI для генерации списка статей
        prompt = f"""
        Generate 3 article suggestions for an English learner at {language_level} level interested in the topic: "{topic}".
        
        For each article, provide:
        1. A title that matches the topic and language level
        2. A realistic URL (can be fictional but should look realistic)
        3. A brief 1-sentence description
        
        Format your response as JSON with this exact structure:
        ```json
        [
            {{
                "title": "Article Title 1",
                "url": "https://example.com/article-1",
                "description": "Brief description of article 1."
            }},
            {{
                "title": "Article Title 2",
                "url": "https://example.com/article-2",
                "description": "Brief description of article 2."
            }},
            {{
                "title": "Article Title 3",
                "url": "https://example.com/article-3",
                "description": "Brief description of article 3."
            }}
        ]
        ```
        
        Ensure the content is appropriate for a {language_level} level English learner interested in "{topic}".
        """
        
        # Отправляем запрос к OpenRouter API
        response = openrouter_client.chat_completion(
            model="openai/gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800
        )
        
        # Получаем ответ и парсим JSON
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Извлекаем JSON из ответа, если он обернут в кодовые блоки
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        # Парсим JSON-ответ
        articles = json.loads(content)
        
        # Проверяем формат ответа
        if not isinstance(articles, list) or len(articles) == 0:
            return default_articles_for_topic(topic)
            
        return articles
        
    except Exception as e:
        logger.error(f"Error finding articles by topic: {e}")
        return default_articles_for_topic(topic)

def default_articles_for_topic(topic: str) -> list:
    """
    Создает стандартный набор статей по теме при недоступности API.
    
    Args:
        topic: Тема для статей
        
    Returns:
        Список словарей с информацией о статьях
    """
    safe_topic = topic.replace(" ", "-").lower()
    
    return [
        {
            "title": f"Introduction to {topic.title()}",
            "url": f"https://learnenglish.example.com/{safe_topic}-introduction",
            "description": f"A beginner's guide to understanding {topic}."
        },
        {
            "title": f"{topic.title()}: Key Concepts Explained",
            "url": f"https://englishlearning.example.org/concepts/{safe_topic}",
            "description": f"Learn the essential vocabulary and concepts related to {topic}."
        },
        {
            "title": f"Practical Guide to {topic.title()}",
            "url": f"https://english-practice.example.net/guides/{safe_topic}",
            "description": f"Practice your English skills while learning about {topic}."
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
    try:
        # Проверяем доступность клиента OpenRouter
        if not openrouter_client:
            # Если клиент недоступен, используем заглушку
            responses = [
                f"That's an interesting point about {user_message.split()[0] if user_message else 'that'}! Can you tell me more?",
                "I understand what you're saying. How do you feel about this topic?",
                "That's a great perspective! Can you elaborate on that?",
                "I see what you mean. What aspects of this topic interest you the most?",
                "Thank you for sharing that. What else would you like to discuss about this topic?"
            ]
            return random.choice(responses)
        
        # Готовим системный запрос с учетом уровня языка
        system_prompt = get_system_prompt(language_level)
        
        # Формируем список сообщений
        messages = [{"role": "system", "content": system_prompt}]
        
        # Добавляем историю разговора, если она предоставлена
        if conversation_history:
            messages.extend(conversation_history)
        
        # Добавляем текущее сообщение пользователя
        messages.append({"role": "user", "content": user_message})
        
        # Отправляем запрос на OpenRouter API
        response = openrouter_client.chat_completion(
            model="openai/gpt-4o-mini",
            messages=messages,
            max_tokens=600,
            temperature=0.7
        )
        
        # Получаем ответ
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        if not content:
            # Если ответ пустой, используем заглушку
            return "I'm thinking about what you said. Could you tell me more about your thoughts on this topic?"
        
        return content
        
    except Exception as e:
        logger.error(f"Error generating learning response: {e}")
        # В случае ошибки возвращаем общий ответ
        return "I'm having trouble processing that right now. Let's try a different aspect of this topic or try again later. What else interests you about this subject?"

@bot.message_handler(func=lambda message: session_manager.get_session(message.from_user.id).get("state") == "waiting_for_topic" if session_manager and session_manager.get_session(message.from_user.id) else False)
def handle_topic_selection(message):
    """Обрабатывает выбор темы пользователем."""
    try:
        user_id = message.from_user.id
        topic = message.text.strip()
        
        # Получаем сессию пользователя
        session = session_manager.get_session(user_id) if session_manager else {}
        language_level = session.get("language_level", "B1")
        
        # Проверяем, что тема не пустая
        if not topic:
            bot.reply_to(message, "Please enter a valid topic for discussion.")
            return
        
        # Отправляем сообщение о поиске статей
        search_message = bot.send_message(
            message.chat.id, 
            "🔍 Searching for relevant articles on this topic..."
        )
        
        # Поиск статей по теме
        articles = find_articles_by_topic(topic, language_level)
        
        # Сохраняем тему и статьи в сессии
        if session_manager:
            session["topic"] = topic
            session["articles"] = articles
            session["state"] = "in_discussion"
            session_manager.update_session(user_id, session)
        
        # Формируем сообщение со списком статей
        articles_message = f"📚 I've found these articles about \"{topic}\" for your {language_level} level:\n\n"
        
        for i, article in enumerate(articles, 1):
            articles_message += f"{i}. [{article['title']}]({article['url']})\n"
            if 'description' in article:
                articles_message += f"   _{article['description']}_\n\n"
        
        articles_message += "\nNow let's discuss this topic! What aspects of it interest you the most?"
        
        # Обновляем сообщение о поиске
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=search_message.message_id,
            text=articles_message,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        
        # Создаем клавиатуру для остановки обсуждения
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        btn_stop = types.KeyboardButton('⏹️ Stop Discussion')
        markup.add(btn_stop)
        
        # Отправляем приглашение к обсуждению
        discussion_message = (
            f"Let's talk about {topic}!\n\n"
            f"I'll adapt my language to your {language_level} level.\n"
            "You can ask questions, share your thoughts, or request explanations.\n\n"
            "When you're done, click the 'Stop Discussion' button or type /stop_discussion."
        )
        
        bot.send_message(
            message.chat.id,
            discussion_message,
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"Error in handle_topic_selection: {e}")
        error_message = "Sorry, an error occurred while processing your topic. Please try again or select a different topic."
        bot.reply_to(message, error_message)

@bot.message_handler(commands=['stop_discussion'])
def handle_stop_discussion(message):
    """Обрабатывает команду /stop_discussion."""
    try:
        user_id = message.from_user.id
        
        # Получаем сессию пользователя
        session = session_manager.get_session(user_id) if session_manager else {}
        
        # Проверяем, что пользователь находится в обсуждении
        if not session or session.get("state") != "in_discussion":
            bot.reply_to(
                message, 
                "You don't have an active discussion. Use /discussion to start one!"
            )
            return
        
        # Получаем тему обсуждения
        topic = session.get("topic", "the topic")
        
        # Обновляем состояние пользователя
        if session_manager:
            session["state"] = "waiting_for_feedback"
            session_manager.update_session(user_id, session)
        
        # Создаем клавиатуру для оценки
        markup = types.InlineKeyboardMarkup(row_width=3)
        btn_helpful = types.InlineKeyboardButton(text="👍 Helpful", callback_data="feedback_helpful")
        btn_okay = types.InlineKeyboardButton(text="🤔 Okay", callback_data="feedback_okay")
        btn_not_helpful = types.InlineKeyboardButton(text="👎 Not Helpful", callback_data="feedback_not_helpful")
        markup.add(btn_helpful, btn_okay, btn_not_helpful)
        
        # Отправляем сообщение с запросом обратной связи
        feedback_message = (
            f"Thanks for discussing {topic} with me! I hope it was helpful for your language learning.\n\n"
            "Could you please rate our conversation?"
        )
        
        bot.send_message(
            message.chat.id,
            feedback_message,
            reply_markup=markup
        )
        
        # Возвращаем основную клавиатуру
        main_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        btn_discussion = types.KeyboardButton('💬 Discussion')
        main_markup.add(btn_discussion)
        
        bot.send_message(
            message.chat.id,
            "You can start a new discussion when you're ready!",
            reply_markup=main_markup
        )
        
    except Exception as e:
        logger.error(f"Error in handle_stop_discussion: {e}")
        error_message = "Sorry, an error occurred. Please try again."
        bot.reply_to(message, error_message)

@bot.callback_query_handler(func=lambda call: call.data.startswith('feedback_'))
def handle_feedback(call):
    """Обрабатывает обратную связь пользователя."""
    try:
        # Получаем тип обратной связи
        feedback_type = call.data.split('_')[1]
        user_id = call.from_user.id
        
        # Получаем сессию пользователя
        session = session_manager.get_session(user_id) if session_manager else {}
        
        # Проверяем, что пользователь ожидает отправки обратной связи
        if not session or session.get("state") != "waiting_for_feedback":
            bot.answer_callback_query(call.id, "This feedback option is no longer available.")
            return
        
        # Сохраняем тип обратной связи в сессии
        if session_manager:
            session["feedback_type"] = feedback_type
            session["state"] = "waiting_for_feedback_comment"
            session_manager.update_session(user_id, session)
        
        # Обновляем сообщение с благодарностью
        feedback_display = {
            "helpful": "👍 Helpful",
            "okay": "🤔 Okay",
            "not_helpful": "👎 Not Helpful"
        }.get(feedback_type, feedback_type)
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"Thank you for your feedback: {feedback_display}"
        )
        
        # Спрашиваем о дополнительных комментариях
        comment_message = (
            "Do you have any specific comments about our conversation?\n\n"
            "Your feedback helps me improve! Please provide a few words of feedback "
            "to receive a bonus discussion request."
        )
        
        bot.send_message(call.message.chat.id, comment_message)
        
    except Exception as e:
        logger.error(f"Error in handle_feedback: {e}")
        error_message = "Sorry, an error occurred while processing your feedback."
        bot.send_message(call.message.chat.id, error_message)

@bot.message_handler(func=lambda message: session_manager.get_session(message.from_user.id).get("state") == "waiting_for_feedback_comment" if session_manager and session_manager.get_session(message.from_user.id) else False)
def handle_feedback_comment(message):
    """Обрабатывает комментарии к обратной связи."""
    try:
        user_id = message.from_user.id
        comment = message.text.strip()
        
        # Получаем сессию пользователя
        session = session_manager.get_session(user_id) if session_manager else {}
        
        # Проверяем, что пользователь находится в ожидании комментария
        if not session or session.get("state") != "waiting_for_feedback_comment":
            return
        
        # Получаем тип обратной связи
        feedback_type = session.get("feedback_type", "helpful")
        
        # Сбрасываем состояние пользователя
        if session_manager:
            session["state"] = None
            session_manager.update_session(user_id, session)
        
        # Создаем запись в базе данных о обратной связи
        def save_to_db():
            try:
                from models import db, Feedback, User
                from main import app
                
                with app.app_context():
                    # Ищем или создаем пользователя
                    user = User.query.filter_by(telegram_id=user_id).first()
                    
                    if not user:
                        # Если пользователь не найден, создаем нового
                        username = message.from_user.username
                        first_name = message.from_user.first_name
                        last_name = message.from_user.last_name
                        
                        user = User(
                            telegram_id=user_id,
                            username=username,
                            first_name=first_name,
                            last_name=last_name,
                            language_level=session.get("language_level", "B1"),
                            created_at=datetime.now()
                        )
                        db.session.add(user)
                        db.session.commit()
                    
                    # Создаем запись обратной связи
                    feedback = Feedback(
                        user_id=user.id,
                        rating=feedback_type,
                        comment=comment,
                        timestamp=datetime.now()
                    )
                    
                    db.session.add(feedback)
                    db.session.commit()
                    
                    return True
            except Exception as e:
                logger.error(f"Error saving feedback to database: {e}")
                return False
        
        # Сохраняем обратную связь в базе данных
        db_saved = save_to_db()
        
        # Определяем, добавлять ли бонусный запрос
        give_bonus = False
        
        # Проверяем, достаточно ли длинный комментарий для бонуса
        if comment and len(comment.split()) >= 3:
            give_bonus = True
            
            # Обновляем сессию с бонусным запросом
            if session_manager:
                session = session_manager.get_session(user_id) or {}
                session["bonus_requests"] = session.get("bonus_requests", 0) + 1
                session_manager.update_session(user_id, session)
        
        # Создаем клавиатуру для получения бонусного запроса
        if give_bonus:
            markup = types.InlineKeyboardMarkup(row_width=1)
            btn_bonus = types.InlineKeyboardButton(
                text="📚 Get Articles on a New Topic", 
                callback_data="bonus_request"
            )
            markup.add(btn_bonus)
        else:
            markup = None
        
        # Формируем сообщение с благодарностью
        if give_bonus:
            thanks_message = (
                "Thank you for your detailed feedback! 🌟\n\n"
                "As a token of appreciation, you've received a bonus discussion request "
                "that you can use anytime.\n\n"
                "Would you like to use it now to get article recommendations on a new topic?"
            )
        else:
            thanks_message = (
                "Thank you for your feedback!\n\n"
                "To receive bonus discussion requests, please provide more detailed feedback next time "
                "(at least 3 words)."
            )
        
        # Отправляем сообщение
        bot.send_message(
            message.chat.id,
            thanks_message,
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"Error in handle_feedback_comment: {e}")
        error_message = "Sorry, an error occurred while processing your comment."
        bot.reply_to(message, error_message)

@bot.callback_query_handler(func=lambda call: call.data == "bonus_request")
def handle_feedback_bonus(call):
    """Обрабатывает запрос на бонусный запрос статей за обратную связь."""
    try:
        # Запускаем команду discussion
        message = call.message
        message.from_user = call.from_user
        message.text = "/discussion"
        
        # Обновляем сообщение с информацией о бонусе
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="You're using your bonus discussion request! Let's find some new articles for you.",
            reply_markup=None
        )
        
        # Вызываем обработчик команды discussion
        handle_discussion(message)
        
    except Exception as e:
        logger.error(f"Error in handle_feedback_bonus: {e}")
        error_message = "Sorry, an error occurred while processing your bonus request."
        bot.send_message(call.message.chat.id, error_message)

@bot.message_handler(func=lambda message: message.text == '💬 Discussion')
def handle_discussion_button(message):
    """Обрабатывает нажатие кнопки Discussion."""
    # Просто перенаправляем на обработчик команды /discussion
    handle_discussion(message)

@bot.message_handler(func=lambda message: message.text == '⏹️ Stop Discussion')
def handle_stop_discussion_button(message):
    """Обрабатывает нажатие кнопки Stop Discussion."""
    # Просто перенаправляем на обработчик команды /stop_discussion
    handle_stop_discussion(message)

@bot.message_handler(commands=['help'])
def handle_help(message):
    """Переадресует команду /help на /start."""
    handle_start(message)

@bot.message_handler(commands=['admin_feedback'])
def handle_admin_feedback(message):
    """
    Обрабатывает команду /admin_feedback.
    Эта команда доступна только администраторам и позволяет им получать отчет об обратной связи
    прямо из базы данных, а также в виде Excel-файла.
    """
    user_id = message.from_user.id
    username = message.from_user.username if hasattr(message.from_user, 'username') else None
    
    # Проверка на имя пользователя и ID администратора
    is_admin = False
    
    # Сначала проверяем принудительный ID администратора (для отладки)
    if user_id == FORCE_ADMIN_ID:
        is_admin = True
        logger.info(f"Администратор авторизован по фиксированному ID: {user_id}")
    
    # Проверяем по имени пользователя
    elif username in ADMIN_USERS:
        is_admin = True
        logger.info(f"Администратор {username} авторизован по имени")
    
    # Проверяем по ID из словаря администраторов
    elif user_id in ADMIN_USERS.values():
        is_admin = True
        logger.info(f"Администратор авторизован по ID из списка: {user_id}")
    
    # Логгируем результат проверки
    logger.info(f"Проверка администратора: username={username}, id={user_id}, result={is_admin}")
    
    # Дополнительный отладочный вывод
    if DEBUG_MODE:
        bot.send_message(
            message.chat.id, 
            f"🔍 Отладка: Проверка прав администратора\nusername={username}\nid={user_id}\nresult={is_admin}"
        )
    
    # Отказываем в доступе неадминистраторам
    if not is_admin:
        bot.reply_to(message, "Извините, эта команда доступна только администраторам.")
        return
    
    # Отправляем сообщение о начале получения данных
    bot.send_message(message.chat.id, "🔄 Получение данных обратной связи...")
    
    # Получаем обратную связь из базы данных
    from models import db, Feedback, User
    from main import app
    
    try:
        with app.app_context():
            # Отладочное сообщение 
            bot.send_message(
                message.chat.id,
                "🔍 Поиск записей обратной связи в базе данных..."
            )
            
            # Получаем все записи обратной связи напрямую
            feedback_records = []
            all_feedback = Feedback.query.order_by(Feedback.timestamp.desc()).all()
            
            # Добавляем информацию о пользователе для каждой записи
            for fb in all_feedback:
                user = User.query.get(fb.user_id)
                if user:
                    feedback_records.append((
                        fb, 
                        user.telegram_id,
                        user.username,
                        user.first_name,
                        user.last_name
                    ))
                else:
                    # Если пользователь не найден, используем заглушки
                    feedback_records.append((
                        fb, 
                        0,
                        "unknown",
                        "Unknown",
                        "User"
                    ))
            
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
            
            # Отправляем отчет администратору в виде текста
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
            
            # Создаем и отправляем Excel-отчет
            try:
                # Импортируем модуль для создания отчета
                from excel_report import create_simple_feedback_excel
                
                # Генерируем файл отчета
                excel_path = create_simple_feedback_excel(feedback_records)
                
                # Отправляем файл
                with open(excel_path, 'rb') as excel_file:
                    bot.send_document(
                        message.chat.id,
                        excel_file,
                        caption="📊 Полный отчет по обратной связи в Excel"
                    )
                
                logger.info(f"Excel-отчет успешно отправлен: {excel_path}")
                
            except Exception as excel_error:
                logger.error(f"Ошибка при создании Excel-отчета: {excel_error}")
                import traceback
                logger.error(traceback.format_exc())
                
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
        bot.send_message(
            message.chat.id, 
            f"❌ Произошла ошибка при получении данных обратной связи: {str(e)}"
        )
        logger.error(f"Ошибка в admin_feedback: {e}")
        import traceback
        logger.error(traceback.format_exc())

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Обрабатывает все текстовые сообщения."""
    try:
        user_id = message.from_user.id
        
        # Получаем сессию пользователя
        session = session_manager.get_session(user_id) if session_manager else {}
        
        # Если пользователь находится в обсуждении, обрабатываем сообщение
        if session and session.get("state") == "in_discussion":
            # Получаем уровень языка пользователя
            language_level = session.get("language_level", "B1")
            
            # Получаем историю сообщений
            messages_history = []
            if session_manager:
                messages_history = session_manager.get_messages(user_id)
            
            # Генерируем ответ
            response = generate_learning_response(message.text, language_level, messages_history)
            
            # Сохраняем сообщение пользователя и ответ бота в истории
            if session_manager:
                session_manager.add_message_to_session(user_id, "user", message.text)
                session_manager.add_message_to_session(user_id, "assistant", response)
            
            # Отправляем ответ пользователю
            bot.reply_to(message, response)
        else:
            # Если нет активного обсуждения, предлагаем начать
            bot.reply_to(
                message, 
                "To start a language practice conversation, use /discussion."
            )
        
    except Exception as e:
        logger.error(f"Error in handle_all_messages: {e}")
        error_message = "Sorry, I couldn't process your message. Please try again or use /discussion to start a new conversation."
        bot.reply_to(message, error_message)

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
    except Exception as e:
        logger.error(f"Error removing webhook: {e}")
    
    # Добавляем паузу перед запуском polling
    import time
    time.sleep(1)
    
    # Запускаем бота с polling в non-threaded режиме с более строгими таймаутами
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        logger.error(f"Error in polling: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()