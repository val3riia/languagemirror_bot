"""
Модуль для управления данными в Google Sheets для Language Mirror Bot.
Этот модуль заменяет хранение данных в PostgreSQL и работает с таблицами Google Sheets.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Идентификация листов в Google Sheets
DEFAULT_SHEETS = {
    "users": "Users",
    "sessions": "Sessions",
    "messages": "Messages",
    "feedback": "Feedback"
}

class SheetsManager:
    """
    Менеджер для работы с Google Sheets.
    Обеспечивает хранение данных Language Mirror Bot в Google Sheets
    вместо PostgreSQL.
    """
    
    def __init__(self, 
                 credentials_path: Optional[str] = None,
                 spreadsheet_key: Optional[str] = None,
                 users_sheet_name: str = "Users",
                 sessions_sheet_name: str = "Sessions",
                 messages_sheet_name: str = "Messages",
                 feedback_sheet_name: str = "Feedback"):
        """
        Инициализирует менеджер для работы с Google Sheets.
        
        Args:
            credentials_path (str, optional): Путь к файлу учетных данных JSON
            spreadsheet_key (str, optional): Ключ таблицы Google Sheets
            users_sheet_name (str): Имя листа для пользователей
            sessions_sheet_name (str): Имя листа для сессий
            messages_sheet_name (str): Имя листа для сообщений
            feedback_sheet_name (str): Имя листа для обратной связи
        """
        self.credentials_path = credentials_path or os.environ.get('GOOGLE_CREDENTIALS_PATH')
        self.spreadsheet_key = spreadsheet_key or os.environ.get('GOOGLE_SHEETS_KEY')
        
        self.users_sheet_name = users_sheet_name
        self.sessions_sheet_name = sessions_sheet_name
        self.messages_sheet_name = messages_sheet_name
        self.feedback_sheet_name = feedback_sheet_name
        
        self.sheet = None
        
        # Инициализация Google Sheets API
        try:
            if self.credentials_path and self.spreadsheet_key:
                # Аутентификация в Google Sheets API
                scope = ['https://spreadsheets.google.com/feeds',
                         'https://www.googleapis.com/auth/drive']
                
                creds = ServiceAccountCredentials.from_json_keyfile_name(
                    self.credentials_path, scope)
                
                client = gspread.authorize(creds)
                
                # Открытие таблицы по ключу
                self.sheet = client.open_by_key(self.spreadsheet_key)
                
                # Проверка и создание необходимых листов
                self._setup_sheets()
                
                logger.info(f"Google Sheets initialized with key: {self.spreadsheet_key}")
            else:
                logger.warning("GOOGLE_CREDENTIALS_PATH or GOOGLE_SHEETS_KEY not provided")
        except Exception as e:
            logger.error(f"Error initializing Google Sheets: {e}")
    
    def _setup_sheets(self):
        """Создает необходимые листы, если они отсутствуют."""
        try:
            # Получаем список существующих листов
            existing_worksheets = [ws.title for ws in self.sheet.worksheets()]
            
            # Создаем лист пользователей, если он не существует
            if self.users_sheet_name not in existing_worksheets:
                self.sheet.add_worksheet(title=self.users_sheet_name, rows=1000, cols=20)
                users_sheet = self.sheet.worksheet(self.users_sheet_name)
                users_sheet.append_row([
                    "id", "telegram_id", "username", "first_name", "last_name", 
                    "language_level", "feedback_bonus_used", "feedback_bonus_available",
                    "created_at", "last_active"
                ])
            
            # Создаем лист сессий, если он не существует
            if self.sessions_sheet_name not in existing_worksheets:
                self.sheet.add_worksheet(title=self.sessions_sheet_name, rows=1000, cols=10)
                sessions_sheet = self.sheet.worksheet(self.sessions_sheet_name)
                sessions_sheet.append_row([
                    "id", "user_id", "telegram_id", "active", "language_level", 
                    "topic", "created_at", "last_active"
                ])
            
            # Создаем лист сообщений, если он не существует
            if self.messages_sheet_name not in existing_worksheets:
                self.sheet.add_worksheet(title=self.messages_sheet_name, rows=5000, cols=10)
                messages_sheet = self.sheet.worksheet(self.messages_sheet_name)
                messages_sheet.append_row([
                    "id", "session_id", "telegram_id", "role", "content", "created_at"
                ])
            
            # Создаем лист обратной связи, если он не существует
            if self.feedback_sheet_name not in existing_worksheets:
                self.sheet.add_worksheet(title=self.feedback_sheet_name, rows=1000, cols=10)
                feedback_sheet = self.sheet.worksheet(self.feedback_sheet_name)
                feedback_sheet.append_row([
                    "id", "telegram_id", "username", "first_name", "last_name", 
                    "session_id", "rating", "comment", "created_at"
                ])
                
            logger.info("All required sheets are set up")
        except Exception as e:
            logger.error(f"Error setting up sheets: {e}")
    
    def _get_next_id(self, sheet_name):
        """
        Получает следующий ID для новой записи в указанном листе.
        
        Args:
            sheet_name (str): Имя листа
            
        Returns:
            int: Следующий ID
        """
        try:
            worksheet = self.sheet.worksheet(sheet_name)
            # Получаем все значения в первом столбце
            values = worksheet.col_values(1)
            
            # Пропускаем заголовок и считаем количество записей
            num_records = len(values) - 1 if len(values) > 0 else 0
            
            # Возвращаем следующий ID
            return num_records + 1
        except Exception as e:
            logger.error(f"Error getting next ID for {sheet_name}: {e}")
            return 1  # В случае ошибки возвращаем 1
    
    def get_user_by_telegram_id(self, telegram_id):
        """
        Получает данные пользователя по его Telegram ID.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            dict: Данные пользователя или None, если пользователь не найден
        """
        try:
            worksheet = self.sheet.worksheet(self.users_sheet_name)
            
            # Получаем заголовки
            headers = worksheet.row_values(1)
            
            # Ищем пользователя по telegram_id
            cell = worksheet.find(str(telegram_id), in_column=2)
            
            if cell:
                row = worksheet.row_values(cell.row)
                
                # Создаем словарь с данными пользователя
                user_data = dict(zip(headers, row))
                return user_data
            
            return None
        except Exception as e:
            logger.error(f"Error getting user by telegram_id {telegram_id}: {e}")
            return None
    
    def add_user(self, telegram_id, username=None, first_name=None, last_name=None, language_level=None):
        """
        Добавляет нового пользователя или обновляет существующего.
        
        Args:
            telegram_id: Telegram ID пользователя
            username: Имя пользователя в Telegram
            first_name: Имя пользователя
            last_name: Фамилия пользователя
            language_level: Уровень владения языком
            
        Returns:
            dict: Данные добавленного пользователя
        """
        try:
            # Проверяем, существует ли пользователь
            existing_user = self.get_user_by_telegram_id(telegram_id)
            
            if existing_user:
                # Обновляем существующего пользователя
                return self.update_user(
                    telegram_id,
                    {
                        "username": username or existing_user.get("username", ""),
                        "first_name": first_name or existing_user.get("first_name", ""),
                        "last_name": last_name or existing_user.get("last_name", ""),
                        "language_level": language_level or existing_user.get("language_level", ""),
                        "last_active": datetime.now().isoformat()
                    }
                )
            
            # Создаем нового пользователя
            worksheet = self.sheet.worksheet(self.users_sheet_name)
            
            # Получаем следующий ID
            user_id = self._get_next_id(self.users_sheet_name)
            current_time = datetime.now().isoformat()
            
            # Создаем запись пользователя
            new_user = [
                user_id,
                telegram_id,
                username or "",
                first_name or "",
                last_name or "",
                language_level or "",
                "False",  # feedback_bonus_used
                "False",  # feedback_bonus_available
                current_time,  # created_at
                current_time   # last_active
            ]
            
            # Добавляем пользователя
            worksheet.append_row([str(val) for val in new_user])
            
            # Получаем заголовки
            headers = worksheet.row_values(1)
            
            # Создаем словарь с данными пользователя
            user_data = dict(zip(headers, new_user))
            
            logger.info(f"Added new user with telegram_id {telegram_id}")
            
            return user_data
        except Exception as e:
            logger.error(f"Error adding user with telegram_id {telegram_id}: {e}")
            return None
    
    def update_user(self, telegram_id, data):
        """
        Обновляет данные пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            data: Словарь с данными для обновления
            
        Returns:
            dict: Обновленные данные пользователя
        """
        try:
            worksheet = self.sheet.worksheet(self.users_sheet_name)
            
            # Получаем заголовки
            headers = worksheet.row_values(1)
            
            # Ищем пользователя по telegram_id
            cell = worksheet.find(str(telegram_id), in_column=2)
            
            if cell:
                # Получаем текущие данные пользователя
                row = worksheet.row_values(cell.row)
                user_data = dict(zip(headers, row))
                
                # Обновляем данные
                for key, value in data.items():
                    if key in headers:
                        col_idx = headers.index(key) + 1
                        worksheet.update_cell(cell.row, col_idx, str(value))
                        user_data[key] = str(value)
                
                # Обязательно обновляем last_active
                last_active_idx = headers.index("last_active") + 1
                current_time = datetime.now().isoformat()
                worksheet.update_cell(cell.row, last_active_idx, current_time)
                user_data["last_active"] = current_time
                
                logger.info(f"Updated user with telegram_id {telegram_id}")
                
                return user_data
            else:
                # Если пользователь не найден, создаем нового
                return self.add_user(telegram_id)
        except Exception as e:
            logger.error(f"Error updating user with telegram_id {telegram_id}: {e}")
            return None
    
    def create_session(self, telegram_id, language_level=None, topic=None):
        """
        Создает новую сессию для пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            language_level: Уровень владения языком
            topic: Тема сессии
            
        Returns:
            dict: Данные созданной сессии
        """
        try:
            # Получаем или создаем пользователя
            user = self.get_user_by_telegram_id(telegram_id)
            if not user:
                user = self.add_user(telegram_id)
            
            # Завершаем все активные сессии пользователя
            self.end_all_sessions(telegram_id)
            
            # Работаем с листом сессий
            worksheet = self.sheet.worksheet(self.sessions_sheet_name)
            
            # Получаем следующий ID
            session_id = self._get_next_id(self.sessions_sheet_name)
            current_time = datetime.now().isoformat()
            
            # Создаем запись сессии
            new_session = [
                session_id,
                user.get("id", ""),
                telegram_id,
                "True",  # active
                language_level or user.get("language_level", ""),
                topic or "",
                current_time,  # created_at
                current_time   # last_active
            ]
            
            # Добавляем сессию
            worksheet.append_row([str(val) for val in new_session])
            
            # Получаем заголовки
            headers = worksheet.row_values(1)
            
            # Создаем словарь с данными сессии
            session_data = dict(zip(headers, new_session))
            
            logger.info(f"Created new session for user with telegram_id {telegram_id}")
            
            return session_data
        except Exception as e:
            logger.error(f"Error creating session for user with telegram_id {telegram_id}: {e}")
            return None
    
    def get_active_session(self, telegram_id):
        """
        Получает активную сессию пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            dict: Данные активной сессии или None, если сессия не найдена
        """
        try:
            worksheet = self.sheet.worksheet(self.sessions_sheet_name)
            
            # Получаем заголовки
            headers = worksheet.row_values(1)
            
            # Находим все строки с данным telegram_id
            cells = worksheet.findall(str(telegram_id), in_column=3)
            
            for cell in cells:
                row = worksheet.row_values(cell.row)
                session_data = dict(zip(headers, row))
                
                # Проверяем, активна ли сессия
                if session_data.get("active", "").lower() == "true":
                    return session_data
            
            return None
        except Exception as e:
            logger.error(f"Error getting active session for user with telegram_id {telegram_id}: {e}")
            return None
    
    def update_session(self, session_id, data):
        """
        Обновляет данные сессии.
        
        Args:
            session_id: ID сессии
            data: Словарь с данными для обновления
            
        Returns:
            dict: Обновленные данные сессии
        """
        try:
            worksheet = self.sheet.worksheet(self.sessions_sheet_name)
            
            # Получаем заголовки
            headers = worksheet.row_values(1)
            
            # Ищем сессию по ID
            cell = worksheet.find(str(session_id), in_column=1)
            
            if cell:
                # Получаем текущие данные сессии
                row = worksheet.row_values(cell.row)
                session_data = dict(zip(headers, row))
                
                # Обновляем данные
                for key, value in data.items():
                    if key in headers:
                        col_idx = headers.index(key) + 1
                        worksheet.update_cell(cell.row, col_idx, str(value))
                        session_data[key] = str(value)
                
                # Обязательно обновляем last_active
                last_active_idx = headers.index("last_active") + 1
                current_time = datetime.now().isoformat()
                worksheet.update_cell(cell.row, last_active_idx, current_time)
                session_data["last_active"] = current_time
                
                logger.info(f"Updated session with ID {session_id}")
                
                return session_data
            
            return None
        except Exception as e:
            logger.error(f"Error updating session with ID {session_id}: {e}")
            return None
    
    def end_session(self, session_id):
        """
        Завершает сессию.
        
        Args:
            session_id: ID сессии
            
        Returns:
            bool: True если сессия завершена успешно, иначе False
        """
        try:
            worksheet = self.sheet.worksheet(self.sessions_sheet_name)
            
            # Получаем заголовки
            headers = worksheet.row_values(1)
            
            # Ищем сессию по ID
            cell = worksheet.find(str(session_id), in_column=1)
            
            if cell:
                # Изменяем статус сессии на неактивный
                active_idx = headers.index("active") + 1
                worksheet.update_cell(cell.row, active_idx, "False")
                
                logger.info(f"Ended session with ID {session_id}")
                
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error ending session with ID {session_id}: {e}")
            return False
    
    def end_all_sessions(self, telegram_id):
        """
        Завершает все активные сессии пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            int: Количество завершенных сессий
        """
        try:
            worksheet = self.sheet.worksheet(self.sessions_sheet_name)
            
            # Получаем заголовки
            headers = worksheet.row_values(1)
            active_idx = headers.index("active") + 1
            
            # Находим все строки с данным telegram_id
            cells = worksheet.findall(str(telegram_id), in_column=3)
            
            count = 0
            for cell in cells:
                row = worksheet.row_values(cell.row)
                session_data = dict(zip(headers, row))
                
                # Проверяем, активна ли сессия
                if session_data.get("active", "").lower() == "true":
                    # Изменяем статус сессии на неактивный
                    worksheet.update_cell(cell.row, active_idx, "False")
                    count += 1
            
            if count > 0:
                logger.info(f"Ended {count} active sessions for user with telegram_id {telegram_id}")
            
            return count
        except Exception as e:
            logger.error(f"Error ending all sessions for user with telegram_id {telegram_id}: {e}")
            return 0
    
    def add_message(self, telegram_id, role, content, session_id=None):
        """
        Добавляет сообщение к сессии.
        
        Args:
            telegram_id: Telegram ID пользователя
            role: Роль отправителя (user/assistant)
            content: Содержимое сообщения
            session_id: ID сессии (опционально)
            
        Returns:
            dict: Данные добавленного сообщения
        """
        try:
            # Если session_id не указан, находим активную сессию
            if not session_id:
                active_session = self.get_active_session(telegram_id)
                if active_session:
                    session_id = active_session.get("id")
                else:
                    # Если активной сессии нет, создаем новую
                    new_session = self.create_session(telegram_id)
                    session_id = new_session.get("id") if new_session else None
            
            if not session_id:
                logger.error(f"Cannot add message: No active session for user {telegram_id}")
                return None
            
            # Работаем с листом сообщений
            worksheet = self.sheet.worksheet(self.messages_sheet_name)
            
            # Получаем следующий ID
            message_id = self._get_next_id(self.messages_sheet_name)
            current_time = datetime.now().isoformat()
            
            # Создаем запись сообщения
            new_message = [
                message_id,
                session_id,
                telegram_id,
                role,
                content,
                current_time
            ]
            
            # Добавляем сообщение
            worksheet.append_row([str(val) for val in new_message])
            
            # Получаем заголовки
            headers = worksheet.row_values(1)
            
            # Создаем словарь с данными сообщения
            message_data = dict(zip(headers, new_message))
            
            # Обновляем время последней активности в сессии
            self.update_session(session_id, {"last_active": current_time})
            
            logger.info(f"Added message to session {session_id} for user {telegram_id}")
            
            return message_data
        except Exception as e:
            logger.error(f"Error adding message for user {telegram_id}: {e}")
            return None
    
    def get_session_messages(self, session_id):
        """
        Получает все сообщения сессии.
        
        Args:
            session_id: ID сессии
            
        Returns:
            list: Список сообщений сессии
        """
        try:
            worksheet = self.sheet.worksheet(self.messages_sheet_name)
            
            # Получаем заголовки
            headers = worksheet.row_values(1)
            
            # Находим все строки с данным session_id
            cells = worksheet.findall(str(session_id), in_column=2)
            
            messages = []
            for cell in cells:
                row = worksheet.row_values(cell.row)
                message_data = dict(zip(headers, row))
                messages.append({
                    "role": message_data.get("role", ""),
                    "content": message_data.get("content", "")
                })
            
            return messages
        except Exception as e:
            logger.error(f"Error getting messages for session {session_id}: {e}")
            return []
    
    def add_feedback(self, telegram_id=None, username=None, first_name=None, last_name=None, 
                       session_id=None, rating=None, comment=None):
        """
        Добавляет новый отзыв в таблицу отзывов.
        
        Args:
            telegram_id (int): Telegram ID пользователя
            username (str, optional): Имя пользователя в Telegram
            first_name (str, optional): Имя пользователя
            last_name (str, optional): Фамилия пользователя
            session_id (int, optional): ID сессии
            rating (str): Рейтинг (оценка)
            comment (str, optional): Комментарий к отзыву
        """
        logger.info(f"Добавление отзыва от пользователя {telegram_id}: {rating}")
        
        try:
            # Работаем с листом отзывов
            feedback_sheet = self.sheet.worksheet(self.feedback_sheet_name)
            
            # Получаем следующий ID для отзыва
            feedback_id = self._get_next_id(self.feedback_sheet_name)
            current_time = datetime.now().isoformat()
            
            # Создаем отзыв
            new_feedback = [
                feedback_id,
                telegram_id,
                username,
                first_name,
                last_name,
                session_id,
                rating,
                comment or "",
                current_time
            ]
            
            # Добавляем отзыв в таблицу
            feedback_sheet.append_row([str(val) for val in new_feedback])
            
            logger.info(f"Добавлен отзыв от пользователя {telegram_id}: {rating}")
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении отзыва от пользователя {telegram_id}: {e}")
            
    def has_user_used_feedback_bonus(self, telegram_id):
        """
        Проверяет, использовал ли пользователь бонус за обратную связь.
        
        Args:
            telegram_id (int): Telegram ID пользователя
            
        Returns:
            bool: True если пользователь уже использовал бонус, иначе False
        """
        try:
            user_data = self.get_user_by_telegram_id(telegram_id)
            if user_data and "feedback_bonus_used" in user_data:
                return user_data["feedback_bonus_used"].lower() == "true"
            return False
        except Exception as e:
            logger.error(f"Ошибка при проверке использования бонуса пользователем {telegram_id}: {e}")
            return False
    
    def set_feedback_bonus_used(self, telegram_id, used=True):
        """
        Устанавливает статус использования бонуса за обратную связь.
        
        Args:
            telegram_id (int): Telegram ID пользователя
            used (bool): Статус использования бонуса
        """
        try:
            self.update_user(telegram_id, {"feedback_bonus_used": str(used)})
            logger.info(f"Установлен статус использования бонуса для пользователя {telegram_id}: {used}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при установке статуса бонуса для пользователя {telegram_id}: {e}")
            return False
            
    def set_feedback_bonus_available(self, telegram_id, available=True):
        """
        Устанавливает доступность бонуса за обратную связь.
        
        Args:
            telegram_id (int): Telegram ID пользователя
            available (bool): Доступен ли бонус
        """
        try:
            self.update_user(telegram_id, {"feedback_bonus_available": str(available)})
            logger.info(f"Установлена доступность бонуса для пользователя {telegram_id}: {available}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при установке доступности бонуса для пользователя {telegram_id}: {e}")
            return False
    
    def get_all_feedback(self) -> List[Dict[str, Any]]:
        """
        Получает все отзывы пользователей.
        
        Returns:
            Список всех отзывов
        """
        try:
            feedback_sheet = self.sheet.worksheet(self.feedback_sheet_name)
            
            # Получаем заголовки и все данные
            all_values = feedback_sheet.get_all_values()
            
            if not all_values or len(all_values) < 2:
                return []
            
            headers = all_values[0]
            data = all_values[1:]
            
            # Преобразуем в список словарей
            feedback_list = [dict(zip(headers, row)) for row in data]
            
            return feedback_list
        except Exception as e:
            logger.error(f"Ошибка при получении всех отзывов: {e}")
            return []