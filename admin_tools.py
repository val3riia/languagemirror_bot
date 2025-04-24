#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Административные инструменты для управления Language Mirror Bot.
"""

import os
import sys
import json
import requests
import subprocess
from datetime import datetime

from add_test_feedback import add_test_feedback

def print_header(text):
    """Печатает заголовок для CLI меню"""
    width = 60
    print("\n" + "=" * width)
    print(f"{text.center(width)}")
    print("=" * width + "\n")

def print_menu():
    """Печатает главное меню"""
    print_header("LANGUAGE MIRROR BOT - ADMIN TOOLS")
    
    print("1. Check Bot Status")
    print("2. Add Test Feedback Data")
    print("3. View Feedback")
    print("4. Check Environment")
    print("5. Start Bot")
    print("0. Exit")
    
    print("\n" + "-" * 60)

def check_bot_status():
    """Проверяет статус бота, отправляя запрос к API"""
    print_header("BOT STATUS CHECK")
    
    try:
        # Проверка, запущен ли сервер Flask
        response = requests.get("http://localhost:5000/api/status", timeout=2)
        
        if response.status_code == 200:
            status = response.json()
            print(f"✓ Web server is running")
            print(f"  - Server time: {status.get('server_time')}")
            print(f"  - Uptime: {status.get('uptime', 'N/A')}")
            print(f"  - Database connected: {status.get('db_connected', False)}")
            print(f"  - Bot active: {status.get('bot_active', False)}")
            
            # Показываем статистику, если есть
            stats = status.get("stats", {})
            if stats:
                print("\nSTATISTICS:")
                print(f"  - Users: {stats.get('users_count', 0)}")
                print(f"  - Sessions: {stats.get('sessions_count', 0)}")
                print(f"  - Active sessions: {stats.get('active_sessions', 0)}")
                print(f"  - Messages: {stats.get('messages_count', 0)}")
                print(f"  - Feedback entries: {stats.get('feedback_count', 0)}")
        else:
            print(f"✗ Web server returned status code: {response.status_code}")
    
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to server. Is the Flask server running?")
        print("  Run 'python main.py' in a separate terminal to start the server.")
    except Exception as e:
        print(f"✗ Error checking bot status: {e}")
    
    input("\nPress Enter to return to the menu...")

def add_test_feedback_menu():
    """Добавляет тестовые данные обратной связи"""
    print_header("ADD TEST FEEDBACK DATA")
    
    if not os.environ.get("DATABASE_URL"):
        print("✗ DATABASE_URL environment variable is not set.")
        print("  Please set it to connect to your PostgreSQL database.")
        input("\nPress Enter to return to the menu...")
        return
    
    try:
        count = input("How many feedback entries to add? (default: 10): ")
        count = int(count) if count else 10
        
        if count <= 0:
            print("✗ Count must be greater than 0.")
            input("\nPress Enter to return to the menu...")
            return
        
        print(f"\nAdding {count} test feedback entries...")
        add_test_feedback(count)
        print("✓ Test data added successfully!")
    
    except ValueError:
        print("✗ Please enter a valid number.")
    except Exception as e:
        print(f"✗ Error adding test feedback: {e}")
    
    input("\nPress Enter to return to the menu...")

def view_feedback():
    """Показывает все данные обратной связи"""
    print_header("VIEW FEEDBACK")
    
    try:
        response = requests.get("http://localhost:5000/api/feedback", timeout=5)
        
        if response.status_code == 200:
            feedback_data = response.json().get("feedback", [])
            
            if not feedback_data:
                print("No feedback data found.")
                input("\nPress Enter to return to the menu...")
                return
            
            print(f"Showing {len(feedback_data)} feedback entries:\n")
            
            for i, feedback in enumerate(feedback_data):
                rating = feedback.get("rating", "unknown")
                comment = feedback.get("comment", "No comment")
                username = feedback.get("username", "Anonymous")
                timestamp = feedback.get("timestamp", "Unknown time")
                
                rating_symbol = "👍" if rating == "helpful" else "🤔" if rating == "okay" else "👎"
                
                print(f"{i+1}. {rating_symbol} {rating.upper()} from {username} at {timestamp}")
                print(f"   \"{comment}\"")
                print()
            
        else:
            print(f"✗ Could not fetch feedback data. Status code: {response.status_code}")
    
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to server. Is the Flask server running?")
    except Exception as e:
        print(f"✗ Error viewing feedback: {e}")
    
    input("\nPress Enter to return to the menu...")

def check_environment():
    """Проверяет переменные окружения"""
    print_header("ENVIRONMENT CHECK")
    
    # Проверка ключевых переменных окружения
    variables = {
        "TELEGRAM_TOKEN": "Telegram Bot Token",
        "DATABASE_URL": "Database Connection URL"
    }
    
    all_good = True
    
    for var, description in variables.items():
        value = os.environ.get(var)
        if value:
            masked_value = value[:3] + "*" * (len(value) - 6) + value[-3:] if len(value) > 6 else "***"
            print(f"✓ {description} ({var}): {masked_value}")
        else:
            all_good = False
            print(f"✗ {description} ({var}): Not set")
    
    if not all_good:
        print("\nSome environment variables are missing. This may cause problems.")
        print("Use these commands to set them (replace values with your actual data):")
        
        for var in variables:
            if not os.environ.get(var):
                print(f"  export {var}=your_{var.lower()}_here")
    
    # Проверка установленных библиотек
    print("\nChecking required Python libraries:")
    
    libraries = [
        "flask", "flask_sqlalchemy", "telebot", "sqlalchemy", "requests"
    ]
    
    for lib in libraries:
        try:
            __import__(lib)
            print(f"✓ {lib} is installed")
        except ImportError:
            all_good = False
            print(f"✗ {lib} is NOT installed. Install it with: pip install {lib}")
    
    if all_good:
        print("\n✅ All environment checks passed!")
    else:
        print("\n⚠️ Some environment checks failed. Please fix the issues above.")
    
    input("\nPress Enter to return to the menu...")

def start_bot():
    """Запускает бот в отдельном процессе"""
    print_header("START BOT")
    
    if not os.environ.get("TELEGRAM_TOKEN"):
        print("✗ TELEGRAM_TOKEN environment variable is not set.")
        print("  You need to set this variable before starting the bot.")
        input("\nPress Enter to return to the menu...")
        return
    
    print("Starting Language Mirror bot...")
    print("(Press Ctrl+C in the bot window to stop it)")
    print("Returning to admin menu in this window.")
    
    try:
        # Запускаем скрипт в новом окне терминала
        if sys.platform.startswith('win'):
            subprocess.Popen(["start", "cmd", "/k", "python", "language_mirror_telebot.py"], shell=True)
        elif sys.platform.startswith('darwin'):  # macOS
            subprocess.Popen(["osascript", "-e", 'tell app "Terminal" to do script "cd ' + os.getcwd() + ' && python language_mirror_telebot.py"'])
        else:  # Linux
            subprocess.Popen(["x-terminal-emulator", "-e", "python language_mirror_telebot.py 2>&1"])
        
        print("✓ Bot started in a new terminal window.")
    except Exception as e:
        print(f"✗ Error starting bot: {e}")
        print("  Try running './start_bot.sh' manually in a separate terminal.")
    
    input("\nPress Enter to return to the menu...")

def main():
    """Основная функция для запуска административных инструментов"""
    while True:
        print_menu()
        choice = input("Select option (0-5): ")
        
        if choice == "0":
            print("\nExiting admin tools. Goodbye!")
            break
        elif choice == "1":
            check_bot_status()
        elif choice == "2":
            add_test_feedback_menu()
        elif choice == "3":
            view_feedback()
        elif choice == "4":
            check_environment()
        elif choice == "5":
            start_bot()
        else:
            print("\nInvalid option. Please try again.")
            input("Press Enter to continue...")

if __name__ == "__main__":
    main()