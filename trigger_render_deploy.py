#!/usr/bin/env python3
"""
Скрипт для запуска деплоя на Render.
Этот скрипт отправляет запрос на URL деплоя Render, чтобы инициировать новый деплой.
"""

import os
import requests
import logging
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def trigger_deploy(deploy_url=None):
    """
    Отправляет POST-запрос на URL деплоя Render.
    
    Args:
        deploy_url: URL для деплоя (по умолчанию берется из переменной окружения WEBHOOK_URL)
    """
    if not deploy_url:
        deploy_url = os.environ.get("WEBHOOK_URL")
        if not deploy_url:
            logger.error("WEBHOOK_URL not set in environment variables")
            return False
    
    logger.info(f"Triggering deploy using URL: {deploy_url}")
    
    try:
        response = requests.post(deploy_url)
        response.raise_for_status()
        
        logger.info(f"Deploy triggered successfully! Status code: {response.status_code}")
        logger.info(f"Response: {response.text}")
        
        return True
    except Exception as e:
        logger.error(f"Error triggering deploy: {e}")
        return False

def main():
    """
    Основная функция скрипта.
    """
    # Если URL указан в аргументах командной строки, используем его
    deploy_url = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Запускаем деплой
    result = trigger_deploy(deploy_url)
    
    if result:
        print("✅ Deploy triggered successfully!")
    else:
        print("❌ Failed to trigger deploy. Check logs for details.")

if __name__ == "__main__":
    main()