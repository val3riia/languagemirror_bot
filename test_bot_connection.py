#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для проверки возможности подключения к Telegram API.
"""

import os
import sys
import time
import logging
import requests

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

def check_telegram_api():
    """Проверяет подключение к Telegram API используя getMe."""
    
    # Получаем токен из переменных окружения
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN не установлен")
        return False
    
    # Формируем URL для запроса getMe
    api_url = f"https://api.telegram.org/bot{token}/getMe"
    
    try:
        # Отправляем запрос к API
        logger.info(f"Отправка запроса к {api_url}...")
        response = requests.get(api_url, timeout=10)
        
        # Проверяем ответ
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Ответ API: {result}")
            
            if result.get("ok"):
                bot_info = result.get("result", {})
                bot_username = bot_info.get("username")
                logger.info(f"✅ Успешное подключение к боту @{bot_username}")
                return True
            else:
                logger.error(f"❌ API вернул ошибку: {result}")
        else:
            logger.error(f"❌ Ошибка запроса: Код {response.status_code}")
            logger.error(f"Ответ: {response.text}")
    
    except Exception as e:
        logger.error(f"❌ Исключение при запросе к API: {e}")
    
    return False

def check_webhook_status():
    """Проверяет текущий статус webhook и удаляет его при необходимости."""
    
    # Получаем токен из переменных окружения
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN не установлен")
        return False
    
    # URL для проверки информации о webhook
    api_url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
    
    try:
        # Отправляем запрос для получения информации о webhook
        logger.info("Проверка статуса webhook...")
        response = requests.get(api_url, timeout=10)
        
        # Проверяем ответ
        if response.status_code == 200:
            result = response.json()
            
            if result.get("ok"):
                webhook_info = result.get("result", {})
                webhook_url = webhook_info.get("url")
                
                if webhook_url:
                    logger.warning(f"⚠️ Обнаружен webhook: {webhook_url}")
                    
                    # Удаляем webhook
                    delete_url = f"https://api.telegram.org/bot{token}/deleteWebhook"
                    logger.info("Удаление webhook...")
                    
                    delete_response = requests.get(delete_url, timeout=10)
                    if delete_response.status_code == 200 and delete_response.json().get("ok"):
                        logger.info("✅ Webhook успешно удален")
                        return True
                    else:
                        logger.error(f"❌ Ошибка при удалении webhook: {delete_response.text}")
                        return False
                else:
                    logger.info("✅ Webhook не установлен")
                    return True
            else:
                logger.error(f"❌ API вернул ошибку: {result}")
        else:
            logger.error(f"❌ Ошибка запроса: Код {response.status_code}")
            logger.error(f"Ответ: {response.text}")
    
    except Exception as e:
        logger.error(f"❌ Исключение при запросе к API: {e}")
    
    return False

def send_test_message():
    """Отправляет тестовое сообщение для проверки работы бота."""
    
    # Получаем токен из переменных окружения
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN не установлен")
        return False

    # ID администратора или группы для тестирования
    chat_id = 5783753055  # ID пользователя avr3lia
    
    # URL для отправки сообщения
    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Данные для запроса
    data = {
        "chat_id": chat_id,
        "text": "🧪 Тестовое сообщение от бота Language Mirror\n\n" 
                "Это сообщение отправлено автоматически для проверки работоспособности "
                "бота и его подключения к Telegram API.\n\n"
                f"Время отправки: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    }
    
    try:
        # Отправляем запрос к API
        logger.info(f"Отправка тестового сообщения пользователю {chat_id}...")
        response = requests.post(api_url, data=data, timeout=10)
        
        # Проверяем ответ
        if response.status_code == 200:
            result = response.json()
            
            if result.get("ok"):
                logger.info("✅ Тестовое сообщение успешно отправлено")
                return True
            else:
                logger.error(f"❌ API вернул ошибку: {result}")
        else:
            logger.error(f"❌ Ошибка запроса: Код {response.status_code}")
            logger.error(f"Ответ: {response.text}")
    
    except Exception as e:
        logger.error(f"❌ Исключение при отправке сообщения: {e}")
    
    return False

def main():
    """Основная функция скрипта."""
    print("🔍 Проверка подключения к Telegram API...")
    
    # Проверяем возможность подключения к API
    if not check_telegram_api():
        print("❌ Ошибка подключения к Telegram API")
        print("Возможные причины:")
        print("1. Некорректный токен TELEGRAM_TOKEN")
        print("2. Проблемы с сетевым подключением")
        print("3. Блокировка API Telegram на стороне сервера")
        sys.exit(1)
    
    # Проверяем и удаляем webhook при необходимости
    if not check_webhook_status():
        print("❌ Ошибка при проверке/удалении webhook")
        sys.exit(1)
    
    # Отправляем тестовое сообщение
    if send_test_message():
        print("✅ Тестовое сообщение успешно отправлено администратору")
        print("Бот подключен и работает правильно")
    else:
        print("❌ Ошибка при отправке тестового сообщения")
        print("Проверьте логи для получения подробной информации")

if __name__ == "__main__":
    main()