import logging
import os
import tempfile
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
from sheets_manager import get_sheets_manager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_sheets_feedback_excel(
    limit: int = 100, filename: Optional[str] = None
) -> Tuple[Union[BytesIO, str], str]:
    """
    Создает Excel-файл с данными обратной связи из Google Sheets.
    
    Args:
        limit: Максимальное количество записей
        filename: Имя выходного файла (опционально)
        
    Returns:
        Tuple: (BytesIO или путь к файлу, имя файла)
    """
    try:
        # Получаем менеджер Google Sheets
        sheets_manager = get_sheets_manager()
        if not sheets_manager:
            logger.error("Google Sheets менеджер недоступен")
            return create_dummy_excel(filename)
            
        # Проверяем подключение
        if not sheets_manager.health_check():
            logger.error("Нет подключения к Google Sheets")
            return create_dummy_excel(filename)
            
        # Получаем обогащенные данные обратной связи
        feedback_data = sheets_manager.get_enriched_feedback(limit=limit)
        
        if not feedback_data:
            logger.warning("Данные обратной связи не найдены")
            return create_dummy_excel(filename)
            
        # Преобразуем данные для отчета
        return create_excel_from_feedback_data(feedback_data, filename)
    except Exception as e:
        logger.error(f"Ошибка при создании отчета из Google Sheets: {e}")
        return create_dummy_excel(filename)


def create_excel_from_feedback_data(
    feedback_data: List[Dict[str, Any]], filename: Optional[str] = None
) -> Tuple[Union[BytesIO, str], str]:
    """
    Создает Excel-файл из списка данных обратной связи.
    
    Args:
        feedback_data: Список словарей с данными обратной связи
        filename: Имя выходного файла (опционально)
        
    Returns:
        Tuple: (BytesIO или путь к файлу, имя файла)
    """
    # Создаем DataFrame из данных
    df = pd.DataFrame(feedback_data)
    
    # Переименовываем столбцы для отчета
    columns_mapping = {
        "id": "ID",
        "user_id": "ID Пользователя",
        "session_id": "ID Сессии",
        "telegram_id": "Telegram ID",
        "username": "Имя пользователя",
        "first_name": "Имя",
        "last_name": "Фамилия",
        "rating": "Оценка",
        "comment": "Комментарий",
        "created_at": "Дата создания"
    }
    
    # Применяем переименование столбцов, если они есть в DataFrame
    rename_cols = {col: columns_mapping[col] for col in df.columns if col in columns_mapping}
    if rename_cols:
        df = df.rename(columns=rename_cols)
    
    # Формируем имя файла, если не указано
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"feedback_report_{timestamp}.xlsx"
    
    # Определяем, куда сохранять файл - в память или на диск
    if os.environ.get("EXCEL_REPORTS_IN_MEMORY", "False").lower() == "true":
        # Сохраняем в память для отправки в Telegram
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Обратная связь", index=False)
            
            # Добавляем автоподбор ширины столбцов
            worksheet = writer.sheets["Обратная связь"]
            for i, col in enumerate(df.columns):
                column_len = max(df[col].astype(str).str.len().max(), len(col) + 2)
                worksheet.set_column(i, i, column_len)
        
        # Возвращаем буфер и имя файла
        excel_buffer.seek(0)
        return excel_buffer, filename
    else:
        # Создаем временный файл для сохранения отчета
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name
            
        # Сохраняем в файл
        with pd.ExcelWriter(tmp_path, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Обратная связь", index=False)
            
            # Добавляем автоподбор ширины столбцов
            worksheet = writer.sheets["Обратная связь"]
            for i, col in enumerate(df.columns):
                column_len = max(df[col].astype(str).str.len().max(), len(col) + 2)
                worksheet.set_column(i, i, column_len)
        
        return tmp_path, filename


def create_dummy_excel(filename: Optional[str] = None) -> Tuple[Union[BytesIO, str], str]:
    """
    Создает пустой Excel-файл при ошибках доступа к данным.
    
    Args:
        filename: Имя выходного файла (опционально)
        
    Returns:
        Tuple: (BytesIO или путь к файлу, имя файла)
    """
    # Создаем пустой DataFrame
    df = pd.DataFrame({
        "Сообщение": ["Нет данных обратной связи или ошибка при доступе к данным."]
    })
    
    # Формируем имя файла, если не указано
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"empty_feedback_report_{timestamp}.xlsx"
    
    # Определяем, куда сохранять файл - в память или на диск
    if os.environ.get("EXCEL_REPORTS_IN_MEMORY", "False").lower() == "true":
        # Сохраняем в память для отправки в Telegram
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Обратная связь", index=False)
        
        # Возвращаем буфер и имя файла
        excel_buffer.seek(0)
        return excel_buffer, filename
    else:
        # Создаем временный файл для сохранения отчета
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name
            
        # Сохраняем в файл
        with pd.ExcelWriter(tmp_path, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Обратная связь", index=False)
        
        return tmp_path, filename


if __name__ == "__main__":
    # Тестирование функции создания отчета
    report_path, report_name = create_sheets_feedback_excel()
    print(f"Отчет сохранен: {report_path} (имя файла: {report_name})")