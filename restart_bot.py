"""
Скрипт для принудительной остановки webhook и перезапуска бота.
"""
import os
import signal
import logging
import subprocess
import time
import requests

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def stop_all_bots():
    """Останавливает все процессы бота"""
    logger.info("Остановка всех процессов бота...")
    
    # Убиваем все процессы, содержащие 'telebot' или 'bot.py' в командной строке
    try:
        subprocess.run(["pkill", "-f", "python.*telebot\\|python.*bot.py"], 
                      check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info("Все процессы бота остановлены")
    except Exception as e:
        logger.warning(f"Ошибка при остановке процессов: {e}")

def delete_webhook():
    """Удаляет webhook в Telegram API"""
    logger.info("Удаление webhook в Telegram API...")
    
    # Получаем токен Telegram из переменных окружения
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN не найден в переменных окружения!")
        return False
    
    # Формируем URL для удаления webhook
    url = f"https://api.telegram.org/bot{token}/deleteWebhook"
    
    try:
        # Отправляем запрос на удаление webhook
        response = requests.get(url)
        data = response.json()
        
        if data.get("ok", False):
            logger.info("Webhook успешно удален")
            return True
        else:
            logger.error(f"Ошибка при удалении webhook: {data}")
            return False
    except Exception as e:
        logger.error(f"Ошибка запроса к Telegram API: {e}")
        return False

def restart_bot():
    """Перезапускает бота в отдельном процессе"""
    logger.info("Перезапуск бота...")
    
    try:
        # Запускаем бота в отдельном процессе, чтобы он не блокировал выполнение скрипта
        subprocess.Popen(["python", "run_telegram_bot.py"], 
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info("Бот запущен в отдельном процессе")
        return True
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        return False

def main():
    """Основная функция для перезапуска бота"""
    logger.info("=== Перезапуск Telegram бота ===")
    
    # Останавливаем все запущенные экземпляры бота
    stop_all_bots()
    
    # Ждем немного для полной остановки процессов
    time.sleep(2)
    
    # Удаляем webhook
    if not delete_webhook():
        logger.warning("Не удалось удалить webhook, но продолжаем...")
    
    # Ждем еще немного
    time.sleep(2)
    
    # Перезапускаем бота
    if restart_bot():
        logger.info("Бот успешно перезапущен!")
    else:
        logger.error("Не удалось перезапустить бота")
    
    logger.info("=== Скрипт перезапуска завершен ===")

if __name__ == "__main__":
    main()