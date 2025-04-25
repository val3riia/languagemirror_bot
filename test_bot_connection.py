"""
Скрипт для проверки соединения с ботом Telegram.
Отправляет запрос к API Telegram, чтобы проверить, что бот подключен и работает.
"""
import logging
import os
import requests
import sys

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def check_bot_connection():
    """Проверяет подключение к боту Telegram"""
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN не найден в переменных окружения")
        return False
    
    logger.info("Проверяем подключение к боту Telegram...")
    try:
        # Отправляем запрос к методу getMe для проверки соединения
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe")
        data = response.json()
        
        if data.get("ok", False):
            bot_info = data.get("result", {})
            bot_username = bot_info.get("username", "Unknown")
            bot_id = bot_info.get("id", "Unknown")
            
            logger.info(f"Подключение установлено успешно!")
            logger.info(f"Имя бота: @{bot_username}")
            logger.info(f"ID бота: {bot_id}")
            return True
        else:
            error_description = data.get("description", "Неизвестная ошибка")
            logger.error(f"Ошибка при подключении к боту: {error_description}")
            return False
    except Exception as e:
        logger.error(f"Ошибка при проверке подключения: {e}")
        return False

def check_bot_process():
    """Проверяет, запущен ли процесс бота"""
    logger.info("Проверяем, запущен ли процесс бота...")
    
    try:
        # Проверяем наличие файла с PID
        if os.path.exists("bot.pid"):
            with open("bot.pid", "r") as file:
                pid = file.read().strip()
                
                if pid:
                    # Проверяем, существует ли процесс с этим PID
                    try:
                        os.kill(int(pid), 0)  # Не убивает процесс, просто проверяет его существование
                        logger.info(f"Процесс бота запущен (PID: {pid})")
                        return True
                    except OSError:
                        logger.warning(f"Процесс с PID {pid} не найден, хотя файл bot.pid существует")
                        return False
                else:
                    logger.warning("Файл bot.pid пуст")
                    return False
        else:
            logger.warning("Файл bot.pid не найден")
            
            # Альтернативный способ проверки
            import subprocess
            output = subprocess.check_output(["pgrep", "-f", "run_telegram_bot.py"]).decode().strip()
            
            if output:
                pids = output.split('\n')
                logger.info(f"Найдены процессы бота: {', '.join(pids)}")
                return True
            else:
                logger.warning("Процессы бота не найдены через pgrep")
                return False
    except Exception as e:
        logger.error(f"Ошибка при проверке процесса бота: {e}")
        return False

def main():
    """Основная функция"""
    logger.info("=== Проверка соединения с ботом Telegram ===")
    
    # Проверяем, запущен ли процесс бота
    process_running = check_bot_process()
    
    # Проверяем подключение к боту
    connection_ok = check_bot_connection()
    
    # Выводим итоговый статус
    print("\n=== Итоговый статус бота ===")
    print(f"Процесс бота запущен: {'ДА' if process_running else 'НЕТ'}")
    print(f"Подключение к Telegram API: {'ДА' if connection_ok else 'НЕТ'}")
    
    if process_running and connection_ok:
        print("\nБот работает нормально!")
        return 0
    else:
        print("\nОбнаружены проблемы в работе бота!")
        print("Рекомендуется перезапустить бота с помощью команды: ./start_bot_stable.sh")
        return 1

if __name__ == "__main__":
    sys.exit(main())