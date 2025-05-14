"""
Административные инструменты для управления Language Mirror Bot с использованием Google Sheets.
"""
import os
import sys
import logging
import subprocess
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from io import BytesIO

from sheets_manager import SheetsManager

# Настройка логирования
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

def print_header(text):
    """Печатает заголовок для CLI меню"""
    print("\n" + "=" * 50)
    print(text.center(50))
    print("=" * 50)

def print_menu():
    """Печатает главное меню"""
    print_header("Language Mirror Bot - Административные инструменты")
    print("\n1. Проверить статус бота")
    print("2. Добавить тестовые данные обратной связи")
    print("3. Просмотреть данные обратной связи")
    print("4. Проверить переменные окружения")
    print("5. Запустить бота")
    print("6. Выгрузить отчет Excel")
    print("0. Выход")

def check_bot_status():
    """Проверяет статус бота, отправляя запрос к API"""
    try:
        # Проверяем наличие процесса бота
        pid = None
        if os.path.exists("bot.pid"):
            with open("bot.pid", "r") as f:
                pid = f.read().strip()
        
        if pid:
            try:
                # Проверяем, существует ли процесс с этим PID
                os.kill(int(pid), 0)
                print(f"\n✅ Бот запущен с PID {pid}")
            except (OSError, ProcessLookupError):
                print("\n❌ Бот не запущен (процесс не найден)")
        else:
            print("\n❌ Бот не запущен (файл PID не найден)")
    
    except Exception as e:
        print(f"\n❌ Ошибка при проверке статуса бота: {e}")

def add_test_feedback_menu():
    """Добавляет тестовые данные обратной связи"""
    try:
        print_header("Добавление тестовых данных обратной связи")
        
        sheets_manager = SheetsManager()
        
        while True:
            try:
                count = int(input("\nВведите количество тестовых отзывов (1-20): "))
                if 1 <= count <= 20:
                    break
                print("Пожалуйста, введите число от 1 до 20.")
            except ValueError:
                print("Пожалуйста, введите корректное число.")
        
        # Генерируем тестовые ID пользователей
        test_telegram_ids = [1000001 + i for i in range(5)]
        test_usernames = ["test_user1", "test_user2", "test_user3", "test_user4", "test_user5"]
        test_ratings = ["helpful", "okay", "not_helpful"]
        test_comments = [
            "Очень помогло с практикой английского",
            "Интересные темы для обсуждения",
            "Нужно больше объяснений по грамматике",
            "Мне понравилось, буду использовать регулярно",
            "Хороший инструмент для практики",
            "Можно улучшить распознавание ошибок",
            "",  # Пустой комментарий
            "Добавьте больше идиом и разговорных фраз"
        ]
        
        import random
        from datetime import datetime, timedelta
        
        # Генерируем тестовые данные и добавляем их
        for _ in range(count):
            telegram_id = random.choice(test_telegram_ids)
            username = test_usernames[test_telegram_ids.index(telegram_id)]
            rating = random.choice(test_ratings)
            comment = random.choice(test_comments)
            
            # Добавляем обратную связь
            sheets_manager.add_feedback(telegram_id, rating, comment)
        
        print(f"\n✅ Успешно добавлено {count} тестовых отзывов.")
    
    except Exception as e:
        print(f"\n❌ Ошибка при добавлении тестовых данных: {e}")

def view_feedback():
    """Показывает все данные обратной связи"""
    try:
        print_header("Данные обратной связи")
        
        sheets_manager = SheetsManager()
        feedback_items = sheets_manager.get_all_feedback()
        
        if not feedback_items:
            print("\nНет данных обратной связи.")
            return
        
        print(f"\nНайдено {len(feedback_items)} записей:\n")
        for item in feedback_items:
            timestamp = item.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    formatted_date = dt.strftime("%d.%m.%Y %H:%M")
                except (ValueError, TypeError):
                    formatted_date = timestamp
            else:
                formatted_date = "неизвестно"
            
            print(f"ID: {item.get('id', 'N/A')}")
            print(f"Пользователь: {item.get('username', 'N/A')} (Telegram ID: {item.get('telegram_id', 'N/A')})")
            print(f"Оценка: {item.get('rating', 'N/A')}")
            print(f"Комментарий: {item.get('comment', '')}")
            print(f"Дата: {formatted_date}")
            print("-" * 40)
    
    except Exception as e:
        print(f"\n❌ Ошибка при получении данных обратной связи: {e}")

def create_excel_report():
    """Создает Excel отчет с данными обратной связи"""
    try:
        print_header("Создание отчета Excel")
        
        sheets_manager = SheetsManager()
        feedback_items = sheets_manager.get_all_feedback()
        
        if not feedback_items:
            print("\nНет данных обратной связи для экспорта.")
            return
        
        # Конвертируем в pandas DataFrame
        df = pd.DataFrame(feedback_items)
        
        # Форматируем временные метки
        if "timestamp" in df.columns:
            try:
                df["formatted_date"] = pd.to_datetime(df["timestamp"]).dt.strftime("%d.%m.%Y %H:%M")
            except:
                df["formatted_date"] = df["timestamp"]
        
        # Определяем имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        directory = "reports"
        os.makedirs(directory, exist_ok=True)
        filename = f"{directory}/feedback_report_{timestamp}.xlsx"
        
        # Создаем writer для Excel
        writer = pd.ExcelWriter(filename, engine="xlsxwriter")
        
        # Записываем данные в Excel
        df.to_excel(writer, sheet_name="Feedback", index=False)
        
        # Получаем объект рабочего листа
        workbook = writer.book
        worksheet = writer.sheets["Feedback"]
        
        # Форматирование
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        # Форматируем заголовки
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, 15)
        
        # Устанавливаем ширину столбца для комментариев
        if "comment" in df.columns:
            comment_col = df.columns.get_loc("comment")
            worksheet.set_column(comment_col, comment_col, 40)
        
        # Сохраняем
        writer.close()
        
        print(f"\n✅ Отчет успешно создан: {filename}")
    
    except Exception as e:
        print(f"\n❌ Ошибка при создании отчета Excel: {e}")

