#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Запуск бота Telegram в фоновом режиме.
Этот скрипт запускает бот в отдельном процессе и возвращает управление
для более удобного использования в Replit.
"""

import os
import time
import subprocess
import logging
import sys

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    # Проверка наличия TELEGRAM_TOKEN
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN не установлен в переменных окружения!")
        print("Ошибка: TELEGRAM_TOKEN не установлен!")
        sys.exit(1)
    
    # Убиваем предыдущие процессы бота, если они существуют
    try:
        print("🔄 Останавливаем предыдущие процессы бота...")
        subprocess.run("pkill -f 'python.*language_mirror' || true", shell=True)
        subprocess.run("pkill -f 'python.*run_bot' || true", shell=True)
        subprocess.run("pkill -f 'python.*telebot' || true", shell=True)
        time.sleep(2)
    except Exception as e:
        logger.warning(f"Ошибка при остановке предыдущих процессов: {e}")
    
    # Запускаем бот в фоновом режиме с редиректом вывода в лог
    try:
        print("🚀 Запускаем бот в фоновом режиме...")
        log_file = "bot_log.txt"
        bot_process = subprocess.Popen(
            ["python", "run_directly.py"], 
            stdout=open(log_file, "a"),
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Ждем немного, чтобы проверить, запустился ли процесс успешно
        time.sleep(3)
        
        # Проверяем, работает ли процесс
        if bot_process.poll() is None:
            print(f"✅ Бот успешно запущен в фоновом режиме (PID: {bot_process.pid})")
            print(f"📝 Логи бота записываются в файл: {log_file}")
            print("\nДля проверки работы бота:")
            print("1. Откройте Telegram")
            print("2. Найдите вашего бота по имени пользователя")
            print("3. Отправьте команду /start чтобы начать общение")
            print("\nВажно: бот продолжит работать в фоновом режиме.")
            print("Чтобы остановить бота, выполните команду: pkill -f 'python.*telebot'")
        else:
            print("❌ Ошибка: не удалось запустить бота в фоновом режиме")
            print("Проверьте файл лога для получения дополнительной информации")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        print(f"❌ Ошибка при запуске бота: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()