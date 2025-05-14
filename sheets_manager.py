import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import gspread
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound
from oauth2client.service_account import ServiceAccountCredentials

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Google Sheets API
SHEETS_API_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class SheetsManager:
    """
    Класс для управления данными бота в Google Sheets.
    Обеспечивает хранение пользователей, сессий, истории сообщений и обратной связи.
    """

    def __init__(
        self,
        spreadsheet_key: Optional[str] = None,
        credentials_path: Optional[str] = None,
        retry_limit: int = 3,
        retry_delay: int = 1,
    ):
        """
        Инициализация менеджера Google Sheets.

        Args:
            spreadsheet_key: ID Google таблицы (по умолчанию из переменной окружения)
            credentials_path: Путь к файлу учетных данных (по умолчанию из переменной окружения)
            retry_limit: Максимальное количество попыток повторных запросов при ошибках API
            retry_delay: Задержка между повторными запросами в секундах
        """
        # Настройка подключения
        self.spreadsheet_key = spreadsheet_key or os.environ.get("GOOGLE_SHEETS_KEY")
        self.credentials_path = credentials_path or os.environ.get(
            "GOOGLE_CREDENTIALS_PATH"
        )
        self.retry_limit = retry_limit
        self.retry_delay = retry_delay
        self.client = None
        self.spreadsheet = None

        # Проверка наличия необходимых параметров
        if not self.spreadsheet_key:
            logger.warning("GOOGLE_SHEETS_KEY не задан в переменных окружения")
            return

        if not self.credentials_path:
            logger.warning("GOOGLE_CREDENTIALS_PATH не задан в переменных окружения")
            return

        if not os.path.exists(self.credentials_path):
            logger.warning(
                f"Файл с учетными данными сервисного аккаунта не найден: {self.credentials_path}"
            )
            return

        try:
            # Аутентификация и подключение
            self._authenticate()
            self._open_spreadsheet()
            self._ensure_required_sheets()
            logger.info("Подключение к Google Sheets успешно установлено")
        except Exception as e:
            logger.error(f"Ошибка при инициализации SheetsManager: {e}")

    def _authenticate(self):
        """Аутентификация с помощью учетных данных сервисного аккаунта"""
        try:
            # Проверяем наличие переменной окружения с JSON данными
            google_creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
            
            if google_creds_json:
                # Используем JSON из переменной окружения
                import json
                from tempfile import NamedTemporaryFile
                
                # Создаем временный файл для хранения учетных данных
                with NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp:
                    temp.write(google_creds_json)
                    temp_creds_path = temp.name
                
                try:
                    # Используем временный файл для создания учетных данных
                    credentials = ServiceAccountCredentials.from_json_keyfile_name(
                        temp_creds_path, SHEETS_API_SCOPES
                    )
                    self.client = gspread.authorize(credentials)
                finally:
                    # Удаляем временный файл
                    if os.path.exists(temp_creds_path):
                        os.unlink(temp_creds_path)
            else:
                # Используем файл, если переменная окружения не найдена
                credentials = ServiceAccountCredentials.from_json_keyfile_name(
                    self.credentials_path, SHEETS_API_SCOPES
                )
                self.client = gspread.authorize(credentials)
        except Exception as e:
            logger.error(f"Ошибка аутентификации в Google Sheets API: {e}")
            raise

    def _open_spreadsheet(self):
        """Открывает таблицу по ID"""
        try:
            self.spreadsheet = self.client.open_by_key(self.spreadsheet_key)
            logger.info(f"Таблица успешно открыта: {self.spreadsheet.title}")
        except SpreadsheetNotFound:
            logger.error(f"Таблица не найдена: {self.spreadsheet_key}")
            raise
        except Exception as e:
            logger.error(f"Ошибка при открытии таблицы: {e}")
            raise

    def _ensure_required_sheets(self):
        """Создает необходимые листы, если их нет"""
        required_sheets = {
            "users": ["id", "telegram_id", "username", "first_name", "last_name", "created_at"],
            "sessions": ["id", "user_id", "language_level", "created_at", "updated_at", "is_active", "data"],
            "messages": ["id", "session_id", "role", "content", "created_at"],
            "feedback": ["id", "user_id", "session_id", "rating", "comment", "created_at"]
        }

        existing_sheets = [ws.title for ws in self.spreadsheet.worksheets()]

        for sheet_name, columns in required_sheets.items():
            try:
                if sheet_name not in existing_sheets:
                    logger.info(f"Создаю лист '{sheet_name}'")
                    worksheet = self.spreadsheet.add_worksheet(title=sheet_name, rows=1, cols=len(columns))
                    worksheet.append_row(columns)
                else:
                    worksheet = self.spreadsheet.worksheet(sheet_name)
                    # Проверим, есть ли заголовки столбцов
                    headers = worksheet.row_values(1)
                    if not headers:
                        worksheet.append_row(columns)
            except Exception as e:
                logger.error(f"Ошибка при создании листа '{sheet_name}': {e}")

    def _execute_with_retry(self, operation, *args, **kwargs):
        """
        Выполняет операцию с повторными попытками при ошибках API.
        
        Args:
            operation: Функция для выполнения
            *args, **kwargs: Аргументы для функции
            
        Returns:
            Результат операции
        """
        attempt = 0
        last_error = None

        while attempt < self.retry_limit:
            try:
                return operation(*args, **kwargs)
            except APIError as e:
                last_error = e
                attempt += 1
                if attempt < self.retry_limit:
                    logger.warning(
                        f"API ошибка при попытке {attempt}, повторяю через {self.retry_delay} сек: {e}"
                    )
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Превышено количество попыток. Последняя ошибка: {e}")
                    raise
            except Exception as e:
                logger.error(f"Непредвиденная ошибка: {e}")
                raise

        if last_error:
            raise last_error
        
        raise Exception("Превышено максимальное количество попыток")

    # ----- Работа с пользователями -----

    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает пользователя по Telegram ID.
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            Словарь с данными пользователя или None, если не найден
        """
        try:
            if not self.spreadsheet:
                logger.error("Нет подключения к Google Sheets")
                return None

            worksheet = self.spreadsheet.worksheet("users")
            
            # Находим строку с указанным telegram_id
            cell = self._execute_with_retry(
                worksheet.find, str(telegram_id), in_column=2
            )
            
            if not cell:
                return None
                
            row_data = worksheet.row_values(cell.row)
            headers = worksheet.row_values(1)
            
            # Преобразуем данные строки в словарь
            user_data = dict(zip(headers, row_data))
            
            # Преобразуем id и telegram_id в числа
            if "id" in user_data and user_data["id"]:
                user_data["id"] = int(user_data["id"])
            if "telegram_id" in user_data and user_data["telegram_id"]:
                user_data["telegram_id"] = int(user_data["telegram_id"])
                
            return user_data
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя по telegram_id: {e}")
            return None

    def create_user(
        self, 
        telegram_id: int, 
        username: Optional[str] = None, 
        first_name: Optional[str] = None, 
        last_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Создает нового пользователя в таблице users.
        
        Args:
            telegram_id: ID пользователя в Telegram
            username: Имя пользователя в Telegram
            first_name: Имя
            last_name: Фамилия
            
        Returns:
            Словарь с данными созданного пользователя или None при ошибке
        """
        try:
            if not self.spreadsheet:
                logger.error("Нет подключения к Google Sheets")
                return None

            # Проверяем, существует ли пользователь
            existing_user = self.get_user_by_telegram_id(telegram_id)
            if existing_user:
                return existing_user

            worksheet = self.spreadsheet.worksheet("users")
            
            # Получаем последний ID
            id_col = worksheet.col_values(1)
            next_id = 1
            if len(id_col) > 1:  # Если есть другие записи кроме заголовка
                last_id = id_col[-1]
                if last_id.isdigit():
                    next_id = int(last_id) + 1
            
            # Подготавливаем данные для добавления
            now = datetime.now().isoformat()
            user_data = [
                next_id,
                telegram_id,
                username or "",
                first_name or "",
                last_name or "",
                now
            ]
            
            # Добавляем пользователя
            self._execute_with_retry(worksheet.append_row, user_data)
            
            # Возвращаем данные в формате словаря
            headers = worksheet.row_values(1)
            user_dict = dict(zip(headers, user_data))
            
            return user_dict
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя: {e}")
            return None

    def update_user(self, user_id: int, data: Dict[str, Any]) -> bool:
        """
        Обновляет данные пользователя.
        
        Args:
            user_id: ID пользователя в таблице
            data: Словарь с обновляемыми полями
            
        Returns:
            True при успешном обновлении, False при ошибке
        """
        try:
            if not self.spreadsheet:
                logger.error("Нет подключения к Google Sheets")
                return False

            worksheet = self.spreadsheet.worksheet("users")
            
            # Находим строку с указанным ID
            cell = self._execute_with_retry(
                worksheet.find, str(user_id), in_column=1
            )
            
            if not cell:
                logger.warning(f"Пользователь с ID {user_id} не найден")
                return False
            
            # Получаем заголовки и текущие данные
            headers = worksheet.row_values(1)
            current_row = worksheet.row_values(cell.row)
            current_data = dict(zip(headers, current_row))
            
            # Обновляем данные
            for key, value in data.items():
                if key in headers:
                    col_idx = headers.index(key) + 1  # +1 т.к. индексация с 1
                    self._execute_with_retry(
                        worksheet.update_cell, cell.row, col_idx, str(value)
                    )
                    current_data[key] = value
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении пользователя: {e}")
            return False

    # ----- Работа с сессиями -----

    def create_session(
        self, 
        user_id: int, 
        language_level: Optional[str] = None, 
        session_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Создает новую сессию для пользователя.
        
        Args:
            user_id: ID пользователя в таблице
            language_level: Уровень владения языком (A1-C2)
            session_data: Дополнительные данные сессии
            
        Returns:
            Словарь с данными созданной сессии или None при ошибке
        """
        try:
            if not self.spreadsheet:
                logger.error("Нет подключения к Google Sheets")
                return None

            worksheet = self.spreadsheet.worksheet("sessions")
            
            # Получаем последний ID
            id_col = worksheet.col_values(1)
            next_id = 1
            if len(id_col) > 1:  # Если есть другие записи кроме заголовка
                last_id = id_col[-1]
                if last_id.isdigit():
                    next_id = int(last_id) + 1
            
            # Подготавливаем данные для добавления
            now = datetime.now().isoformat()
            
            # Если есть дополнительные данные, сериализуем их в JSON
            json_data = "{}"
            if session_data:
                json_data = json.dumps(session_data)
            
            session_row = [
                next_id,
                user_id,
                language_level or "",
                now,  # created_at
                now,  # updated_at
                True,  # is_active
                json_data  # data
            ]
            
            # Добавляем сессию
            self._execute_with_retry(worksheet.append_row, session_row)
            
            # Возвращаем данные в формате словаря
            headers = worksheet.row_values(1)
            session_dict = dict(zip(headers, session_row))
            
            # Если data - это JSON строка, преобразуем её обратно в словарь
            if "data" in session_dict and isinstance(session_dict["data"], str):
                try:
                    session_dict["data"] = json.loads(session_dict["data"])
                except json.JSONDecodeError:
                    session_dict["data"] = {}
            
            return session_dict
        except Exception as e:
            logger.error(f"Ошибка при создании сессии: {e}")
            return None

    def get_active_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает активную сессию пользователя.
        
        Args:
            user_id: ID пользователя в таблице
            
        Returns:
            Словарь с данными активной сессии или None, если не найдена
        """
        try:
            if not self.spreadsheet:
                logger.error("Нет подключения к Google Sheets")
                return None

            worksheet = self.spreadsheet.worksheet("sessions")
            
            # Получаем все сессии пользователя
            user_id_str = str(user_id)
            all_sessions = worksheet.get_all_records()
            
            # Находим активную сессию
            active_session = None
            for session in all_sessions:
                if str(session.get("user_id")) == user_id_str and session.get("is_active") in (True, "TRUE", "True", "true", 1, "1"):
                    active_session = session
                    break
            
            if not active_session:
                return None
            
            # Если data - это JSON строка, преобразуем её в словарь
            if "data" in active_session and isinstance(active_session["data"], str):
                try:
                    active_session["data"] = json.loads(active_session["data"])
                except json.JSONDecodeError:
                    active_session["data"] = {}
            
            return active_session
        except Exception as e:
            logger.error(f"Ошибка при получении активной сессии: {e}")
            return None

    def update_session(self, session_id: int, data: Dict[str, Any]) -> bool:
        """
        Обновляет данные сессии.
        
        Args:
            session_id: ID сессии
            data: Словарь с обновляемыми полями
            
        Returns:
            True при успешном обновлении, False при ошибке
        """
        try:
            if not self.spreadsheet:
                logger.error("Нет подключения к Google Sheets")
                return False

            worksheet = self.spreadsheet.worksheet("sessions")
            
            # Находим строку с указанным ID
            cell = self._execute_with_retry(
                worksheet.find, str(session_id), in_column=1
            )
            
            if not cell:
                logger.warning(f"Сессия с ID {session_id} не найдена")
                return False
            
            # Получаем заголовки и текущие данные
            headers = worksheet.row_values(1)
            current_row = worksheet.row_values(cell.row)
            current_data = dict(zip(headers, current_row))
            
            # Особая обработка для поля data
            if "data" in data:
                if isinstance(data["data"], dict):
                    # Если в data передан словарь, сериализуем его в JSON
                    data["data"] = json.dumps(data["data"])
            
            # Всегда обновляем поле updated_at
            data["updated_at"] = datetime.now().isoformat()
            
            # Обновляем данные
            for key, value in data.items():
                if key in headers:
                    col_idx = headers.index(key) + 1  # +1 т.к. индексация с 1
                    self._execute_with_retry(
                        worksheet.update_cell, cell.row, col_idx, str(value)
                    )
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении сессии: {e}")
            return False

    def end_session(self, session_id: int) -> bool:
        """
        Завершает сессию, устанавливая is_active = False.
        
        Args:
            session_id: ID сессии
            
        Returns:
            True при успешном завершении, False при ошибке
        """
        return self.update_session(session_id, {"is_active": False})

    # ----- Работа с сообщениями -----

    def add_message(
        self, 
        session_id: int, 
        role: str, 
        content: str
    ) -> Optional[Dict[str, Any]]:
        """
        Добавляет сообщение в историю сессии.
        
        Args:
            session_id: ID сессии
            role: Роль отправителя ('user' или 'assistant')
            content: Содержание сообщения
            
        Returns:
            Словарь с данными добавленного сообщения или None при ошибке
        """
        try:
            if not self.spreadsheet:
                logger.error("Нет подключения к Google Sheets")
                return None

            worksheet = self.spreadsheet.worksheet("messages")
            
            # Получаем последний ID
            id_col = worksheet.col_values(1)
            next_id = 1
            if len(id_col) > 1:  # Если есть другие записи кроме заголовка
                last_id = id_col[-1]
                if last_id.isdigit():
                    next_id = int(last_id) + 1
            
            # Подготавливаем данные для добавления
            now = datetime.now().isoformat()
            
            message_row = [
                next_id,
                session_id,
                role,
                content,
                now  # created_at
            ]
            
            # Добавляем сообщение
            self._execute_with_retry(worksheet.append_row, message_row)
            
            # Возвращаем данные в формате словаря
            headers = worksheet.row_values(1)
            message_dict = dict(zip(headers, message_row))
            
            return message_dict
        except Exception as e:
            logger.error(f"Ошибка при добавлении сообщения: {e}")
            return None

    def get_session_messages(self, session_id: int) -> List[Dict[str, Any]]:
        """
        Получает все сообщения сессии.
        
        Args:
            session_id: ID сессии
            
        Returns:
            Список словарей с данными сообщений
        """
        try:
            if not self.spreadsheet:
                logger.error("Нет подключения к Google Sheets")
                return []

            worksheet = self.spreadsheet.worksheet("messages")
            
            # Получаем все сообщения
            session_id_str = str(session_id)
            all_messages = worksheet.get_all_records()
            
            # Фильтруем сообщения для указанной сессии
            session_messages = [
                msg for msg in all_messages 
                if str(msg.get("session_id")) == session_id_str
            ]
            
            # Сортируем по ID (для сохранения порядка)
            session_messages.sort(key=lambda x: int(x.get("id", 0)))
            
            return session_messages
        except Exception as e:
            logger.error(f"Ошибка при получении сообщений сессии: {e}")
            return []

    # ----- Работа с обратной связью -----

    def add_feedback(
        self, 
        user_id: int, 
        rating: int, 
        comment: Optional[str] = None, 
        session_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Добавляет обратную связь от пользователя.
        
        Args:
            user_id: ID пользователя
            rating: Оценка (1-5)
            comment: Комментарий
            session_id: ID сессии (опционально)
            
        Returns:
            Словарь с данными добавленной обратной связи или None при ошибке
        """
        try:
            if not self.spreadsheet:
                logger.error("Нет подключения к Google Sheets")
                return None

            worksheet = self.spreadsheet.worksheet("feedback")
            
            # Получаем последний ID
            id_col = worksheet.col_values(1)
            next_id = 1
            if len(id_col) > 1:  # Если есть другие записи кроме заголовка
                last_id = id_col[-1]
                if last_id.isdigit():
                    next_id = int(last_id) + 1
            
            # Подготавливаем данные для добавления
            now = datetime.now().isoformat()
            
            feedback_row = [
                next_id,
                user_id,
                session_id or "",
                rating,
                comment or "",
                now  # created_at
            ]
            
            # Добавляем обратную связь
            self._execute_with_retry(worksheet.append_row, feedback_row)
            
            # Возвращаем данные в формате словаря
            headers = worksheet.row_values(1)
            feedback_dict = dict(zip(headers, feedback_row))
            
            return feedback_dict
        except Exception as e:
            logger.error(f"Ошибка при добавлении обратной связи: {e}")
            return None

    def get_all_feedback(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Получает всю обратную связь из таблицы.
        
        Args:
            limit: Максимальное количество записей
            
        Returns:
            Список словарей с данными обратной связи
        """
        try:
            if not self.spreadsheet:
                logger.error("Нет подключения к Google Sheets")
                return []

            worksheet = self.spreadsheet.worksheet("feedback")
            
            # Получаем все записи обратной связи
            all_feedback = worksheet.get_all_records()
            
            # Сортируем по дате создания (от новых к старым)
            all_feedback.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            # Ограничиваем количество записей
            return all_feedback[:limit]
        except Exception as e:
            logger.error(f"Ошибка при получении обратной связи: {e}")
            return []

    def get_enriched_feedback(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Получает обратную связь с дополнительной информацией о пользователях.
        
        Args:
            limit: Максимальное количество записей
            
        Returns:
            Список словарей с обогащенными данными обратной связи
        """
        try:
            if not self.spreadsheet:
                logger.error("Нет подключения к Google Sheets")
                return []

            # Получаем обратную связь
            feedback_list = self.get_all_feedback(limit)
            
            # Получаем всех пользователей
            users_worksheet = self.spreadsheet.worksheet("users")
            all_users = users_worksheet.get_all_records()
            users_dict = {str(user.get("id")): user for user in all_users}
            
            # Обогащаем данные обратной связи информацией о пользователях
            for feedback in feedback_list:
                user_id = str(feedback.get("user_id", ""))
                user_data = users_dict.get(user_id, {})
                
                feedback["username"] = user_data.get("username", "")
                feedback["first_name"] = user_data.get("first_name", "")
                feedback["last_name"] = user_data.get("last_name", "")
                feedback["telegram_id"] = user_data.get("telegram_id", "")
            
            return feedback_list
        except Exception as e:
            logger.error(f"Ошибка при получении обогащенной обратной связи: {e}")
            return []

    # ----- Служебные методы -----

    def health_check(self) -> bool:
        """
        Проверяет доступность Google Sheets API.
        
        Returns:
            True, если соединение работает, иначе False
        """
        try:
            if not self.spreadsheet:
                return False
                
            # Пытаемся получить заголовок таблицы
            title = self.spreadsheet.title
            return True
        except Exception as e:
            logger.error(f"Ошибка при проверке соединения с Google Sheets: {e}")
            return False


# Создаем глобальный экземпляр класса для использования в других модулях
sheets_manager = None


def init_sheets_manager():
    """Инициализирует глобальный экземпляр SheetsManager"""
    global sheets_manager
    
    # Проверяем, существуют ли необходимые переменные окружения
    spreadsheet_key = os.environ.get("GOOGLE_SHEETS_KEY")
    credentials_path = os.environ.get("GOOGLE_CREDENTIALS_PATH")
    
    if not spreadsheet_key or not credentials_path:
        logger.warning("GOOGLE_SHEETS_KEY или GOOGLE_CREDENTIALS_PATH не найдены в переменных окружения")
        return None
    
    # Создаем экземпляр, если еще не создан
    if sheets_manager is None:
        try:
            sheets_manager = SheetsManager(
                spreadsheet_key=spreadsheet_key,
                credentials_path=credentials_path
            )
            logger.info("SheetsManager успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка при инициализации SheetsManager: {e}")
            return None
    
    return sheets_manager


def get_sheets_manager():
    """
    Возвращает глобальный экземпляр SheetsManager, при необходимости инициализируя его.
    
    Returns:
        Экземпляр SheetsManager или None, если инициализация не удалась
    """
    global sheets_manager
    
    if sheets_manager is None:
        sheets_manager = init_sheets_manager()
    
    return sheets_manager


if __name__ == "__main__":
    # Тестирование функциональности
    manager = init_sheets_manager()
    
    if manager and manager.health_check():
        print("Подключение к Google Sheets успешно!")
        
        # Пример создания пользователя
        user = manager.create_user(
            telegram_id=123456789,
            username="test_user",
            first_name="Test",
            last_name="User"
        )
        
        if user:
            print(f"Создан пользователь: {user}")
            
            # Пример создания сессии
            session = manager.create_session(
                user_id=user["id"],
                language_level="B2",
                session_data={"topic": "travel"}
            )
            
            if session:
                print(f"Создана сессия: {session}")
                
                # Пример добавления сообщений
                manager.add_message(session["id"], "user", "Hello, I want to practice English")
                manager.add_message(session["id"], "assistant", "Hi there! What would you like to talk about?")
                
                # Получаем сообщения сессии
                messages = manager.get_session_messages(session["id"])
                print(f"Сообщения сессии: {messages}")
                
                # Пример добавления обратной связи
                feedback = manager.add_feedback(
                    user_id=user["id"],
                    session_id=session["id"],
                    rating=5,
                    comment="Great conversation!"
                )
                
                if feedback:
                    print(f"Добавлена обратная связь: {feedback}")
    else:
        print("Не удалось подключиться к Google Sheets")