#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для добавления тестовых данных обратной связи в Language Mirror Bot.
Это полезно для тестирования функционала admin_feedback и системы генерации отчетов.
"""

import os
import sys
import random
import logging
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

def generate_timestamp():
    """Генерирует случайную временную метку за последние 7 дней"""
    now = datetime.now()
    days_ago = random.randint(0, 7)
    hours_ago = random.randint(0, 23)
    minutes_ago = random.randint(0, 59)
    
    return now - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)

def add_test_feedback(count=10):
    """Добавляет тестовые данные обратной связи"""
    try:
        # Импортируем необходимые модули
        from models import db, User, Feedback
        from main import app
        
        # Тестовые данные для отзывов
        ratings = ["helpful", "okay", "not_helpful"]
        
        # Веса для рейтингов, чтобы сделать распределение более реалистичным
        # 60% полезно, 30% нормально, 10% не полезно
        rating_weights = [0.6, 0.3, 0.1]
        
        # Примеры комментариев для каждого типа рейтинга
        comments = {
            "helpful": [
                "Очень полезно! Узнал много новых слов.",
                "Отличный разговорный партнер, помог мне улучшить произношение.",
                "Понравилось объяснение грамматики, все очень понятно.",
                "Хороший собеседник, дает полезную обратную связь.",
                "Помог мне преодолеть языковой барьер.",
                "Отличные статьи по теме, много узнал нового.",
                "Супер! Буду использовать каждый день для практики."
            ],
            "okay": [
                "Неплохо, но хотелось бы больше тем для обсуждения.",
                "Нормально, но иногда ответы слишком длинные.",
                "В целом полезно, но не хватает упражнений на грамматику.",
                "Помогает, но хотелось бы больше идиом и разговорных фраз.",
                "Удобно для практики, но иногда не совсем понимает вопросы."
            ],
            "not_helpful": [
                "Не помогло мне с моей конкретной задачей.",
                "Слишком много ошибок в ответах.",
                "Не понравились рекомендованные статьи."
            ]
        }
        
        # Демо пользователи
        demo_users = [
            {"telegram_id": 123456789, "username": "language_learner1", "first_name": "Иван", "last_name": "Петров"},
            {"telegram_id": 987654321, "username": "english_student", "first_name": "Анна", "last_name": "Смирнова"},
            {"telegram_id": 555555555, "username": "polyglot007", "first_name": "Максим", "last_name": "Иванов"},
            {"telegram_id": 111222333, "username": "linguist", "first_name": "Елена", "last_name": "Козлова"},
            {"telegram_id": 444333222, "username": "word_lover", "first_name": "Алексей", "last_name": "Соколов"}
        ]
        
        with app.app_context():
            created_count = 0
            
            # Создаем или получаем пользователей
            users = []
            for user_data in demo_users:
                user = User.query.filter_by(telegram_id=user_data["telegram_id"]).first()
                if not user:
                    user = User(
                        telegram_id=user_data["telegram_id"],
                        username=user_data["username"],
                        first_name=user_data["first_name"],
                        last_name=user_data["last_name"],
                        language_level="B1",  # Значение по умолчанию
                        created_at=datetime.now()
                    )
                    db.session.add(user)
                    db.session.commit()
                    logger.info(f"Создан тестовый пользователь: {user.username}")
                
                users.append(user)
            
            # Добавляем отзывы
            for i in range(count):
                # Выбираем случайного пользователя
                user = random.choice(users)
                
                # Выбираем рейтинг с учетом весов
                rating = random.choices(ratings, weights=rating_weights, k=1)[0]
                
                # Выбираем случайный комментарий для этого рейтинга
                comment = random.choice(comments[rating])
                
                # Генерируем случайную временную метку
                timestamp = generate_timestamp()
                
                # Создаем отзыв
                feedback = Feedback(
                    user_id=user.id,
                    rating=rating,
                    comment=comment,
                    timestamp=timestamp
                )
                
                db.session.add(feedback)
                created_count += 1
            
            # Сохраняем в базу данных
            db.session.commit()
            
            return created_count
            
    except Exception as e:
        logger.error(f"Ошибка при добавлении тестовой обратной связи: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0

def main():
    """Основная функция скрипта"""
    print("\n📊 Добавление тестовых данных обратной связи для Language Mirror Bot\n")
    
    # Проверяем переменные окружения
    if not os.environ.get("DATABASE_URL"):
        print("❌ ОШИБКА: Переменная окружения DATABASE_URL не установлена")
        print("Установите URL базы данных PostgreSQL в переменных окружения")
        sys.exit(1)
    
    # Используем значение по умолчанию без ввода пользователя
    count = 10
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            print(f"Некорректное значение в аргументе командной строки: {sys.argv[1]}")
            print("Будет использовано значение по умолчанию (10)")
    
    print(f"Добавление {count} тестовых отзывов...")
    created_count = add_test_feedback(count)
    
    if created_count > 0:
        print(f"✅ Успешно добавлено {created_count} тестовых отзывов")
        print("\nТеперь вы можете использовать команду /admin_feedback в боте для просмотра")
        print("этих данных или запустить test_admin_feedback.py для проверки генерации Excel-отчета.")
    else:
        print("❌ Не удалось добавить тестовые отзывы. Проверьте логи для деталей.")
        sys.exit(1)

if __name__ == "__main__":
    main()