#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Отладочный скрипт для тестирования функции обратной связи администратора.
"""

import os
import sys
import json
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

def check_environment():
    """Проверка необходимых переменных окружения."""
    variables = {
        "TELEGRAM_TOKEN": os.environ.get("TELEGRAM_TOKEN"),
        "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY"),
        "DATABASE_URL": os.environ.get("DATABASE_URL"),
    }
    
    for name, value in variables.items():
        if value:
            logger.info(f"✅ {name} найден")
        else:
            logger.error(f"❌ {name} не установлен")
    
    return all(variables.values())

def get_admin_feedback():
    """
    Получение данных обратной связи, имитирующее функцию handle_admin_feedback.
    Это позволяет нам отладить проблемы с получением обратной связи без запуска бота.
    """
    logger.info("🔍 Получение данных обратной связи для администратора...")
    
    try:
        # Импортируем модели для работы с базой данных
        from models import db, Feedback, User
        from main import app

        with app.app_context():
            # Прямое тестирование запроса из базы данных
            logger.info("Выполняем прямой запрос к базе данных...")
            
            # Получаем все записи обратной связи напрямую
            feedback_records = []
            all_feedback = Feedback.query.order_by(Feedback.timestamp.desc()).all()
            
            if not all_feedback:
                logger.warning("В базе данных нет записей обратной связи")
                return
            
            logger.info(f"Найдено {len(all_feedback)} записей обратной связи")
            
            # Добавляем информацию о пользователе для каждой записи
            for fb in all_feedback:
                user = User.query.get(fb.user_id)
                if user:
                    feedback_records.append({
                        "id": fb.id,
                        "rating": fb.rating,
                        "comment": fb.comment,
                        "timestamp": fb.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "user_id": user.telegram_id,
                        "username": user.username,
                        "first_name": user.first_name,
                        "last_name": user.last_name
                    })
                else:
                    # Если пользователь не найден, используем заглушки
                    feedback_records.append({
                        "id": fb.id,
                        "rating": fb.rating,
                        "comment": fb.comment,
                        "timestamp": fb.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "user_id": 0,
                        "username": "unknown",
                        "first_name": "Unknown",
                        "last_name": "User"
                    })
            
            # Подсчитываем статистику рейтингов
            rating_counts = {"helpful": 0, "okay": 0, "not_helpful": 0}
            
            for record in feedback_records:
                if record["rating"] in rating_counts:
                    rating_counts[record["rating"]] += 1
            
            # Выводим отчет в консоль для отладки
            report = "📊 Отчет по обратной связи\n\n"
            report += f"👍 Полезно: {rating_counts['helpful']}\n"
            report += f"🤔 Нормально: {rating_counts['okay']}\n"
            report += f"👎 Не полезно: {rating_counts['not_helpful']}\n\n"
            
            # Общее количество отзывов
            total_feedback = sum(rating_counts.values())
            report += f"\nВсего отзывов: {total_feedback}\n\n"
            
            # Добавляем последние 5 комментариев
            report += "Последние комментарии:\n"
            comment_count = 0
            
            for record in feedback_records:
                if record["comment"]:
                    comment_count += 1
                    
                    # Формируем имя пользователя для отображения
                    user_display = record["username"] or record["first_name"] or f"User {record['user_id']}"
                    
                    # Выводим информацию о комментарии
                    report += f"{comment_count}. {user_display} ({record['timestamp']}):\n"
                    report += f"\"{record['comment']}\"\n\n"
                    
                    if comment_count >= 5:
                        break
            
            if comment_count == 0:
                report += "Комментариев пока нет."
            
            # Выводим полный отчет
            print("\n" + "=" * 80)
            print(report)
            print("=" * 80 + "\n")
            
            # Также выводим полные данные в JSON формате для отладки
            logger.debug("Полные данные обратной связи:")
            logger.debug(json.dumps(feedback_records, indent=2, ensure_ascii=False))
            
            return feedback_records
            
    except Exception as e:
        logger.error(f"❌ Ошибка при получении данных обратной связи: {e}")
        import traceback
        logger.error(traceback.format_exc())

def main():
    """Основная функция."""
    print("🔍 Запуск отладки команды admin_feedback...")
    
    # Проверяем переменные окружения
    if not check_environment():
        print("❌ Отсутствуют необходимые переменные окружения")
        sys.exit(1)
    
    # Получаем данные обратной связи
    feedback_data = get_admin_feedback()
    
    if not feedback_data:
        print("❌ Не удалось получить данные обратной связи")
        print("Проверьте логи выше для получения информации об ошибке.")
    else:
        print(f"✅ Успешно получено {len(feedback_data)} записей обратной связи")

if __name__ == "__main__":
    main()