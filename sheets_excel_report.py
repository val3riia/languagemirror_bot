"""
Модуль для создания отчетов в формате Excel на основе данных из Google Sheets.
"""

import logging
import os
import tempfile
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
from xlsxwriter import Workbook
from xlsxwriter.utility import xl_rowcol_to_cell

from sheets_manager import SheetsManager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    logger.info("Создание Excel-отчета с данными обратной связи")
    
    # Если filename не указан, создаем временное имя файла
    if not filename:
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"feedback_report_{now}.xlsx"
    
    try:
        # Если sheets_manager не передан, создаем новый
        if not sheets_manager:
            sheets_manager = SheetsManager()
            
        # Получаем данные обратной связи
        feedback_data = sheets_manager.get_all_feedback()
        
        # Если нет данных, возвращаем пустой отчет
        if not feedback_data:
            logger.warning("Нет данных обратной связи для создания отчета")
            output = BytesIO()
            workbook = Workbook(output)
            worksheet = workbook.add_worksheet("Обратная связь")
            
            # Заголовки
            headers = ["ID", "Telegram ID", "Имя пользователя", "Имя", "Фамилия", 
                      "ID сессии", "Оценка", "Комментарий", "Дата создания"]
            
            # Форматирование
            header_format = workbook.add_format({
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'fg_color': '#D7E4BC',
                'border': 1,
            })
            
            # Пишем заголовки
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
                worksheet.set_column(col, col, 15)
            
            # Добавляем сообщение о пустых данных
            empty_format = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'italic': True,
                'fg_color': '#F2F2F2',
            })
            
            worksheet.merge_range(1, 0, 1, len(headers) - 1, 
                                "Нет данных обратной связи", empty_format)
            
            workbook.close()
            output.seek(0)
            
            return output, filename
        
        # Создаем DataFrame из данных обратной связи
        df = pd.DataFrame(feedback_data)
        
        # Определяем, куда сохранять отчет: в файл или в память
        save_to_file = False
        
        # Если имя файла указано с расширением .xlsx, сохраняем в файл
        if filename.endswith('.xlsx'):
            temp_dir = tempfile.gettempdir()
            file_path = os.path.join(temp_dir, filename)
            output = file_path
            save_to_file = True
        else:
            output = BytesIO()
        
        # Создаем Excel-файл
        if save_to_file:
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
        else:
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            
        # Записываем данные в Excel
        df.to_excel(writer, sheet_name='Обратная связь', index=False)
        
        # Форматирование
        workbook = writer.book
        worksheet = writer.sheets['Обратная связь']
        
        # Форматы
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'fg_color': '#D7E4BC',
            'border': 1,
        })
        
        date_format = workbook.add_format({
            'num_format': 'yyyy-mm-dd hh:mm:ss',
            'align': 'center',
        })
        
        text_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'text_wrap': True,
        })
        
        # Применяем форматы к заголовкам
        for col_num, column in enumerate(df.columns):
            worksheet.write(0, col_num, column, header_format)
            
            # Устанавливаем ширину столбца в зависимости от содержимого
            if column in ['комментарий', 'comment']:
                worksheet.set_column(col_num, col_num, 40, text_format)
            elif column in ['created_at', 'дата создания']:
                worksheet.set_column(col_num, col_num, 20, date_format)
            else:
                max_len = max([len(str(s)) for s in df[column]] + [len(column)])
                worksheet.set_column(col_num, col_num, max_len + 2)
        
        # Сохраняем Excel-файл
        writer.close()
        
        if not save_to_file:
            output.seek(0)
        
        logger.info(f"Создан Excel-отчет по обратной связи: {filename}")
        
        return output, filename
    
    except Exception as e:
        logger.error(f"Ошибка при создании Excel-отчета: {e}")
        
        # В случае ошибки возвращаем пустой отчет
        output = BytesIO()
        workbook = Workbook(output)
        worksheet = workbook.add_worksheet("Ошибка")
        
        worksheet.write(0, 0, f"Произошла ошибка при создании отчета: {str(e)}")
        worksheet.set_column(0, 0, 50)
        
        workbook.close()
        output.seek(0)
        
        return output, filename

def create_temp_excel_for_telegram(sheets_manager: Optional[SheetsManager] = None) -> Tuple[str, str]:
    """
    Создает временный Excel-файл для отправки через Telegram.
    
    Args:
        sheets_manager: Менеджер для работы с Google Sheets
        
    Returns:
        Tuple: (путь к временному файлу, имя файла)
    """
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"feedback_report_{now}.xlsx"
    
    # Создаем отчет во временном файле
    output, actual_filename = create_feedback_excel(sheets_manager, filename)
    
    if isinstance(output, BytesIO):
        # Если отчет в памяти, сохраняем его во временный файл
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, actual_filename)
        
        with open(file_path, 'wb') as f:
            f.write(output.getvalue())
        
        return file_path, actual_filename
    else:
        # Если отчет уже в файле, просто возвращаем путь
        return output, actual_filename