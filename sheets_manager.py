"""
Google Sheets интеграция для хранения данных вместо PostgreSQL.
Использует gspread для работы с Google Sheets API.
"""
import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Настройка логирования
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class SheetsManager:
    """
    Менеджер для работы с Google Sheets вместо базы данных PostgreSQL.
    Хранит все данные бота в Google Sheets: пользователей, сессии, сообщения и обратную связь.
    """
    
    def __init__(self, creds_path: Optional[str] = None, spreadsheet_key: Optional[str] = None):
        """
        Инициализирует соединение с Google Sheets.
        
        Args:
            creds_path: Путь к JSON-файлу с учетными данными сервисного аккаунта
            spreadsheet_key: Идентификатор таблицы Google Sheets
        """
        self.creds_path = creds_path or os.environ.get("GOOGLE_CREDENTIALS_PATH")
        self.spreadsheet_key = spreadsheet_key or os.environ.get("GOOGLE_SHEETS_KEY")
        self.client = None
        self.sheet = None
        
        # Названия листов для каждого типа данных
        self.users_sheet_name = "Users"
        self.sessions_sheet_name = "Sessions"
        self.messages_sheet_name = "Messages"
        self.feedback_sheet_name = "Feedback"
        
        # Кэш для уменьшения количества запросов к API
        self.users_cache = {}  # user_id -> user_data
        self.sessions_cache = {}  # session_id -> session_data
        
        try:
            self._connect()
            self._create_sheets_if_not_exist()
        except Exception as e:
            logger.error(f"Ошибка при инициализации Google Sheets: {e}")
            logger.warning("Работаем в режиме без сохранения данных.")
    
    def _connect(self):
        """Устанавливает соединение с Google Sheets API."""
        if not self.creds_path or not self.spreadsheet_key:
            raise ValueError("GOOGLE_CREDENTIALS_PATH и GOOGLE_SHEETS_KEY должны быть указаны.")
            
        if not os.path.exists(self.creds_path):
            raise FileNotFoundError(f"Файл с учетными данными не найден: {self.creds_path}")
        
        try:
            # Определяем области доступа
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            
            # Получаем учетные данные из файла
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.creds_path, scope)
            
            # Создаем клиент gspread
            self.client = gspread.authorize(creds)
            
            # Открываем таблицу по ключу
            self.sheet = self.client.open_by_key(self.spreadsheet_key)
            
            logger.info(f"Успешно подключились к Google Sheets: {self.sheet.title}")
        except Exception as e:
            logger.error(f"Ошибка при подключении к Google Sheets: {e}")
            raise
    
    def _create_sheets_if_not_exist(self):
        """Создает необходимые листы, если они не существуют."""
        try:
            # Получаем список существующих листов
            existing_sheets = [worksheet.title for worksheet in self.sheet.worksheets()]
            
            # Создаем лист Users, если его нет
            if self.users_sheet_name not in existing_sheets:
                users_sheet = self.sheet.add_worksheet(title=self.users_sheet_name, rows=1000, cols=10)
                users_headers = ["id", "telegram_id", "username", "first_name", "last_name", 
                                "language_level", "created_at", "last_activity", 
                                "last_discussion_date", "discussions_count", "feedback_bonus_used"]
                users_sheet.append_row(users_headers)
                logger.info(f"Создан лист {self.users_sheet_name}")
            
            # Создаем лист Sessions, если его нет
            if self.sessions_sheet_name not in existing_sheets:
                sessions_sheet = self.sheet.add_worksheet(title=self.sessions_sheet_name, rows=1000, cols=10)
                sessions_headers = ["id", "user_id", "telegram_id", "started_at", "ended_at", 
                                  "messages_count", "is_active"]
                sessions_sheet.append_row(sessions_headers)
                logger.info(f"Создан лист {self.sessions_sheet_name}")
            
            # Создаем лист Messages, если его нет
            if self.messages_sheet_name not in existing_sheets:
                messages_sheet = self.sheet.add_worksheet(title=self.messages_sheet_name, rows=5000, cols=10)
                messages_headers = ["id", "session_id", "role", "content", 
                                   "corrections", "timestamp"]
                messages_sheet.append_row(messages_headers)
                logger.info(f"Создан лист {self.messages_sheet_name}")
            
            # Создаем лист Feedback, если его нет
            if self.feedback_sheet_name not in existing_sheets:
                feedback_sheet = self.sheet.add_worksheet(title=self.feedback_sheet_name, rows=1000, cols=10)
                feedback_headers = ["id", "user_id", "telegram_id", "username", "session_id", 
                                   "rating", "comment", "timestamp"]
                feedback_sheet.append_row(feedback_headers)
                logger.info(f"Создан лист {self.feedback_sheet_name}")
                
            logger.info("Все необходимые листы созданы")
        except Exception as e:
            logger.error(f"Ошибка при создании листов: {e}")
            raise
    
    def _get_next_id(self, worksheet_name: str) -> int:
        """
        Получает следующий доступный ID для указанного листа.
        
        Args:
            worksheet_name: Название листа
            
        Returns:
            Следующий доступный ID
        """
        try:
            worksheet = self.sheet.worksheet(worksheet_name)
            values = worksheet.get_all_values()
            
            # Если таблица пуста или содержит только заголовки
            if len(values) <= 1:
                return 1
                
            # Пропускаем строку заголовков и находим максимальный ID
            ids = [int(row[0]) for row in values[1:] if row and row[0].isdigit()]
            return max(ids) + 1 if ids else 1
        except Exception as e:
            logger.error(f"Ошибка при получении следующего ID для {worksheet_name}: {e}")
            return int(time.time())  # В случае ошибки используем временную метку
    
    def get_or_create_user(self, telegram_id: int, username: Optional[str] = None, 
                           first_name: Optional[str] = None, last_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Получает или создает пользователя по Telegram ID.
        
        Args:
            telegram_id: Telegram ID пользователя
            username: Имя пользователя в Telegram
            first_name: Имя пользователя
            last_name: Фамилия пользователя
            
        Returns:
            Данные пользователя
        """
        # Проверяем кэш
        if telegram_id in self.users_cache:
            # Обновляем last_activity в кэше
            self.users_cache[telegram_id]["last_activity"] = datetime.now().isoformat()
            return self.users_cache[telegram_id]
        
        try:
            users_sheet = self.sheet.worksheet(self.users_sheet_name)
            
            # Ищем пользователя по telegram_id
            cell = users_sheet.findall(str(telegram_id))
            user_exists = False
            user_data = {}
            
            for found_cell in cell:
                # Если найдена ячейка во втором столбце (telegram_id)
                if found_cell.col == 2:
                    row = users_sheet.row_values(found_cell.row)
                    headers = users_sheet.row_values(1)
                    
                    # Создаем словарь с данными пользователя
                    user_data = dict(zip(headers, row))
                    user_exists = True
                    
                    # Обновляем last_activity
                    current_time = datetime.now().isoformat()
                    users_sheet.update_cell(found_cell.row, headers.index("last_activity") + 1, current_time)
                    user_data["last_activity"] = current_time
                    break
            
            # Если пользователь не найден, создаем его
            if not user_exists:
                # Получаем следующий доступный ID
                user_id = self._get_next_id(self.users_sheet_name)
                current_time = datetime.now().isoformat()
                
                # Подготавливаем данные нового пользователя
                new_user = [
                    user_id,
                    telegram_id,
                    username or "",
                    first_name or "",
                    last_name or "",
                    "",  # language_level
                    current_time,  # created_at
                    current_time,  # last_activity
                    "",  # last_discussion_date
                    0,  # discussions_count
                    False  # feedback_bonus_used
                ]
                
                # Добавляем нового пользователя
                users_sheet.append_row(new_user)
                
                # Создаем словарь с данными нового пользователя
                headers = users_sheet.row_values(1)
                user_data = dict(zip(headers, [str(val) for val in new_user]))
                
                logger.info(f"Создан новый пользователь: {telegram_id}")
            
            # Сохраняем в кэш
            self.users_cache[telegram_id] = user_data
            return user_data
            
        except Exception as e:
            logger.error(f"Ошибка при получении/создании пользователя {telegram_id}: {e}")
            
            # В случае ошибки возвращаем базовые данные
            return {
                "id": str(int(time.time())),
                "telegram_id": str(telegram_id),
                "username": username or "",
                "first_name": first_name or "",
                "last_name": last_name or "",
                "language_level": "",
                "created_at": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat(),
                "last_discussion_date": "",
                "discussions_count": "0",
                "feedback_bonus_used": "False"
            }
    
    def update_user(self, telegram_id: int, data: Dict[str, Any]) -> None:
        """
        Обновляет данные пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            data: Новые данные пользователя
        """
        try:
            users_sheet = self.sheet.worksheet(self.users_sheet_name)
            
            # Ищем пользователя по telegram_id
            cell = users_sheet.findall(str(telegram_id))
            for found_cell in cell:
                # Если найдена ячейка во втором столбце (telegram_id)
                if found_cell.col == 2:
                    headers = users_sheet.row_values(1)
                    row = found_cell.row
                    
                    # Обновляем каждое поле из data
                    for field, value in data.items():
                        if field in headers:
                            col = headers.index(field) + 1
                            value_str = str(value) if value is not None else ""
                            users_sheet.update_cell(row, col, value_str)
                    
                    # Обновляем кэш
                    if telegram_id in self.users_cache:
                        self.users_cache[telegram_id].update(data)
                    
                    logger.info(f"Обновлены данные пользователя {telegram_id}")
                    return
            
            logger.warning(f"Пользователь {telegram_id} не найден при обновлении")
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении пользователя {telegram_id}: {e}")
    
    def create_session(self, telegram_id: int) -> Dict[str, Any]:
        """
        Создает новую сессию для пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            Данные созданной сессии
        """
        try:
            # Получаем данные пользователя
            user_data = self.get_or_create_user(telegram_id)
            user_id = user_data["id"]
            
            # Работаем с листом сессий
            sessions_sheet = self.sheet.worksheet(self.sessions_sheet_name)
            
            # Получаем следующий ID для сессии
            session_id = self._get_next_id(self.sessions_sheet_name)
            current_time = datetime.now().isoformat()
            
            # Создаем новую сессию
            new_session = [
                session_id,
                user_id,
                telegram_id,
                current_time,  # started_at
                "",  # ended_at
                0,  # messages_count
                True  # is_active
            ]
            
            # Добавляем сессию в таблицу
            sessions_sheet.append_row([str(val) for val in new_session])
            
            # Создаем словарь с данными сессии
            headers = sessions_sheet.row_values(1)
            session_data = dict(zip(headers, [str(val) for val in new_session]))
            
            # Сохраняем сессию в кэш
            self.sessions_cache[session_id] = session_data
            
            logger.info(f"Создана новая сессия для пользователя {telegram_id}")
            return session_data
            
        except Exception as e:
            logger.error(f"Ошибка при создании сессии для пользователя {telegram_id}: {e}")
            
            # В случае ошибки возвращаем базовые данные
            session_id = int(time.time())
            return {
                "id": str(session_id),
                "user_id": user_data.get("id", "0") if 'user_data' in locals() else "0",
                "telegram_id": str(telegram_id),
                "started_at": datetime.now().isoformat(),
                "ended_at": "",
                "messages_count": "0",
                "is_active": "True"
            }
    
    def get_active_session(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает активную сессию пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            Данные активной сессии или None, если активной сессии нет
        """
        try:
            sessions_sheet = self.sheet.worksheet(self.sessions_sheet_name)
            
            # Находим все сессии пользователя
            telegram_id_cells = sessions_sheet.findall(str(telegram_id))
            active_session = None
            
            for cell in telegram_id_cells:
                # Проверяем, что это столбец telegram_id
                if cell.col == 3:
                    row = sessions_sheet.row_values(cell.row)
                    headers = sessions_sheet.row_values(1)
                    session_data = dict(zip(headers, row))
                    
                    # Проверяем, активна ли сессия
                    if session_data.get("is_active", "").lower() == "true":
                        active_session = session_data
                        
                        # Обновляем кэш
                        session_id = int(session_data["id"])
                        self.sessions_cache[session_id] = session_data
                        break
            
            return active_session
            
        except Exception as e:
            logger.error(f"Ошибка при получении активной сессии для пользователя {telegram_id}: {e}")
            return None
    
    def end_session(self, telegram_id: int) -> None:
        """
        Завершает активную сессию пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
        """
        try:
            active_session = self.get_active_session(telegram_id)
            if not active_session:
                logger.warning(f"Нет активной сессии для завершения у пользователя {telegram_id}")
                return
            
            sessions_sheet = self.sheet.worksheet(self.sessions_sheet_name)
            
            # Находим сессию в таблице
            session_id = active_session["id"]
            session_cells = sessions_sheet.findall(session_id)
            
            for cell in session_cells:
                # Проверяем, что это столбец id
                if cell.col == 1:
                    headers = sessions_sheet.row_values(1)
                    row = cell.row
                    
                    # Обновляем поля сессии
                    current_time = datetime.now().isoformat()
                    
                    # Устанавливаем ended_at
                    ended_at_col = headers.index("ended_at") + 1
                    sessions_sheet.update_cell(row, ended_at_col, current_time)
                    
                    # Устанавливаем is_active в False
                    is_active_col = headers.index("is_active") + 1
                    sessions_sheet.update_cell(row, is_active_col, "False")
                    
                    # Обновляем messages_count
                    messages_count = self.count_session_messages(int(session_id))
                    messages_count_col = headers.index("messages_count") + 1
                    sessions_sheet.update_cell(row, messages_count_col, str(messages_count))
                    
                    # Обновляем кэш
                    if int(session_id) in self.sessions_cache:
                        self.sessions_cache[int(session_id)].update({
                            "ended_at": current_time,
                            "is_active": "False",
                            "messages_count": str(messages_count)
                        })
                    
                    logger.info(f"Завершена сессия {session_id} для пользователя {telegram_id}")
                    return
            
            logger.warning(f"Сессия {session_id} не найдена при завершении")
            
        except Exception as e:
            logger.error(f"Ошибка при завершении сессии для пользователя {telegram_id}: {e}")
    
    def add_message(self, telegram_id: int, role: str, content: str, 
                    corrections: Optional[Dict[str, Any]] = None) -> None:
        """
        Добавляет сообщение в активную сессию пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            role: Роль ('user' или 'assistant')
            content: Содержимое сообщения
            corrections: Исправления (опционально)
        """
        try:
            # Получаем активную сессию
            active_session = self.get_active_session(telegram_id)
            
            # Если активной сессии нет, создаем новую
            if not active_session:
                active_session = self.create_session(telegram_id)
            
            session_id = active_session["id"]
            
            # Работаем с листом сообщений
            messages_sheet = self.sheet.worksheet(self.messages_sheet_name)
            
            # Получаем следующий ID для сообщения
            message_id = self._get_next_id(self.messages_sheet_name)
            current_time = datetime.now().isoformat()
            
            # Подготавливаем данные сообщения
            corrections_json = json.dumps(corrections) if corrections else ""
            
            # Обрезаем длинные сообщения, чтобы они поместились в ячейку
            max_content_length = 50000  # Примерное ограничение для ячейки Google Sheets
            if len(content) > max_content_length:
                content = content[:max_content_length-100] + "... [сообщение обрезано из-за длины]"
            
            new_message = [
                message_id,
                session_id,
                role,
                content,
                corrections_json,
                current_time
            ]
            
            # Добавляем сообщение в таблицу
            messages_sheet.append_row([str(val) for val in new_message])
            
            # Обновляем счетчик сообщений в сессии
            sessions_sheet = self.sheet.worksheet(self.sessions_sheet_name)
            session_cells = sessions_sheet.findall(str(session_id))
            
            for cell in session_cells:
                # Проверяем, что это столбец id
                if cell.col == 1:
                    headers = sessions_sheet.row_values(1)
                    row = cell.row
                    
                    # Обновляем messages_count
                    messages_count_col = headers.index("messages_count") + 1
                    current_count = int(active_session.get("messages_count", 0)) + 1
                    sessions_sheet.update_cell(row, messages_count_col, str(current_count))
                    
                    # Обновляем кэш
                    if int(session_id) in self.sessions_cache:
                        self.sessions_cache[int(session_id)]["messages_count"] = str(current_count)
                    
                    break
            
            logger.info(f"Добавлено сообщение от {role} в сессию {session_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении сообщения для пользователя {telegram_id}: {e}")
    
    def get_session_messages(self, telegram_id: int) -> List[Dict[str, str]]:
        """
        Получает все сообщения из активной сессии пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            Список сообщений в формате для API
        """
        try:
            active_session = self.get_active_session(telegram_id)
            if not active_session:
                logger.warning(f"Нет активной сессии для получения сообщений у пользователя {telegram_id}")
                return []
            
            session_id = active_session["id"]
            
            # Получаем сообщения из таблицы
            messages_sheet = self.sheet.worksheet(self.messages_sheet_name)
            all_messages = messages_sheet.get_all_values()
            headers = all_messages[0]
            
            # Фильтруем сообщения по session_id
            session_messages = []
            for row in all_messages[1:]:  # Пропускаем заголовки
                message_data = dict(zip(headers, row))
                if message_data.get("session_id") == session_id:
                    session_messages.append({
                        "role": message_data.get("role", ""),
                        "content": message_data.get("content", "")
                    })
            
            return session_messages
            
        except Exception as e:
            logger.error(f"Ошибка при получении сообщений для пользователя {telegram_id}: {e}")
            return []
    
    def count_session_messages(self, session_id: int) -> int:
        """
        Подсчитывает количество сообщений в сессии.
        
        Args:
            session_id: ID сессии
            
        Returns:
            Количество сообщений
        """
        try:
            messages_sheet = self.sheet.worksheet(self.messages_sheet_name)
            all_messages = messages_sheet.get_all_values()
            headers = all_messages[0]
            
            # Индекс столбца session_id
            session_id_idx = headers.index("session_id")
            
            # Подсчитываем сообщения
            count = 0
            for row in all_messages[1:]:  # Пропускаем заголовки
                if row[session_id_idx] == str(session_id):
                    count += 1
            
            return count
            
        except Exception as e:
            logger.error(f"Ошибка при подсчете сообщений для сессии {session_id}: {e}")
            return 0
    
    def add_feedback(self, telegram_id: int, rating: str, comment: Optional[str] = None) -> None:
        """
        Добавляет отзыв от пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            rating: Оценка ('helpful', 'okay', 'not_helpful')
            comment: Комментарий (опционально)
        """
        try:
            # Получаем данные пользователя
            user_data = self.get_or_create_user(telegram_id)
            user_id = user_data["id"]
            username = user_data.get("username", "")
            
            # Получаем активную сессию (если есть)
            active_session = self.get_active_session(telegram_id)
            session_id = active_session["id"] if active_session else ""
            
            # Работаем с листом отзывов
            feedback_sheet = self.sheet.worksheet(self.feedback_sheet_name)
            
            # Получаем следующий ID для отзыва
            feedback_id = self._get_next_id(self.feedback_sheet_name)
            current_time = datetime.now().isoformat()
            
            # Создаем отзыв
            new_feedback = [
                feedback_id,
                user_id,
                telegram_id,
                username,
                session_id,
                rating,
                comment or "",
                current_time
            ]
            
            # Добавляем отзыв в таблицу
            feedback_sheet.append_row([str(val) for val in new_feedback])
            
            logger.info(f"Добавлен отзыв от пользователя {telegram_id}: {rating}")
            
            # Если пользователь оставил бонусный отзыв с комментарием, обновляем его статус
            if comment and len(comment.strip()) > 0:
                self.update_user(telegram_id, {"feedback_bonus_used": "True"})
                logger.info(f"Пользователь {telegram_id} использовал бонус за отзыв")
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении отзыва от пользователя {telegram_id}: {e}")
    
    def get_all_feedback(self) -> List[Dict[str, Any]]:
        """
        Получает все отзывы пользователей.
        
        Returns:
            Список всех отзывов
        """
        try:
            feedback_sheet = self.sheet.worksheet(self.feedback_sheet_name)
            all_feedback = feedback_sheet.get_all_values()
            
            if len(all_feedback) <= 1:  # Только заголовки или пусто
                return []
            
            headers = all_feedback[0]
            feedback_list = []
            
            for row in all_feedback[1:]:  # Пропускаем заголовки
                feedback_data = dict(zip(headers, row))
                feedback_list.append(feedback_data)
            
            # Сортируем по убыванию времени
            feedback_list.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return feedback_list
            
        except Exception as e:
            logger.error(f"Ошибка при получении всех отзывов: {e}")
            return []
    
    def update_language_level(self, telegram_id: int, language_level: str) -> None:
        """
        Обновляет уровень языка пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            language_level: Уровень языка (A1, A2, B1, B2, C1, C2)
        """
        self.update_user(telegram_id, {"language_level": language_level})
        logger.info(f"Обновлен уровень языка пользователя {telegram_id}: {language_level}")
    
    def increment_discussions_count(self, telegram_id: int) -> int:
        """
        Увеличивает счетчик дискуссий пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            Новое количество дискуссий
        """
        try:
            user_data = self.get_or_create_user(telegram_id)
            current_count = int(user_data.get("discussions_count", 0))
            new_count = current_count + 1
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # Обновляем счетчик и дату последней дискуссии
            self.update_user(telegram_id, {
                "discussions_count": str(new_count),
                "last_discussion_date": current_date
            })
            
            logger.info(f"Увеличен счетчик дискуссий пользователя {telegram_id}: {new_count}")
            return new_count
            
        except Exception as e:
            logger.error(f"Ошибка при увеличении счетчика дискуссий пользователя {telegram_id}: {e}")
            return 0
    
    def has_user_used_feedback_bonus(self, telegram_id: int) -> bool:
        """
        Проверяет, использовал ли пользователь бонус за отзыв.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            True, если пользователь уже использовал бонус, иначе False
        """
        try:
            user_data = self.get_or_create_user(telegram_id)
            bonus_used = user_data.get("feedback_bonus_used", "").lower() == "true"
            return bonus_used
            
        except Exception as e:
            logger.error(f"Ошибка при проверке бонуса за отзыв для пользователя {telegram_id}: {e}")
            return False