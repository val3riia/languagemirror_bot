#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для проверки соединения с базой данных.
Используется для диагностики проблем с подключением к PostgreSQL.
"""

import os
import sys
import logging
import psycopg2
import sqlalchemy
from sqlalchemy import create_engine, text

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def check_psycopg2_connection(connection_string):
    """Проверяет подключение к PostgreSQL через psycopg2."""
    print("\n=== Проверка через psycopg2 ===")
    try:
        # Удаляем префикс postgresql:// если он есть
        if connection_string.startswith('postgresql://'):
            conn_params = connection_string[13:]
        else:
            conn_params = connection_string
            
        # Подключаемся к базе данных
        connection = psycopg2.connect(conn_params)
        cursor = connection.cursor()
        
        # Выполняем простой запрос
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ Успешное подключение через psycopg2")
        print(f"PostgreSQL версия: {version[0]}")
        
        # Проверяем SSL
        cursor.execute("SHOW ssl;")
        ssl_status = cursor.fetchone()[0]
        print(f"SSL статус: {ssl_status}")
        
        # Закрываем подключение
        cursor.close()
        connection.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка подключения через psycopg2: {str(e)}")
        return False

def check_sqlalchemy_connection(connection_string, ssl_mode="prefer"):
    """Проверяет подключение к PostgreSQL через SQLAlchemy."""
    print(f"\n=== Проверка через SQLAlchemy (sslmode={ssl_mode}) ===")
    try:
        # Создаем движок SQLAlchemy
        engine = create_engine(
            connection_string,
            connect_args={
                "sslmode": ssl_mode,
                "application_name": "DB Connection Checker",
                "connect_timeout": 10
            }
        )
        
        # Подключаемся и выполняем запрос
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✅ Успешное подключение через SQLAlchemy")
            print(f"PostgreSQL версия: {version}")
            
            # Проверяем SSL
            result = connection.execute(text("SHOW ssl;"))
            ssl_status = result.fetchone()[0]
            print(f"SSL статус: {ssl_status}")
            
        return True
    except Exception as e:
        print(f"❌ Ошибка подключения через SQLAlchemy: {str(e)}")
        return False

def main():
    """Основная функция скрипта."""
    print("=== Проверка подключения к базе данных ===")
    
    # Получаем URL базы данных из переменных окружения
    database_url = os.environ.get("DATABASE_URL")
    
    if not database_url:
        print("❌ Ошибка: Переменная окружения DATABASE_URL не найдена")
        print("Пожалуйста, установите DATABASE_URL в формате:")
        print("postgresql://username:password@hostname:port/database_name")
        return 1
        
    print(f"Используется DATABASE_URL: {database_url.replace(database_url.split('@')[0], '***')}")
    
    # Проверяем соединение через psycopg2
    psycopg2_ok = check_psycopg2_connection(database_url)
    
    # Проверяем соединение через SQLAlchemy с разными режимами SSL
    sqlalchemy_prefer = check_sqlalchemy_connection(database_url, "prefer")
    sqlalchemy_require = check_sqlalchemy_connection(database_url, "require")
    sqlalchemy_disable = check_sqlalchemy_connection(database_url, "disable")
    
    # Выводим результаты
    print("\n=== Результаты проверки ===")
    print(f"psycopg2: {'✅ OK' if psycopg2_ok else '❌ Ошибка'}")
    print(f"SQLAlchemy (sslmode=prefer): {'✅ OK' if sqlalchemy_prefer else '❌ Ошибка'}")
    print(f"SQLAlchemy (sslmode=require): {'✅ OK' if sqlalchemy_require else '❌ Ошибка'}")
    print(f"SQLAlchemy (sslmode=disable): {'✅ OK' if sqlalchemy_disable else '❌ Ошибка'}")
    
    # Рекомендации на основе результатов
    print("\n=== Рекомендации ===")
    if not (psycopg2_ok or sqlalchemy_prefer or sqlalchemy_require or sqlalchemy_disable):
        print("❌ Не удалось подключиться к базе данных ни одним из способов.")
        print("Проверьте следующее:")
        print("1. Правильность URL базы данных")
        print("2. Доступность сервера базы данных (возможны проблемы с сетью)")
        print("3. Права доступа пользователя базы данных")
    else:
        if sqlalchemy_prefer:
            print("✅ Рекомендуется использовать SQLAlchemy с sslmode=prefer")
        elif sqlalchemy_require:
            print("✅ Рекомендуется использовать SQLAlchemy с sslmode=require")
        elif sqlalchemy_disable:
            print("✅ Рекомендуется использовать SQLAlchemy с sslmode=disable, но это небезопасно!")
        elif psycopg2_ok:
            print("✅ Рекомендуется использовать psycopg2 напрямую")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())