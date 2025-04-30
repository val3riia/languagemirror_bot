"""
Скрипт для исправления конфликтов между несколькими экземплярами бота.
Останавливает все запущенные экземпляры бота и запускает только один экземпляр.
"""
import logging
import os
import signal
import subprocess
import sys
import time
import requests

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def stop_all_bots():
    """Останавливает все запущенные экземпляры бота"""
    logger.info("Останавливаем все процессы бота...")
    
    # Ищем процессы бота по ключевым словам
    keywords = ["telebot", "telegram", "bot.py", "run_telegram", "language_mirror"]
    
    for keyword in keywords:
        try:
            output = subprocess.check_output(["pgrep", "-f", keyword]).decode().strip()
            if output:
                pids = output.split('\n')
                for pid in pids:
                    try:
                        pid = int(pid)
                        # Не убиваем текущий процесс
                        if pid != os.getpid():
                            os.kill(pid, signal.SIGTERM)
                            logger.info(f"Остановлен процесс бота с PID {pid} (по ключевому слову '{keyword}')")
                    except (ValueError, ProcessLookupError):
                        pass
        except subprocess.CalledProcessError:
            # pgrep не нашел процессов
            pass
    
    logger.info("Все процессы бота остановлены")

def delete_webhook():
    """Удаляет webhook в Telegram API"""
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
            logger.error("Ошибка при удалении webhook")
            return False
    except Exception:
        logger.error("Ошибка при удалении webhook")
        return False

def start_bot():
    """Запускает один экземпляр бота"""
    logger.info("Запускаем бота...")
    
    # Определяем команду для запуска бота
    command = ["python", "run_telegram_bot.py"]
    
    try:
        # Запускаем бота в отдельном процессе
        process = subprocess.Popen(command)
        
        # Ждем немного, чтобы убедиться, что бот запустился
        time.sleep(5)
        
        # Проверяем, что процесс все еще работает
        if process.poll() is None:
            logger.info(f"Бот успешно запущен с PID {process.pid}")
            return True
        else:
            logger.error(f"Бот не смог запуститься, код возврата: {process.returncode}")
            return False
    except Exception:
        logger.error("Ошибка при запуске бота")
        return False

def main():
    """Основная функция"""
    logger.info("=== Исправление конфликтов бота ===")
    
    # Останавливаем все запущенные экземпляры бота
    stop_all_bots()
    
    # Даем время для завершения процессов
    time.sleep(2)
    
    # Удаляем webhook в Telegram API
    delete_webhook()
    
    # Даем время для завершения удаления webhook
    time.sleep(2)
    
    # Запускаем один экземпляр бота
    if start_bot():
        logger.info("Бот успешно запущен без конфликтов")
        return 0
    else:
        logger.error("Не удалось запустить бота")
        return 1

if __name__ == "__main__":
    sys.exit(main())