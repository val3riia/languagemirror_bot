"""
Скрипт для запуска Telegram-бота как рабочего процесса Replit.
Этот скрипт запускает бота и поддерживает его работу, запуская его заново
в случае ошибок.
"""
import logging
import os
import subprocess
import sys
import time
import requests
import threading

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def delete_webhook():
    """Удаляет webhook в Telegram API, чтобы освободить бота для polling"""
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN не найден в переменных окружения")
        return False
    
    logger.info("Удаляем webhook в Telegram API...")
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/deleteWebhook")
        data = response.json()
        
        if data.get("ok", False):
            logger.info("Webhook успешно удален")
            return True
        else:
            logger.error(f"Ошибка при удалении webhook: {data}")
            return False
    except Exception as e:
        logger.error(f"Ошибка при удалении webhook: {e}")
        return False

def stop_all_bot_processes():
    """Останавливает все существующие процессы бота"""
    logger.info("Останавливаем все существующие процессы бота...")
    
    # Ищем процессы, которые содержат в названии ключевые слова
    keywords = ["python run_telegram_bot", "language_mirror_telebot", "telebot", "bot.py"]
    
    for keyword in keywords:
        try:
            result = subprocess.run(
                ["pgrep", "-f", keyword],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                
                for pid in pids:
                    try:
                        # Не убиваем текущий процесс
                        if int(pid) != os.getpid():
                            os.kill(int(pid), 9)
                            logger.info(f"Остановлен процесс {pid} ({keyword})")
                    except (ValueError, ProcessLookupError):
                        pass
        except Exception as e:
            logger.error(f"Ошибка при остановке процессов: {e}")
    
    logger.info("Все существующие процессы бота остановлены")

def start_bot():
    """Запускает бота через run_telegram_bot.py"""
    logger.info("Запускаем телеграм-бота...")
    
    try:
        # Запускаем бот в отдельном процессе
        process = subprocess.Popen(
            ["python", "run_telegram_bot.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Читаем и логируем вывод бота
        def log_output():
            for line in process.stdout:
                logger.info(f"Bot output: {line.strip()}")
        
        # Запускаем чтение вывода в отдельном потоке
        threading.Thread(target=log_output, daemon=True).start()
        
        # Ждем некоторое время, чтобы убедиться, что бот запустился
        time.sleep(5)
        
        # Проверяем, что процесс все еще работает
        if process.poll() is None:
            logger.info(f"Бот успешно запущен с PID {process.pid}")
            return process
        else:
            logger.error(f"Не удалось запустить бота, код возврата: {process.returncode}")
            return None
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        return None

def run_bot_with_monitoring():
    """Запускает бота и перезапускает его в случае остановки"""
    # Начальная задержка для стабилизации системы
    time.sleep(1)
    
    # Удаляем webhook и запускаем бота
    delete_webhook()
    bot_process = start_bot()
    
    if not bot_process:
        logger.error("Не удалось запустить бота")
        return
    
    # Мониторим процесс бота и перезапускаем его при необходимости
    try:
        while True:
            # Проверяем, работает ли процесс бота
            if bot_process.poll() is not None:
                logger.warning(f"Бот остановился с кодом {bot_process.returncode}, перезапускаем...")
                time.sleep(5)  # Даем системе время для освобождения ресурсов
                delete_webhook()  # На всякий случай снова удаляем webhook
                bot_process = start_bot()
                
                if not bot_process:
                    logger.error("Не удалось перезапустить бота, пробуем снова через 30 секунд")
                    time.sleep(30)
                    continue
            
            # Спим некоторое время перед проверкой снова
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания, останавливаем бота...")
        if bot_process:
            bot_process.terminate()
    except Exception as e:
        logger.error(f"Ошибка в мониторинге бота: {e}")
        if bot_process:
            bot_process.terminate()

def main():
    """Основная функция скрипта"""
    logger.info("=== Запуск Telegram-бота как рабочего процесса Replit ===")
    
    # Останавливаем все существующие процессы бота
    stop_all_bot_processes()
    
    # Запускаем бота с мониторингом
    run_bot_with_monitoring()

if __name__ == "__main__":
    main()