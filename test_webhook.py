#!/usr/bin/env python3
"""
Скрипт для проверки состояния webhook в Telegram API.
Этот скрипт позволяет проверить, правильно ли настроен webhook для бота.
"""

import os
import requests
import json
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_webhook_info():
    """
    Проверяет информацию о текущем webhook.
    """
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN not set in environment variables")
        return False
    
    url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        webhook_info = response.json()
        
        if response.status_code == 200 and webhook_info.get("ok"):
            result = webhook_info.get("result", {})
            
            print("\n=== Webhook Information ===")
            print(f"URL: {result.get('url')}")
            print(f"Has Custom Certificate: {result.get('has_custom_certificate')}")
            print(f"Pending Update Count: {result.get('pending_update_count')}")
            
            if result.get("last_error_date"):
                import datetime
                error_date = datetime.datetime.fromtimestamp(result.get("last_error_date"))
                print(f"Last Error Date: {error_date}")
                print(f"Last Error Message: {result.get('last_error_message')}")
            
            print(f"Max Connections: {result.get('max_connections')}")
            print(f"IP Address: {result.get('ip_address')}")
            print("==========================\n")
            
            if result.get("url"):
                logger.info(f"Webhook is set to: {result.get('url')}")
                return True
            else:
                logger.warning("No webhook URL is set")
                return False
        else:
            logger.error(f"Failed to get webhook info: {webhook_info}")
            return False
    
    except Exception as e:
        logger.error(f"Error checking webhook: {e}")
        return False

def set_webhook(webhook_url=None):
    """
    Устанавливает webhook для бота.
    
    Args:
        webhook_url: URL для установки webhook (по умолчанию использует WEBHOOK_URL из переменных окружения)
    """
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN not set in environment variables")
        return False
    
    if not webhook_url:
        webhook_url = os.environ.get("WEBHOOK_URL")
        if not webhook_url:
            logger.error("WEBHOOK_URL not set in environment variables")
            return False
    
    url = f"https://api.telegram.org/bot{token}/setWebhook"
    params = {"url": webhook_url}
    
    try:
        response = requests.post(url, json=params)
        response.raise_for_status()
        
        result = response.json()
        
        if response.status_code == 200 and result.get("ok"):
            logger.info(f"Webhook successfully set to: {webhook_url}")
            return True
        else:
            logger.error(f"Failed to set webhook: {result}")
            return False
    
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        return False

def delete_webhook():
    """
    Удаляет webhook для бота.
    """
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN not set in environment variables")
        return False
    
    url = f"https://api.telegram.org/bot{token}/deleteWebhook"
    
    try:
        response = requests.post(url)
        response.raise_for_status()
        
        result = response.json()
        
        if response.status_code == 200 and result.get("ok"):
            logger.info("Webhook successfully deleted")
            return True
        else:
            logger.error(f"Failed to delete webhook: {result}")
            return False
    
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")
        return False

def print_help():
    """
    Выводит справку по использованию скрипта.
    """
    print("\nWebhook Test Script")
    print("------------------")
    print("Usage:")
    print("  python test_webhook.py info   - Check current webhook information")
    print("  python test_webhook.py set    - Set webhook using WEBHOOK_URL from environment")
    print("  python test_webhook.py set URL - Set webhook to specified URL")
    print("  python test_webhook.py delete - Delete current webhook")
    print("  python test_webhook.py help   - Show this help message")

def main():
    """
    Основная функция скрипта.
    """
    import sys
    
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "info":
        check_webhook_info()
    elif command == "set":
        webhook_url = sys.argv[2] if len(sys.argv) > 2 else None
        set_webhook(webhook_url)
        check_webhook_info()
    elif command == "delete":
        delete_webhook()
        check_webhook_info()
    elif command == "help":
        print_help()
    else:
        print(f"Unknown command: {command}")
        print_help()

if __name__ == "__main__":
    main()