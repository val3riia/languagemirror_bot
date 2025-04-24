#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Утилиты для управления базой данных Language Mirror Bot.
"""

import os
import random
import sys
from datetime import datetime, timedelta
from flask import Flask
from models import db, User, Session, Message, Feedback

# Примеры имен пользователей и данных обратной связи
SAMPLE_USERNAMES = [
    "user1", "language_learner", "alex_student", "english_fan", 
    "maria_novice", "john_doe", "jane_smith", "learner2023"
]

LANGUAGE_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]

SAMPLE_MESSAGES = [
    "Привет! Как дела?",
    "Я изучаю английский язык уже несколько месяцев.",
    "Что ты думаешь о книгах Стивена Кинга?",
    "Я был в Лондоне прошлым летом.",
    "Мне нравится изучать иностранные языки.",
    "Какие фильмы тебе нравится смотреть?",
    "Я работаю программистом в IT-компании.",
    "Расскажи мне о своих хобби.",
    "Что ты делаешь в свободное время?",
    "Я хочу улучшить свое произношение."
]

BOT_RESPONSES = [
    "That's interesting! How long have you been learning English?",
    "I understand. Many people find language learning challenging but rewarding.",
    "Great! Your sentence structure is quite good. Just a small suggestion: you could use 'have been' instead of 'was' for a more natural sound.",
    "I noticed you used the word 'like'. You can expand your vocabulary by using alternatives such as 'enjoy', 'appreciate', or 'am fond of'.",
    "What specific aspects of English do you find most challenging?",
    "Your grammar is improving! I can see you're making good progress.",
    "Let's practice some more complex sentences. Try using connecting words like 'however', 'moreover', or 'consequently'.",
    "Have you tried reading English books or watching movies without subtitles?",
    "That's a great question! Let's explore that topic more.",
    "I'd recommend focusing on phrasal verbs - they're very common in everyday English."
]

RATINGS = ["helpful", "okay", "not_helpful"]

COMMENTS = [
    "Отличный бот! Очень помог с практикой разговорного английского.",
    "Хорошо исправляет ошибки, но иногда не понимает контекст.",
    "Понравилась возможность обсуждать интересные темы.",
    "Нужно больше разнообразных тем для обсуждения.",
    "Слишком строгие исправления, чувствую себя неуверенно.",
    "Замечательный инструмент для ежедневной практики!",
    "Бот хорошо адаптируется к моему уровню.",
    "Хотелось бы больше объяснений грамматических правил.",
    "Очень полезно для понимания разговорных фраз.",
    "Отлично помог мне подготовиться к собеседованию на английском.",
    "",  # пустой комментарий
]

def create_app():
    """Создает Flask приложение для использования с базой данных"""
    app = Flask(__name__)
    
    # Настройка подключения к базе данных
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
        
        # Инициализация базы данных
        db.init_app(app)
        return app
    else:
        print("ERROR: DATABASE_URL environment variable not set")
        return None

def create_test_users(app, count=5):
    """Создает тестовых пользователей в базе данных"""
    with app.app_context():
        print(f"Создание {count} тестовых пользователей...")
        
        for i in range(count):
            # Генерируем случайные данные
            telegram_id = random.randint(100000, 999999)
            username = random.choice(SAMPLE_USERNAMES)
            language_level = random.choice(LANGUAGE_LEVELS)
            
            # Создаем пользователя
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=f"Test{i}",
                last_name="User",
                language_level=language_level
            )
            
            try:
                db.session.add(user)
                db.session.commit()
                print(f"✓ Создан пользователь {i+1}: {username} (ID: {telegram_id})")
            except Exception as e:
                db.session.rollback()
                print(f"✗ Ошибка при создании пользователя {i+1}: {e}")
        
        print("Готово!")

def create_test_sessions(app, count=10):
    """Создает тестовые сессии для существующих пользователей"""
    with app.app_context():
        # Получаем всех пользователей
        users = User.query.all()
        
        if not users:
            print("Нет пользователей в базе данных. Сначала создайте пользователей.")
            return
        
        print(f"Создание {count} тестовых сессий...")
        
        for i in range(count):
            # Выбираем случайного пользователя
            user = random.choice(users)
            
            # Генерируем случайные данные
            started_at = datetime.utcnow() - timedelta(days=random.randint(0, 7))
            is_active = random.choice([True, False])
            
            # Если сессия неактивна, добавляем время завершения
            ended_at = None
            if not is_active:
                ended_at = started_at + timedelta(minutes=random.randint(5, 60))
            
            # Создаем сессию
            session = Session(
                user_id=user.id,
                started_at=started_at,
                ended_at=ended_at,
                is_active=is_active
            )
            
            try:
                db.session.add(session)
                db.session.commit()
                print(f"✓ Создана сессия {i+1} для пользователя {user.username}")
                
                # Добавляем сообщения
                messages_count = random.randint(3, 15)
                create_test_messages(app, session.id, messages_count)
                
                # Обновляем количество сообщений в сессии
                session.messages_count = messages_count
                db.session.commit()
                
                # Если сессия неактивна, добавляем обратную связь
                if not is_active:
                    create_test_feedback(app, user.id, session.id)
                
            except Exception as e:
                db.session.rollback()
                print(f"✗ Ошибка при создании сессии {i+1}: {e}")
        
        print("Готово!")

def create_test_messages(app, session_id, count=10):
    """Создает тестовые сообщения для указанной сессии"""
    with app.app_context():
        session = Session.query.get(session_id)
        
        if not session:
            print(f"Сессия с ID {session_id} не найдена.")
            return
        
        # Поочередно добавляем сообщения от пользователя и бота
        for i in range(count):
            role = "user" if i % 2 == 0 else "assistant"
            content = random.choice(SAMPLE_MESSAGES if role == "user" else BOT_RESPONSES)
            
            # Время сообщения в пределах времени сессии
            if session.ended_at:
                message_time = session.started_at + (session.ended_at - session.started_at) * (i / count)
            else:
                message_time = session.started_at + timedelta(minutes=i*2)
            
            # Создаем сообщение
            message = Message(
                session_id=session_id,
                role=role,
                content=content,
                timestamp=message_time
            )
            
            try:
                db.session.add(message)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"✗ Ошибка при создании сообщения: {e}")

def create_test_feedback(app, user_id, session_id=None):
    """Создает тестовую обратную связь для указанного пользователя и сессии"""
    with app.app_context():
        # Проверяем, существует ли пользователь
        user = User.query.get(user_id)
        
        if not user:
            print(f"Пользователь с ID {user_id} не найден.")
            return
        
        # Создаем обратную связь
        rating = random.choice(RATINGS)
        comment = random.choice(COMMENTS)
        
        feedback = Feedback(
            user_id=user_id,
            session_id=session_id,
            rating=rating,
            comment=comment
        )
        
        try:
            db.session.add(feedback)
            db.session.commit()
            print(f"✓ Создана обратная связь для пользователя {user.username} (рейтинг: {rating})")
        except Exception as e:
            db.session.rollback()
            print(f"✗ Ошибка при создании обратной связи: {e}")

def main():
    """Основная функция для работы с базой данных"""
    app = create_app()
    
    if not app:
        sys.exit(1)
    
    # Создаем все таблицы
    with app.app_context():
        db.create_all()
        print("Таблицы базы данных созданы!")
    
    # Меню действий
    while True:
        print("\n=== УТИЛИТЫ БАЗЫ ДАННЫХ LANGUAGE MIRROR BOT ===")
        print("1. Создать тестовых пользователей")
        print("2. Создать тестовые сессии и сообщения")
        print("3. Просмотреть статистику базы данных")
        print("0. Выход")
        
        choice = input("\nВыберите опцию (0-3): ")
        
        if choice == "0":
            print("Выход из программы...")
            break
        elif choice == "1":
            count = int(input("Введите количество пользователей (по умолчанию 5): ") or "5")
            create_test_users(app, count)
        elif choice == "2":
            count = int(input("Введите количество сессий (по умолчанию 10): ") or "10")
            create_test_sessions(app, count)
        elif choice == "3":
            with app.app_context():
                users_count = User.query.count()
                sessions_count = Session.query.count()
                active_sessions = Session.query.filter_by(is_active=True).count()
                messages_count = Message.query.count()
                feedback_count = Feedback.query.count()
                
                print("\n=== СТАТИСТИКА БАЗЫ ДАННЫХ ===")
                print(f"Пользователей: {users_count}")
                print(f"Сессий: {sessions_count} (активных: {active_sessions})")
                print(f"Сообщений: {messages_count}")
                print(f"Обратной связи: {feedback_count}")
                
                input("\nНажмите Enter для продолжения...")
        else:
            print("Неверный выбор. Попробуйте еще раз.")

if __name__ == "__main__":
    main()