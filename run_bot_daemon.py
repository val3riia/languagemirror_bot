#!/usr/bin/env python3
"""
Демон для поддержания работы Telegram бота.
Этот скрипт запускает бота в отдельном процессе и постоянно мониторит его состояние.
При падении бота, он автоматически перезапускается.
"""
import logging
import os
import signal
import subprocess
import sys
import time
import requests
from datetime import datetime

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot_daemon.log')
    ]
)
logger = logging.getLogger(__name__)

def delete_webhook():
    """Удаляет webhook в Telegram API для предотвращения конфликтов."""
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
        logger.error(f"Ошибка при удалении webhook: {str(e)}")
        return False

def kill_existing_bots():
    """Находит и останавливает все процессы бота."""
    logger.info("Ищем и останавливаем существующие процессы бота...")
    try:
        # Ищем процессы Python, в командной строке которых есть ключевые слова
        cmd = "ps aux | grep -E 'telebot|language_mirror|run_telegram' | grep -v grep | awk '{print $2}'"
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        output, _ = process.communicate()
        
        pids = output.decode().strip().split('\n')
        current_pid = os.getpid()
        
        for pid in pids:
            if pid and pid.isdigit():
                pid = int(pid)
                # Не останавливаем текущий процесс
                if pid != current_pid:
                    try:
                        os.kill(pid, signal.SIGTERM)
                        logger.info(f"Остановлен процесс бота с PID {pid}")
                    except ProcessLookupError:
                        pass
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при остановке процессов бота: {str(e)}")
        return False

def start_bot():
    """Запускает Telegram бота в отдельном процессе."""
    logger.info("Запускаем бота...")
    
    try:
        # Запускаем run_telegram_bot.py в отдельном процессе
        process = subprocess.Popen([sys.executable, "run_telegram_bot.py"],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        
        # Сохраняем PID в файл
        with open("bot.pid", "w") as f:
            f.write(str(process.pid))
        
        logger.info(f"Бот запущен с PID {process.pid}")
        return process
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {str(e)}")
        return None

def check_bot_status(process):
    """Проверяет статус бота и возвращает True, если бот работает."""
    if process is None:
        return False
    
    # Проверяем, жив ли процесс
    return process.poll() is None

def main():
    """Основная функция для запуска и мониторинга бота."""
    logger.info("=== Запуск демона мониторинга бота ===")
    
    # Останавливаем все существующие процессы бота
    kill_existing_bots()
    
    # Удаляем webhook
    delete_webhook()
    
    # Запускаем бота
    bot_process = start_bot()
    if not bot_process:
        logger.error("Не удалось запустить бота, выход")
        return 1
    
    # Время последнего перезапуска
    last_restart = time.time()
    
    # Счетчик перезапусков
    restart_count = 0
    
    # Основной цикл мониторинга
    logger.info("Запуск цикла мониторинга бота")
    try:
        while True:
            # Проверяем статус бота
            if not check_bot_status(bot_process):
                # Если прошло меньше 10 секунд с последнего перезапуска, ждем
                current_time = time.time()
                if current_time - last_restart < 10:
                    restart_count += 1
                    
                    # Если было слишком много быстрых перезапусков, делаем более длительную паузу
                    if restart_count > 3:
                        logger.warning(f"Слишком много перезапусков ({restart_count}), ожидание 60 секунд")
                        time.sleep(60)
                        restart_count = 0
                else:
                    restart_count = 0
                
                logger.warning(f"Бот остановлен, перезапускаем... (PID: {bot_process.pid})")
                
                # Получаем последние логи для отладки
                stdout, stderr = bot_process.communicate()
                logger.info(f"Последний вывод бота: {stdout.decode()}")
                if stderr:
                    logger.error(f"Ошибки бота: {stderr.decode()}")
                
                # Перезапускаем бота
                bot_process = start_bot()
                last_restart = time.time()
                
                if not bot_process:
                    logger.error("Не удалось перезапустить бота после сбоя")
                    time.sleep(30)  # Ждем перед следующей попыткой
            
            # Записываем в лог информацию о состоянии бота каждый час
            current_hour = datetime.now().hour
            if not hasattr(main, "last_log_hour") or main.last_log_hour != current_hour:
                logger.info(f"Бот работает нормально (PID: {bot_process.pid})")
                main.last_log_hour = current_hour
            
            # Ждем перед следующей проверкой
            time.sleep(5)
    except KeyboardInterrupt:
        logger.info("Демон мониторинга остановлен пользователем")
        if bot_process and bot_process.poll() is None:
            bot_process.terminate()
            logger.info(f"Бот остановлен (PID: {bot_process.pid})")
    except Exception as e:
        logger.error(f"Неожиданная ошибка в демоне мониторинга: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())