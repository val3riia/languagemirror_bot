#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для создания отчетов в формате Excel для системы обратной связи.
"""

import os
import pandas as pd
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
from io import BytesIO
import tempfile

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

def create_feedback_excel(feedback_data: List[Dict[str, Any]], filename: Optional[str] = None) -> Tuple[Union[BytesIO, str], str]:
    """
    Создает Excel-файл с данными обратной связи.
    
    Args:
        feedback_data: Список словарей с данными обратной связи
        filename: Имя выходного файла (опционально)
        
    Returns:
        Tuple: (BytesIO или путь к файлу, имя файла)
    """
    # Если имя файла не указано, генерируем по текущей дате
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"feedback_report_{timestamp}.xlsx"
    
    # Трансформируем данные для pandas DataFrame
    data = []
    for item in feedback_data:
        # Конвертируем рейтинг в понятную форму
        rating_display = {
            "helpful": "Полезно 👍",
            "okay": "Нормально 🤔",
            "not_helpful": "Не полезно 👎"
        }.get(item.get("rating", ""), item.get("rating", ""))
        
        # Форматируем дату
        timestamp = item.get("timestamp")
        date_str = timestamp.strftime("%d.%m.%Y %H:%M") if timestamp else ""
        
        # Добавляем запись в список
        data.append({
            "ID": item.get("id", ""),
            "Пользователь": item.get("username", ""),
            "Telegram ID": item.get("user_id", ""),
            "Оценка": rating_display,
            "Комментарий": item.get("comment", ""),
            "Дата": date_str
        })
    
    # Создаем DataFrame 
    try:
        # Если данных нет, создаем пустой DataFrame с заголовками
        if not data:
            columns = ["ID", "Пользователь", "Telegram ID", "Оценка", "Комментарий", "Дата"]
            df = pd.DataFrame(columns=columns)
        else:
            df = pd.DataFrame(data)
        
        # Создаем BytesIO объект для хранения Excel-файла в памяти
        excel_bytes = BytesIO()
        
        # Создаем writer с настройками
        with pd.ExcelWriter(excel_bytes, engine='xlsxwriter') as writer:
            # Конвертируем DataFrame в Excel
            df.to_excel(writer, sheet_name='Обратная связь', index=False)
            
            # Получаем объект worksheet для форматирования
            worksheet = writer.sheets['Обратная связь']
            
            # Автоматическая ширина столбцов
            for i, col in enumerate(df.columns):
                # Находим максимальную ширину в каждом столбце
                max_len = max(
                    df[col].astype(str).map(len).max() if len(df) > 0 else 0,  # Макс длина содержимого
                    len(col)  # Длина заголовка
                ) + 2  # Добавляем отступ
                
                # Устанавливаем ширину стобца
                worksheet.set_column(i, i, max_len)
            
            # Форматирование заголовка
            header_format = writer.book.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'bg_color': '#D9EAD3',  # Светло-зеленый фон
                'border': 1
            })
            
            # Применяем формат к заголовку
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
        
        # Перемещаем указатель в начало BytesIO
        excel_bytes.seek(0)
        
        # Для совместимости с Telegram, создаем временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            temp_file.write(excel_bytes.getvalue())
            temp_path = temp_file.name
        
        logger.info(f"Excel отчет создан успешно в памяти и временном файле: {temp_path}")
        return temp_path, filename
        
    except Exception:
        logger.error("Ошибка при создании Excel-отчета")
        # Закомментировано для безопасности на GitHub
        # import traceback
        # logger.error(traceback.format_exc())
        raise
        
def create_simple_feedback_excel(feedback_records, filename: Optional[str] = None) -> str:
    """
    Упрощенная версия для создания Excel из записей обратной связи, полученных напрямую из базы данных.
    
    Args:
        feedback_records: Список кортежей (feedback, telegram_id, username, first_name, last_name)
        filename: Имя выходного файла (опционально)
    
    Returns:
        Путь к созданному временному файлу Excel
    """
    print("===================== EXCEL REPORT GENERATION STARTED =====================")
    print(f"Received {len(feedback_records)} feedback records")
    logger.info(f"Получено {len(feedback_records)} записей обратной связи для отчета")
    
    # Преобразуем в формат, подходящий для основной функции
    feedback_data = []
    
    try:
        for record, telegram_id, username, first_name, last_name in feedback_records:
            # Формируем имя пользователя для отображения
            user_display = username or first_name or f"User {telegram_id}"
            
            print(f"Processing record: ID={record.id}, Rating={record.rating}, User={user_display}")
            
            feedback_data.append({
                "id": record.id,
                "rating": record.rating,
                "comment": record.comment,
                "timestamp": record.timestamp,
                "user_id": telegram_id,
                "username": user_display,
                "first_name": first_name,
                "last_name": last_name
            })
        
        print(f"Transformed {len(feedback_data)} records for Excel report")
        logger.info(f"Подготовлено {len(feedback_data)} записей для Excel отчета")
        
        # Используем основную функцию для создания Excel
        print("Calling create_feedback_excel function...")
        temp_path, _ = create_feedback_excel(feedback_data, filename)
        print(f"Excel report created at: {temp_path}")
        
        return temp_path
    except Exception as e:
        print(f"ERROR in create_simple_feedback_excel: {str(e)}")
        logger.error(f"Ошибка в create_simple_feedback_excel: {str(e)}")
        # Перезапускаем исключение, чтобы верхний уровень мог его обработать
        raise