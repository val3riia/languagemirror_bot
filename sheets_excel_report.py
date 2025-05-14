"""
Модуль для создания отчетов в формате Excel на основе данных из Google Sheets.
"""
import os
import tempfile
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
from io import BytesIO

import pandas as pd
from sheets_manager import SheetsManager

# Настройка логирования
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

def create_feedback_excel(sheets_manager: Optional[SheetsManager] = None, 
                          filename: Optional[str] = None) -> Tuple[Union[BytesIO, str], str]:
    """
    Создает Excel-файл с данными обратной связи из Google Sheets.
    
    Args:
        sheets_manager: Менеджер для работы с Google Sheets
        filename: Имя выходного файла (опционально)
        
    Returns:
        Tuple: (BytesIO или путь к файлу, имя файла)
    """
    try:
        # Создаем экземпляр SheetsManager, если он не передан
        if not sheets_manager:
            sheets_manager = SheetsManager()
        
        # Получаем данные обратной связи
        feedback_items = sheets_manager.get_all_feedback()
        
        if not feedback_items:
            logger.warning("Нет данных обратной связи для экспорта.")
            
            # Создаем пустой DataFrame с заголовками
            feedback_items = [{
                "id": "",
                "user_id": "",
                "telegram_id": "",
                "username": "",
                "session_id": "",
                "rating": "",
                "comment": "",
                "timestamp": ""
            }]
        
        # Конвертируем в pandas DataFrame
        df = pd.DataFrame(feedback_items)
        
        # Форматируем временные метки
        if "timestamp" in df.columns:
            try:
                df["formatted_date"] = pd.to_datetime(df["timestamp"]).dt.strftime("%d.%m.%Y %H:%M")
            except:
                df["formatted_date"] = df["timestamp"]
        
        # Определяем имя файла
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            directory = "reports"
            os.makedirs(directory, exist_ok=True)
            filename = f"{directory}/feedback_report_{timestamp}.xlsx"
        
        # Создаем временный файл или BytesIO
        if filename.startswith("/tmp/") or "temp" in filename:
            # Используем BytesIO для передачи через Telegram
            output = BytesIO()
            writer = pd.ExcelWriter(output, engine="xlsxwriter")
            use_bytesio = True
        else:
            # Используем обычный файл
            writer = pd.ExcelWriter(filename, engine="xlsxwriter")
            use_bytesio = False
        
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
        
        if use_bytesio:
            output.seek(0)
            return output, os.path.basename(filename)
        else:
            return filename, os.path.basename(filename)
    
    except Exception as e:
        logger.error(f"Ошибка при создании отчета Excel: {e}")
        
        # В случае ошибки создаем пустой отчет
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            directory = "reports"
            os.makedirs(directory, exist_ok=True)
            filename = f"{directory}/empty_report_{timestamp}.xlsx"
        
        # Создаем пустой DataFrame
        df = pd.DataFrame({"Error": ["Ошибка при создании отчета"]})
        
        if "output" in locals() and isinstance(output, BytesIO):
            # Если уже создан BytesIO
            output = BytesIO()
            df.to_excel(output, index=False)
            output.seek(0)
            return output, os.path.basename(filename)
        else:
            # Иначе создаем файл
            df.to_excel(filename, index=False)
            return filename, os.path.basename(filename)

def create_temp_excel_for_telegram(sheets_manager: Optional[SheetsManager] = None) -> Tuple[str, str]:
    """
    Создает временный Excel-файл для отправки через Telegram.
    
    Args:
        sheets_manager: Менеджер для работы с Google Sheets
        
    Returns:
        Tuple: (путь к временному файлу, имя файла)
    """
    # Создаем временный файл
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
        temp_filename = temp_file.name
    
    # Создаем отчет во временном файле
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path, _ = create_feedback_excel(
        sheets_manager=sheets_manager, 
        filename=temp_filename
    )
    
    # Имя файла для пользователя
    user_filename = f"feedback_report_{timestamp}.xlsx"
    
    return file_path, user_filename