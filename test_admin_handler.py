"""
Тестовый скрипт для непосредственной проверки обработчика admin_feedback.
"""
import logging
import os
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Создаем тестовый класс для имитации сообщения Telegram
class MockMessage:
    class MockUser:
        def __init__(self, id, username, first_name):
            self.id = id
            self.username = username
            self.first_name = first_name
    
    class MockChat:
        def __init__(self, id):
            self.id = id
    
    def __init__(self, chat_id, user_id, username, first_name):
        self.chat = self.MockChat(chat_id)
        self.from_user = self.MockUser(user_id, username, first_name)

def main():
    logger.info("Тестирование обработчика admin_feedback...")
    
    # Импортируем модуль с ботом и обработчиком
    from language_mirror_telebot import handle_admin_feedback, bot
    
    # ID пользователя avr3lia, который мы добавили в код
    user_id = 5783753055
    username = "avr3lia"
    
    # Создаем фиктивное сообщение
    logger.info(f"Создаем тестовое сообщение для пользователя {username} с ID {user_id}")
    message = MockMessage(
        chat_id=user_id,  # Используем тот же ID для чата
        user_id=user_id,
        username=username,
        first_name="Test User"
    )
    
    # Проверяем, распознается ли пользователь как администратор
    from language_mirror_telebot import ADMIN_USERS
    logger.info(f"Список администраторов: {ADMIN_USERS}")
    is_admin = username in ADMIN_USERS and ADMIN_USERS.get(username) == user_id
    logger.info(f"Пользователь {username} распознается как администратор: {is_admin}")
    
    # Вызываем обработчик напрямую
    logger.info("Вызываем обработчик admin_feedback напрямую...")
    handle_admin_feedback(message)
    
    # Даем время для обработки и вывода сообщений
    logger.info("Ожидаем завершения обработки (5 секунд)...")
    time.sleep(5)
    
    logger.info("Тестирование завершено!")

if __name__ == "__main__":
    main()