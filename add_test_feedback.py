#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script to add test feedback data to the Language Mirror Bot.
This is useful for testing the admin dashboard.
"""

import requests
import random
import time
from datetime import datetime, timedelta

# URL для API обратной связи
API_URL = "http://localhost:5000/api/feedback"

# Имена пользователей для генерации тестовых данных
sample_usernames = [
    "user1", "language_learner", "alex_student", "english_fan", 
    "maria_novice", "john_doe", "jane_smith", "learner2023"
]

# Возможные рейтинги
ratings = ["helpful", "okay", "not_helpful"]

# Примеры комментариев
sample_comments = [
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

def generate_timestamp():
    """Генерирует случайную временную метку за последние 7 дней"""
    now = datetime.now()
    delta = random.randint(0, 7 * 24 * 60 * 60)  # случайное количество секунд в пределах 7 дней
    random_time = now - timedelta(seconds=delta)
    return random_time.isoformat()

def add_test_feedback(count=10):
    """Добавляет тестовые данные обратной связи"""
    
    print(f"Добавление {count} тестовых отзывов...")
    
    for i in range(count):
        # Генерируем случайные данные
        user_id = random.randint(100000, 999999)
        username = random.choice(sample_usernames)
        rating = random.choice(ratings)
        comment = random.choice(sample_comments)
        
        # Создаем данные для отправки
        feedback_data = {
            "user_id": user_id,
            "username": username,
            "rating": rating,
            "comment": comment
        }
        
        # Пытаемся отправить запрос
        try:
            response = requests.post(API_URL, json=feedback_data)
            
            if response.status_code == 201:
                print(f"✓ Успешно добавлен отзыв #{i+1}: {username} - {rating}")
            else:
                print(f"✗ Ошибка при добавлении отзыва #{i+1}: {response.status_code} - {response.text}")
        
        except Exception as e:
            print(f"✗ Ошибка при отправке запроса: {e}")
        
        # Небольшая пауза между запросами
        time.sleep(0.2)
    
    print("Готово!")

if __name__ == "__main__":
    # Запрашиваем у пользователя количество тестовых отзывов
    try:
        count = int(input("Введите количество тестовых отзывов (по умолчанию 10): ") or "10")
    except ValueError:
        count = 10
        print("Введено некорректное значение, используется значение по умолчанию: 10")
    
    add_test_feedback(count)