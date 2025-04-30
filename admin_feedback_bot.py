#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Упрощенный бот для получения отчетов об обратной связи.
Этот бот предназначен только для администраторов и обрабатывает только команду /admin_feedback.
"""

import os
import sys
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Проверяем наличие PyTelegramBotAPI
try:
    import telebot
except ImportError:
    logger.error("Не установлена библиотека PyTelegramBotAPI. Установите её с помощью pip install pyTelegramBotAPI")
    sys.exit(1)

# Получаем токен из переменных окружения
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN не установлен в переменных окружения")
    sys.exit(1)

# Создаем экземпляр бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ID администраторов из переменных окружения
ADMIN_ID = int(os.environ.get("ADMIN_USER_ID", "0"))

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Обработчик команды /start."""
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь администратором
    if user_id != ADMIN_ID:
        bot.reply_to(message, "Извините, этот бот доступен только администраторам.")
        return
    
    bot.send_message(
        message.chat.id,
        "👋 Здравствуйте, администратор!\n\n"
        "Этот бот предназначен только для получения отчетов об обратной связи.\n"
        "Используйте команду /admin_feedback для получения отчета."
    )

@bot.message_handler(commands=['admin_feedback'])
def handle_admin_feedback(message):
    """Обработчик команды /admin_feedback."""
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь администратором
    if user_id != ADMIN_ID:
        bot.reply_to(message, "Извините, эта команда доступна только администраторам.")
        return
    
    # Отправляем сообщение о начале получения данных
    bot.send_message(message.chat.id, "🔄 Получение данных обратной связи...")
    
    try:
        # Импортируем модели для работы с базой данных
        from models import db, Feedback, User
        from main import app
        
        with app.app_context():
            # Отладочное сообщение
            bot.send_message(
                message.chat.id,
                "🔍 Поиск записей обратной связи в базе данных..."
            )
            
            # Получаем все записи обратной связи напрямую
            feedback_records = []
            all_feedback = Feedback.query.order_by(Feedback.timestamp.desc()).all()
            
            if not all_feedback:
                bot.send_message(
                    message.chat.id,
                    "📝 Данные обратной связи отсутствуют.\n\n"
                    "Вы можете добавить тестовые данные с помощью скрипта add_test_feedback.py."
                )
                return
            
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
            
            # Формируем отчет
            # Подсчитываем статистику рейтингов
            rating_counts = {"helpful": 0, "okay": 0, "not_helpful": 0}
            
            for record, _, _, _, _ in feedback_records:
                if record.rating in rating_counts:
                    rating_counts[record.rating] += 1
            
            # Отправляем отчет администратору
            report = "📊 Отчет по обратной связи\n\n"
            report += f"👍 Полезно: {rating_counts['helpful']}\n"
            report += f"🤔 Нормально: {rating_counts['okay']}\n"
            report += f"👎 Не полезно: {rating_counts['not_helpful']}\n\n"
            
            # Добавляем последние 5 комментариев с подробной информацией
            report += "Последние комментарии:\n"
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
                    
                    # Добавляем информацию о комментарии
                    report += f"{comment_count}. {rating_emoji} {user_display} ({date_str}):\n"
                    report += f"\"{record.comment}\"\n\n"
                    
                    if comment_count >= 5:
                        break
            
            if comment_count == 0:
                report += "Комментариев пока нет."
            
            # Общее количество отзывов
            total_feedback = sum(rating_counts.values())
            report += f"\nВсего отзывов: {total_feedback}"
            
            # Отправляем отчет
            bot.send_message(
                message.chat.id, 
                report
            )
            
            # Отладочное сообщение для проверки
            bot.send_message(
                message.chat.id,
                "✅ Отчёт по обратной связи сформирован успешно"
            )
            
    except Exception:
        bot.send_message(
            message.chat.id, 
            "❌ Произошла ошибка при получении данных обратной связи. Проверьте журнал."
        )
        logger.error("Ошибка в admin_feedback")
        # Закомментировано для безопасности на GitHub
        # import traceback
        # logger.error(traceback.format_exc())

@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    """Обработчик всех остальных сообщений."""
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь администратором
    if user_id != ADMIN_ID:
        bot.reply_to(message, "Извините, этот бот доступен только администраторам.")
        return
    
    bot.reply_to(
        message,
        "Для получения отчета об обратной связи используйте команду /admin_feedback."
    )

def main():
    """Запуск бота."""
    logger.info("Запуск бота для обратной связи администратора...")
    
    # Удаляем webhook перед запуском polling
    try:
        bot.remove_webhook()
        logger.info("Webhook успешно удален")
    except Exception:
        logger.error("Ошибка при удалении webhook")
    
    # Запускаем бота с опросом
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception:
        logger.error("Ошибка при запуске бота")
        # Закомментировано для безопасности на GitHub
        # import traceback
        # logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()