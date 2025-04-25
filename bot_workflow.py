#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Обертка для запуска бота Telegram в workflow Replit.
Этот скрипт будет импортировать и запускать основной бот в бесконечном цикле,
с обработкой исключений и повторными попытками в случае сбоев.
"""

import os
import sys
import time
import logging
import traceback

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

def run_bot():
    """Запускает основной бот"""
    # Импортируем бота
    try:
        logger.info("Импорт модуля language_mirror_telebot...")
        import language_mirror_telebot
        
        # Запуск основной функции бота
        logger.info("Запуск main() функции бота...")
        language_mirror_telebot.main()
        
        logger.info("Основная функция бота завершилась")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        logger.error(traceback.format_exc())
        return False
    
    return True

def main():
    """Основная функция скрипта"""
    print("=" * 70)
    print("Запуск Language Mirror Bot в режиме workflow")
    print("=" * 70)
    
    # Проверка переменных окружения
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN не установлен! Бот не может быть запущен.")
        print("❌ ОШИБКА: TELEGRAM_TOKEN не установлен!")
        print("Установите токен бота в переменных окружения Replit")
        sys.exit(1)
    
    # Запуск бота с повторными попытками при сбоях
    retry_count = 0
    max_retries = 10  # Максимальное количество быстрых повторных попыток
    
    while True:
        try:
            logger.info(f"Запуск бота (попытка #{retry_count + 1})...")
            
            # Запускаем бота
            success = run_bot()
            
            if not success:
                # Увеличиваем счетчик повторных попыток
                retry_count += 1
                
                # Если слишком много быстрых повторов, делаем длинную паузу
                if retry_count > max_retries:
                    logger.warning(f"Достигнуто максимальное количество повторных попыток ({max_retries}). Длинная пауза.")
                    print(f"⚠️ Достигнуто максимальное количество повторных попыток. Пауза 300 секунд...")
                    time.sleep(300)  # 5 минут пауза
                    retry_count = 0  # Сбрасываем счетчик
                else:
                    # Короткая пауза между повторами
                    backoff = min(60, 5 * (2 ** retry_count))  # Экспоненциальная задержка, максимум 60 секунд
                    logger.info(f"Пауза перед повторной попыткой: {backoff} секунд")
                    print(f"⏱️ Пауза перед повторной попыткой: {backoff} секунд...")
                    time.sleep(backoff)
            else:
                # Если бот завершился нормально, делаем паузу и перезапускаем
                logger.info("Бот завершил работу нормально. Перезапуск через 5 секунд...")
                time.sleep(5)
                retry_count = 0  # Сбрасываем счетчик повторов
        
        except KeyboardInterrupt:
            logger.info("Получен сигнал прерывания. Завершение работы.")
            print("\n🛑 Получен сигнал прерывания. Завершение работы.")
            break
        
        except Exception as e:
            logger.error(f"Неожиданная ошибка в main(): {e}")
            logger.error(traceback.format_exc())
            print(f"❌ Неожиданная ошибка: {e}")
            
            # Увеличиваем счетчик повторных попыток
            retry_count += 1
            
            # Пауза перед повторной попыткой
            backoff = min(60, 5 * (2 ** retry_count))
            print(f"⏱️ Пауза перед повторной попыткой: {backoff} секунд...")
            time.sleep(backoff)

if __name__ == "__main__":
    main()