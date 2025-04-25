#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для запуска и поддержания работы бота Telegram.
Этот скрипт будет запускать бота в отдельном процессе и перезапускать
его в случае сбоя.
"""

import os
import sys
import time
import subprocess
import logging
import signal
import datetime

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Создаем папку для логов
os.makedirs("logs", exist_ok=True)

# Путь к лог-файлу
log_file = f"logs/bot_{time.strftime('%Y%m%d_%H%M%S')}.log"

# Функция для запуска бота
def start_bot():
    """Запускает бота и возвращает процесс"""
    try:
        # Проверка наличия токена Telegram
        if not os.environ.get("TELEGRAM_TOKEN"):
            logger.error("TELEGRAM_TOKEN не установлен в переменных окружения")
            return None
        
        # Запуск бота с перенаправлением вывода в лог-файл
        logger.info(f"Запуск бота: python language_mirror_telebot.py > {log_file} 2>&1")
        process = subprocess.Popen(
            ["python", "language_mirror_telebot.py"],
            stdout=open(log_file, "a"),
            stderr=subprocess.STDOUT,
            # Используем preexec_fn для создания нового сеанса
            preexec_fn=os.setpgrp
        )
        
        # Запись PID в файл
        with open("bot.pid", "w") as pid_file:
            pid_file.write(str(process.pid))
        
        logger.info(f"Бот запущен с PID: {process.pid}")
        return process
    
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        return None

# Функция для остановки всех существующих процессов бота
def stop_existing_bots():
    """Останавливает все существующие процессы бота"""
    try:
        # Остановка по PID файлу
        if os.path.exists("bot.pid"):
            with open("bot.pid", "r") as pid_file:
                pid = int(pid_file.read().strip())
                
                try:
                    # Отправляем сигнал SIGTERM для корректного завершения
                    os.kill(pid, signal.SIGTERM)
                    logger.info(f"Отправлен сигнал SIGTERM процессу {pid}")
                    
                    # Даем время на завершение
                    time.sleep(2)
                    
                    # Если процесс все еще жив, используем SIGKILL
                    try:
                        os.kill(pid, 0)  # Проверка наличия процесса
                        os.kill(pid, signal.SIGKILL)
                        logger.info(f"Отправлен сигнал SIGKILL процессу {pid}")
                    except OSError:
                        pass  # Процесс уже завершен
                    
                except OSError:
                    logger.info(f"Процесс с PID {pid} не найден")
            
            # Удаляем файл PID
            os.remove("bot.pid")
        
        # Также ищем и останавливаем все запущенные процессы по имени файла
        # Это резервный механизм, если PID-файл некорректен
        try:
            subprocess.run(
                ["pkill", "-f", "python.*language_mirror.*"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            logger.info("Остановлены все процессы с именем 'python.*language_mirror.*'")
        except Exception as e:
            logger.error(f"Ошибка при остановке процессов по имени: {e}")
    
    except Exception as e:
        logger.error(f"Ошибка при остановке существующих ботов: {e}")

def main():
    """Основная функция для запуска и мониторинга бота"""
    
    print("=" * 60)
    print("🤖 Запуск и мониторинг Language Mirror Bot")
    print("=" * 60)
    
    # Остановка всех существующих ботов
    stop_existing_bots()
    
    # Запуск бота
    bot_process = start_bot()
    if not bot_process:
        print("❌ Не удалось запустить бота. Проверьте логи.")
        sys.exit(1)
    
    print(f"✅ Бот успешно запущен (PID: {bot_process.pid})")
    print(f"📝 Логи сохраняются в файл: {log_file}")
    print("🔄 Мониторинг статуса бота...")
    print("-" * 60)
    
    # Мониторинг бота
    try:
        while True:
            # Проверяем статус процесса
            status = bot_process.poll()
            
            # Если процесс завершился (status не None)
            if status is not None:
                logger.warning(f"Бот завершил работу с кодом {status}. Перезапуск...")
                print(f"⚠️ Бот завершил работу с кодом {status}. Перезапуск...")
                
                # Небольшая задержка перед перезапуском
                time.sleep(5)
                
                # Перезапуск бота
                bot_process = start_bot()
                if not bot_process:
                    logger.error("Не удалось перезапустить бота")
                    print("❌ Не удалось перезапустить бота. Проверьте логи.")
                    sys.exit(1)
                
                print(f"✅ Бот успешно перезапущен (PID: {bot_process.pid})")
            
            # Выводим на экран только каждые 10 минут (для снижения нагрузки)
            if datetime.datetime.now().minute % 10 == 0 and datetime.datetime.now().second == 0:
                print(f"✅ Бот активен (PID: {bot_process.pid}). Текущее время: {datetime.datetime.now().strftime('%H:%M:%S')}")
            
            # Пауза перед следующей проверкой
            time.sleep(1)
    
    except KeyboardInterrupt:
        # Обработка Ctrl+C для корректного завершения
        print("\n🛑 Получен сигнал остановки. Завершение работы бота...")
        if bot_process:
            bot_process.terminate()
            bot_process.wait(timeout=5)
        
        print("✅ Бот остановлен")
    
    except Exception as e:
        logger.error(f"Неожиданная ошибка в мониторинге: {e}")
        print(f"❌ Неожиданная ошибка: {e}")
        
        # Останавливаем бота при ошибке
        if bot_process:
            bot_process.terminate()
            bot_process.wait(timeout=5)
        
        sys.exit(1)

if __name__ == "__main__":
    main()