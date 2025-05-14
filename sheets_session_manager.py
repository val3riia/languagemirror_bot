"""
Менеджер сессий на основе Google Sheets для Language Mirror бота.
Эта реализация заменяет DatabaseSessionManager и использует Google Sheets вместо PostgreSQL.
"""
import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from sheets_manager import SheetsManager

# Настройка логирования
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class SheetSessionManager:
    """
    Менеджер сессий на основе Google Sheets для Language Mirror бота.
    Используется как замена для DatabaseSessionManager.
    """
    
    def __init__(self, sheets_manager: Optional[SheetsManager] = None, session_timeout: int = 1800):
        """
        Инициализирует менеджер сессий на основе Google Sheets.
        
        Args:
            sheets_manager: Менеджер для работы с Google Sheets
            session_timeout: Таймаут сессии в секундах (по умолчанию 30 минут)
        """
        self.sheets_manager = sheets_manager or SheetsManager()
        self.session_timeout = session_timeout
        self.in_memory_sessions = {}  # Для резервного хранения в памяти
    
    def create_session(self, user_id: int, initial_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Создает новую сессию для пользователя.
        
        Args:
            user_id: Telegram ID пользователя
            initial_data: Начальные данные сессии (может включать language_level и др.)
        """
        try:
            # Всегда поддерживаем копию в памяти для резервного использования
            self.in_memory_sessions[user_id] = {
                "created_at": time.time(),
                "last_updated": time.time(),
                "messages": [],
                **(initial_data or {})
            }
            
            # Извлекаем данные пользователя из initial_data
            username = initial_data.get("username") if initial_data else None
            first_name = initial_data.get("first_name") if initial_data else None
            last_name = initial_data.get("last_name") if initial_data else None
            
            # Получаем или создаем пользователя
            user_data = self.sheets_manager.get_or_create_user(
                telegram_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            
            # Обновляем уровень языка, если он указан
            if initial_data and "language_level" in initial_data:
                self.sheets_manager.update_language_level(user_id, initial_data["language_level"])
            
            # Создаем сессию
            session_data = self.sheets_manager.create_session(user_id)
            
            # Сохраняем ID сессии в памяти
            self.in_memory_sessions[user_id]["sheet_session_id"] = session_data["id"]
            
            logger.info(f"Создана новая сессия для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при создании сессии для пользователя {user_id}: {e}")
    
    def get_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает сессию пользователя, если она существует и не истекла.
        
        Args:
            user_id: Telegram ID пользователя
            
        Returns:
            Данные сессии или None, если сессия не найдена/истекла
        """
        # Сначала проверяем данные в памяти
        in_memory_session = self.in_memory_sessions.get(user_id)
        
        if not in_memory_session:
            return None
        
        # Проверяем, не истекла ли сессия
        if time.time() - in_memory_session["last_updated"] > self.session_timeout:
            self.end_session(user_id)
            return None
        
        # Обновляем последнее время активности в памяти
        in_memory_session["last_updated"] = time.time()
        
        # Проверяем, есть ли активная сессия в таблице
        active_session = self.sheets_manager.get_active_session(user_id)
        
        # Если нет активной сессии в таблице, но есть в памяти, повторно создаем
        if not active_session and "sheet_session_id" in in_memory_session:
            # Создаем новую сессию в таблице
            session_data = self.sheets_manager.create_session(user_id)
            # Обновляем ID сессии в памяти
            in_memory_session["sheet_session_id"] = session_data["id"]
        
        return in_memory_session
    
    def update_session(self, user_id: int, data: Dict[str, Any]) -> None:
        """
        Обновляет сессию пользователя новыми данными.
        
        Args:
            user_id: Telegram ID пользователя
            data: Новые данные сессии для объединения
        """
        session = self.get_session(user_id)
        if session:
            # Обновляем данные в памяти
            session.update(data)
            session["last_updated"] = time.time()
            
            # Обновляем уровень языка, если он указан
            if "language_level" in data:
                self.sheets_manager.update_language_level(user_id, data["language_level"])
    
    def end_session(self, user_id: int) -> None:
        """
        Завершает сессию пользователя.
        
        Args:
            user_id: Telegram ID пользователя
        """
        # Проверяем хранилище в памяти
        if user_id in self.in_memory_sessions:
            session = self.in_memory_sessions[user_id]
            
            # Завершаем сессию в таблице
            self.sheets_manager.end_session(user_id)
            
            # Удаляем из памяти
            del self.in_memory_sessions[user_id]
            
            logger.info(f"Завершена сессия пользователя {user_id}")
    
    def add_message_to_session(self, user_id: int, role: str, content: str) -> None:
        """
        Добавляет сообщение в историю разговора сессии.
        
        Args:
            user_id: Telegram ID пользователя
            role: Роль сообщения ('user' или 'assistant')
            content: Содержимое сообщения
        """
        session = self.get_session(user_id)
        if session:
            # Добавляем в память
            if "messages" not in session:
                session["messages"] = []
            
            session["messages"].append({
                "role": role,
                "content": content,
                "timestamp": time.time()
            })
            session["last_updated"] = time.time()
            
            # Добавляем в таблицу
            self.sheets_manager.add_message(user_id, role, content)
    
    def get_messages(self, user_id: int) -> List[Dict[str, str]]:
        """
        Получает все сообщения в текущей сессии отформатированные для модели ИИ.
        
        Args:
            user_id: Telegram ID пользователя
            
        Returns:
            Список словарей сообщений
        """
        session = self.get_session(user_id)
        if not session or "messages" not in session:
            return []
        
        # Форматируем сообщения для модели ИИ (только роль и содержимое)
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in session["messages"]
        ]
    
    def clean_expired_sessions(self) -> None:
        """Очищает истекшие сессии в памяти."""
        current_time = time.time()
        expired_user_ids = [
            user_id for user_id, session in self.in_memory_sessions.items()
            if current_time - session["last_updated"] > self.session_timeout
        ]
        
        for user_id in expired_user_ids:
            self.end_session(user_id)