def check_environment():
    """Проверяет переменные окружения"""
    print_header("Проверка переменных окружения")
    
    # Список необходимых переменных
    required_vars = {
        "TELEGRAM_TOKEN": "Токен Telegram API",
        "GOOGLE_CREDENTIALS_PATH": "Путь к файлу с учетными данными Google API",
        "GOOGLE_SHEETS_KEY": "Ключ таблицы Google Sheets",
        "OPENROUTER_API_KEY": "API ключ OpenRouter",
        "BOT_AUTO_START": "Автоматический запуск бота (true/false)"
    }
    
    # Опциональные переменные
    optional_vars = {
        "ADMIN_USER_ID": "ID администратора (Telegram)",
        "ADMIN_USERNAME": "Имя пользователя администратора (Telegram)",
        "DEBUG": "Режим отладки (true/false)"
    }
    
    print("\nНеобходимые переменные окружения:")
    all_required_present = True
    for var, desc in required_vars.items():
        value = os.environ.get(var)
        if value:
            masked_value = "***" if "TOKEN" in var or "KEY" in var or "PATH" in var else value
            status = "✅"
        else:
            masked_value = "не установлена"
            status = "❌"
            all_required_present = False
        
        print(f"{status} {var}: {masked_value} - {desc}")
    
    print("\nОпциональные переменные окружения:")
    for var, desc in optional_vars.items():
        value = os.environ.get(var)
        if value:
            masked_value = "***" if "TOKEN" in var or "KEY" in var else value
            status = "✅"
        else:
            masked_value = "не установлена"
            status = "⚠️"
        
        print(f"{status} {var}: {masked_value} - {desc}")
    
    if all_required_present:
        print("\n✅ Все необходимые переменные окружения установлены.")
    else:
        print("\n❌ Некоторые необходимые переменные окружения не установлены.")
        print("   Установите их перед запуском бота.")

def start_bot():
    """Запускает бот в отдельном процессе"""
    try:
        print_header("Запуск бота")
        
        # Проверяем, не запущен ли уже бот
        if os.path.exists("bot.pid"):
            with open("bot.pid", "r") as f:
                pid = f.read().strip()
            
            try:
                # Проверяем, существует ли процесс с этим PID
                os.kill(int(pid), 0)
                print(f"\n⚠️ Бот уже запущен с PID {pid}")
                
                restart = input("Хотите перезапустить бота? (y/n): ").lower()
                if restart != 'y':
                    return
                
                print(f"Остановка процесса {pid}...")
                try:
                    os.kill(int(pid), 15)  # SIGTERM
                    print(f"Процесс {pid} остановлен.")
                except (OSError, ProcessLookupError):
                    print(f"Процесс {pid} не найден, возможно уже остановлен.")
            except (OSError, ProcessLookupError):
                print(f"Процесс {pid} не найден, запускаем новый экземпляр бота.")
        
        # Запускаем бота
        print("\nЗапуск бота в фоновом режиме...")
        
        # Определяем, какой скрипт использовать в зависимости от ОС
        if os.name == 'posix':  # Linux, macOS
            subprocess.Popen(["nohup", "python", "run_bot_stable.py", "&"],
                             stdout=open("bot_output.txt", "a"),
                             stderr=open("bot_log.txt", "a"),
                             preexec_fn=os.setpgrp)
        else:  # Windows
            subprocess.Popen(["python", "run_bot_stable.py"],
                             stdout=open("bot_output.txt", "a"),
                             stderr=open("bot_log.txt", "a"),
                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        
        print("✅ Бот запущен в фоновом режиме.")
        print("   Логи сохраняются в файлах bot_output.txt и bot_log.txt")
    
    except Exception as e:
        print(f"\n❌ Ошибка при запуске бота: {e}")

def main():
    """Основная функция для запуска административных инструментов"""
    try:
        while True:
            print_menu()
            choice = input("\nВыберите действие (0-6): ")
            
            if choice == '0':
                print("\nВыход из административных инструментов.")
                sys.exit(0)
            elif choice == '1':
                check_bot_status()
            elif choice == '2':
                add_test_feedback_menu()
            elif choice == '3':
                view_feedback()
            elif choice == '4':
                check_environment()
            elif choice == '5':
                start_bot()
            elif choice == '6':
                create_excel_report()
            else:
                print("\n❌ Неверный выбор. Пожалуйста, выберите 0-6.")
            
            input("\nНажмите Enter для продолжения...")
    
    except KeyboardInterrupt:
        print("\n\nВыход из административных инструментов.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Произошла ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()