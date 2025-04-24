#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Административные инструменты для управления Language Mirror Bot.
"""

import os
import sys
import json
import requests
import random
from datetime import datetime, timedelta

# Base URL
BASE_URL = "http://localhost:5000"
API_URL = f"{BASE_URL}/api/feedback"

def print_header(text):
    """Печатает заголовок для CLI меню"""
    print("\n" + "=" * 50)
    print(f"   {text}")
    print("=" * 50)

def print_menu():
    """Печатает главное меню"""
    print_header("LANGUAGE MIRROR BOT - АДМИНИСТРАТИВНЫЕ ИНСТРУМЕНТЫ")
    print("\n1. Проверить статус бота")
    print("2. Добавить тестовые данные обратной связи")
    print("3. Просмотреть все данные обратной связи")
    print("4. Очистить данные обратной связи")
    print("5. Проверить переменные окружения")
    print("0. Выход")

def check_bot_status():
    """Проверяет статус бота, отправляя запрос к API"""
    print_header("ПРОВЕРКА СТАТУСА БОТА")
    
    try:
        response = requests.get(f"{BASE_URL}/api/feedback")
        
        if response.status_code == 200:
            print("\n✓ Бот запущен и API работает!")
            print(f"✓ HTTP Status: {response.status_code}")
        else:
            print("\n✗ API вернуло необычный статус-код:")
            print(f"✗ HTTP Status: {response.status_code}")
            print(f"✗ Response: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("\n✗ Не удалось подключиться к API. Проверьте, запущен ли сервер.")
    except Exception as e:
        print(f"\n✗ Ошибка при проверке статуса: {e}")
    
    input("\nНажмите Enter для продолжения...")

def add_test_feedback():
    """Добавляет тестовые данные обратной связи"""
    print_header("ДОБАВЛЕНИЕ ТЕСТОВЫХ ДАННЫХ")
    
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
    
    try:
        count = int(input("\nВведите количество тестовых отзывов (по умолчанию 5): ") or "5")
    except ValueError:
        count = 5
        print("Введено некорректное значение, используется значение по умолчанию: 5")
    
    print(f"\nДобавление {count} тестовых отзывов...")
    
    success = 0
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
                success += 1
                print(f"✓ Успешно добавлен отзыв #{i+1}: {username} - {rating}")
            else:
                print(f"✗ Ошибка при добавлении отзыва #{i+1}: {response.status_code} - {response.text}")
        
        except Exception as e:
            print(f"✗ Ошибка при отправке запроса: {e}")
    
    print(f"\nУспешно добавлено {success} из {count} отзывов.")
    input("\nНажмите Enter для продолжения...")

def view_feedback():
    """Показывает все данные обратной связи"""
    print_header("ПРОСМОТР ДАННЫХ ОБРАТНОЙ СВЯЗИ")
    
    try:
        response = requests.get(API_URL)
        
        if response.status_code == 200:
            data = response.json()
            
            if not data:
                print("\nДанные обратной связи отсутствуют.")
            else:
                print(f"\nНайдено {len(data)} записей:\n")
                
                for item in data:
                    rating_display = item['rating']
                    if rating_display == 'helpful':
                        rating_display = '👍 Helpful'
                    elif rating_display == 'okay':
                        rating_display = '🤔 Okay'
                    elif rating_display == 'not_helpful':
                        rating_display = '👎 Not helpful'
                    
                    print(f"ID: {item.get('id', 'N/A')}")
                    print(f"Пользователь: {item.get('username', 'unknown')} (ID: {item.get('user_id', 'unknown')})")
                    print(f"Оценка: {rating_display}")
                    print(f"Комментарий: {item.get('comment', '')}")
                    print(f"Время: {item.get('timestamp', 'unknown')}")
                    print("-" * 40)
        else:
            print(f"\n✗ Ошибка при получении данных: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"\n✗ Ошибка при получении данных: {e}")
    
    input("\nНажмите Enter для продолжения...")

def check_environment():
    """Проверяет переменные окружения"""
    print_header("ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ")
    
    telegram_token = os.environ.get("TELEGRAM_TOKEN")
    
    print("\nTELEGRAM_TOKEN:", "✓ Установлен" if telegram_token else "✗ Не установлен")
    
    if not telegram_token:
        print("\nДля работы бота необходимо установить TELEGRAM_TOKEN.")
        print("Вы можете установить его через переменные окружения:")
        print("  export TELEGRAM_TOKEN='your_telegram_bot_token'")
    
    input("\nНажмите Enter для продолжения...")

def main():
    """Основная функция для запуска административных инструментов"""
    while True:
        os.system('clear' if os.name != 'nt' else 'cls')
        print_menu()
        
        choice = input("\nВыберите опцию (0-5): ")
        
        if choice == '0':
            print("\nВыход из программы...")
            sys.exit(0)
        elif choice == '1':
            check_bot_status()
        elif choice == '2':
            add_test_feedback()
        elif choice == '3':
            view_feedback()
        elif choice == '4':
            print("\nЭта функция не реализована.")
            input("\nНажмите Enter для продолжения...")
        elif choice == '5':
            check_environment()
        else:
            print("\nНеверный выбор. Попробуйте еще раз.")
            input("\nНажмите Enter для продолжения...")

if __name__ == "__main__":
    main()