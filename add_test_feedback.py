#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script to add test feedback data to the Language Mirror Bot.
This is useful for testing the admin dashboard.
"""

import os
import sys
import random
from datetime import datetime, timedelta

from models import db, User, Session, Feedback

# Примеры комментариев для обратной связи
SAMPLE_COMMENTS = [
    "Очень полезный бот! Помог мне с практикой английского.",
    "Хорошо корректирует ошибки, но иногда не понимает контекст.",
    "Нравится, что можно обсуждать интересные темы.",
    "Хотелось бы больше разнообразия в темах для обсуждения.",
    "Слишком строгие исправления, теряю мотивацию.",
    "Отличный инструмент для ежедневной практики!",
    "Бот хорошо адаптируется к моему уровню.",
    "Нужно больше грамматических объяснений.",
    "Помогает понимать разговорные фразы.",
    "Подготовил меня к собеседованию на английском!",
    ""  # Пустой комментарий
]

RATINGS = ["helpful", "okay", "not_helpful"]

def generate_timestamp():
    """Генерирует случайную временную метку за последние 7 дней"""
    now = datetime.utcnow()
    days_ago = random.randint(0, 7)
    hours_ago = random.randint(0, 23)
    minutes_ago = random.randint(0, 59)
    
    return now - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)

def add_test_feedback(count=10):
    """Добавляет тестовые данные обратной связи"""
    from flask import Flask
    
    # Создаем Flask приложение для работы с базой данных
    app = Flask(__name__)
    database_url = os.environ.get("DATABASE_URL")
    
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set")
        return
    
    # Исправляем URL для PostgreSQL, если нужно
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Инициализируем базу данных с приложением
    db.init_app(app)
    
    with app.app_context():
        # Получаем существующих пользователей
        users = User.query.all()
        
        if not users:
            print("No users found in the database. Creating test users first...")
            # Создаем тестовых пользователей, если их нет
            for i in range(5):
                user = User(
                    telegram_id=random.randint(100000, 999999),
                    username=f"test_user_{i}",
                    first_name=f"Test{i}",
                    last_name="User",
                    language_level=random.choice(["A1", "A2", "B1", "B2", "C1", "C2"])
                )
                db.session.add(user)
            
            db.session.commit()
            users = User.query.all()
        
        # Создаем сессии, если их нет
        sessions = Session.query.all()
        if not sessions:
            print("No sessions found. Creating test sessions...")
            for user in users:
                # Случайное количество сессий для каждого пользователя
                session_count = random.randint(1, 3)
                for _ in range(session_count):
                    started_at = generate_timestamp()
                    ended_at = started_at + timedelta(minutes=random.randint(5, 60))
                    
                    session = Session(
                        user_id=user.id,
                        started_at=started_at,
                        ended_at=ended_at,
                        is_active=False,
                        messages_count=random.randint(5, 20)
                    )
                    db.session.add(session)
            
            db.session.commit()
            sessions = Session.query.all()
        
        # Создаем обратную связь
        print(f"Adding {count} test feedback entries...")
        for _ in range(count):
            # Выбираем случайного пользователя и сессию
            user = random.choice(users)
            session = None
            
            # 30% шанс, что обратная связь не привязана к сессии
            if random.random() > 0.3 and sessions:
                user_sessions = [s for s in sessions if s.user_id == user.id]
                if user_sessions:
                    session = random.choice(user_sessions)
            
            feedback = Feedback(
                user_id=user.id,
                session_id=session.id if session else None,
                rating=random.choice(RATINGS),
                comment=random.choice(SAMPLE_COMMENTS),
                timestamp=generate_timestamp()
            )
            
            db.session.add(feedback)
        
        db.session.commit()
        print(f"Successfully added {count} test feedback entries!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
            add_test_feedback(count)
        except ValueError:
            print(f"Error: '{sys.argv[1]}' is not a valid number")
            print("Usage: python add_test_feedback.py [count]")
    else:
        add_test_feedback()