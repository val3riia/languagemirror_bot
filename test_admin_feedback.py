#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Тестовый скрипт для проверки функционала /admin_feedback.
Это полезно для проверки и отладки создания Excel-отчета
без необходимости использования бота Telegram.
"""

import os
import sys
import logging
import traceback
from datetime import datetime
from typing import List, Tuple, Any

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

def get_feedback_data():
    """
    Получает данные обратной связи из базы данных.
    Возвращает список кортежей (feedback, telegram_id, username, first_name, last_name).
    """
    try:
        # Импортируем необходимые модули
        from models import db, Feedback, User
        from main import app
        
        with app.app_context():
            # Получаем все записи обратной связи
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
            
            return feedback_records
    
    except Exception as e:
        logger.error(f"Ошибка при получении данных обратной связи: {e}")
        logger.error(traceback.format_exc())
        return []

def create_and_save_excel(feedback_records: List[Tuple[Any, int, str, str, str]]):
    """
    Создает и сохраняет Excel-отчет.
    
    Args:
        feedback_records: Список кортежей (feedback, telegram_id, username, first_name, last_name)
    """
    try:
        from excel_report import create_simple_feedback_excel
        
        if not feedback_records:
            logger.warning("Нет данных обратной связи для создания отчета")
            return None
        
        # Генерируем файл отчета
        excel_path = create_simple_feedback_excel(feedback_records)
        logger.info(f"Excel-отчет успешно создан: {excel_path}")
        
        return excel_path
    
    except Exception as e:
        logger.error(f"Ошибка при создании Excel-отчета: {e}")
        logger.error(traceback.format_exc())
        return None

def print_summary(feedback_records: List[Tuple[Any, int, str, str, str]]):
    """
    Выводит сводную информацию о данных обратной связи.
    
    Args:
        feedback_records: Список кортежей (feedback, telegram_id, username, first_name, last_name)
    """
    if not feedback_records:
        print("📝 Данные обратной связи отсутствуют.")
        return
    
    # Подсчитываем статистику рейтингов
    rating_counts = {"helpful": 0, "okay": 0, "not_helpful": 0}
    
    for record, _, _, _, _ in feedback_records:
        if record.rating in rating_counts:
            rating_counts[record.rating] += 1
    
    # Выводим отчет
    print("\n" + "="*80)
    print("📊 Отчет по обратной связи")
    print("="*80)
    
    print(f"👍 Полезно: {rating_counts['helpful']}")
    print(f"🤔 Нормально: {rating_counts['okay']}")
    print(f"👎 Не полезно: {rating_counts['not_helpful']}")
    print(f"\nВсего отзывов: {sum(rating_counts.values())}")
    
    print("\nПоследние комментарии:")
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
            
            # Выводим информацию о комментарии
            print(f"{comment_count}. {rating_emoji} {user_display} ({date_str}):")
            print(f'"{record.comment}"\n')
            
            if comment_count >= 5:
                break
    
    if comment_count == 0:
        print("Комментариев пока нет.")
    
    print("="*80)

def main():
    """Основная функция скрипта."""
    print("\n🔍 Тестирование функционала admin_feedback и создания Excel-отчета...\n")
    
    # Проверяем переменные окружения
    if not os.environ.get("DATABASE_URL"):
        print("❌ ОШИБКА: Переменная окружения DATABASE_URL не установлена")
        print("Установите URL базы данных PostgreSQL в переменных окружения")
        sys.exit(1)
    
    # Получаем данные обратной связи
    print("Получение данных обратной связи из базы данных...")
    feedback_records = get_feedback_data()
    
    if not feedback_records:
        print("❌ Не удалось получить данные обратной связи или они отсутствуют")
        sys.exit(1)
    
    print(f"✅ Получено {len(feedback_records)} записей обратной связи")
    
    # Выводим сводную информацию
    print_summary(feedback_records)
    
    # Создаем Excel-отчет
    print("\nСоздание Excel-отчета...")
    excel_path = create_and_save_excel(feedback_records)
    
    if excel_path:
        print(f"✅ Excel-отчет успешно создан: {excel_path}")
        print(f"   Полный путь: {os.path.abspath(excel_path)}")
    else:
        print("❌ Не удалось создать Excel-отчет")
        sys.exit(1)

if __name__ == "__main__":
    main()