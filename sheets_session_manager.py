"""
Менеджер сессий на основе Google Sheets для Language Mirror бота.
Эта реализация заменяет DatabaseSessionManager и использует Google Sheets вместо PostgreSQL.
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from sheets_manager import SheetsManager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        self.sheets_manager = sheets_manager
        self.session_timeout = session_timeout
        logger.info(f"SheetSessionManager initialized with timeout {session_timeout} seconds")
    
    def create_session(self, user_id: int, initial_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Создает новую сессию для пользователя.
        
        Args:
            user_id: Telegram ID пользователя
            initial_data: Начальные данные сессии (может включать language_level и др.)
        """
        if not self.sheets_manager:
            logger.warning(f"Cannot create session for user {user_id}: sheets_manager not initialized")
            return
            
        # Получаем или создаем пользователя
        language_level = None
        topic = None
        
        if initial_data:
            language_level = initial_data.get("language_level")
            topic = initial_data.get("topic")
        
        # Создаем новую сессию
        self.sheets_manager.create_session(
            telegram_id=user_id,
            language_level=language_level,
            topic=topic
        )
        
        logger.info(f"Created new session for user {user_id}")
    
    def get_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает сессию пользователя, если она существует и не истекла.
        
        Args:
            user_id: Telegram ID пользователя
            
        Returns:
            Данные сессии или None, если сессия не найдена/истекла
        """
        if not self.sheets_manager:
            logger.warning(f"Cannot get session for user {user_id}: sheets_manager not initialized")
            return None
            
        # Получаем активную сессию
        session = self.sheets_manager.get_active_session(user_id)
        
        if not session:
            logger.info(f"No active session found for user {user_id}")
            return None
            
        # Проверяем, не истекла ли сессия
        if "last_active" in session:
            try:
                last_active_str = session["last_active"]
                last_active = datetime.fromisoformat(last_active_str)
                now = datetime.now()
                
                # Рассчитываем разницу во времени в секундах
                delta = (now - last_active).total_seconds()
                
                if delta > self.session_timeout:
                    logger.info(f"Session for user {user_id} expired ({delta} seconds old)")
                    self.end_session(user_id)
                    return None
            except Exception as e:
                logger.error(f"Error checking session timeout for user {user_id}: {e}")
        
        # Дополняем сессию данными из таблицы сообщений
        session["messages"] = self.get_messages(user_id)
        
        return session
    
    def update_session(self, user_id: int, data: Dict[str, Any]) -> None:
        """
        Обновляет сессию пользователя новыми данными.
        
        Args:
            user_id: Telegram ID пользователя
            data: Новые данные сессии для объединения
        """
        if not self.sheets_manager:
            logger.warning(f"Cannot update session for user {user_id}: sheets_manager not initialized")
            return
            
        # Получаем активную сессию
        session = self.sheets_manager.get_active_session(user_id)
        
        if not session:
            logger.info(f"No active session found for user {user_id} to update, creating new session")
            self.create_session(user_id, data)
            return
            
        # Обновляем данные сессии
        session_id = session.get("id")
        
        # Удаляем из данных поле messages, чтобы не сохранять его в основной таблице сессий
        updated_data = {k: v for k, v in data.items() if k != "messages"}
        
        self.sheets_manager.update_session(session_id, updated_data)
        logger.info(f"Updated session for user {user_id}")
    
    def end_session(self, user_id: int) -> None:
        """
        Завершает сессию пользователя.
        
        Args:
            user_id: Telegram ID пользователя
        """
        if not self.sheets_manager:
            logger.warning(f"Cannot end session for user {user_id}: sheets_manager not initialized")
            return
            
        # Получаем активную сессию
        session = self.sheets_manager.get_active_session(user_id)
        
        if not session:
            logger.info(f"No active session found for user {user_id} to end")
            return
            
        # Завершаем сессию
        session_id = session.get("id")
        self.sheets_manager.end_session(session_id)
        logger.info(f"Ended session for user {user_id}")
    
    def add_message_to_session(self, user_id: int, role: str, content: str) -> None:
        """
        Добавляет сообщение в историю разговора сессии.
        
        Args:
            user_id: Telegram ID пользователя
            role: Роль сообщения ('user' или 'assistant')
            content: Содержимое сообщения
        """
        if not self.sheets_manager:
            logger.warning(f"Cannot add message for user {user_id}: sheets_manager not initialized")
            return
            
        # Получаем активную сессию
        session = self.sheets_manager.get_active_session(user_id)
        
        if not session:
            logger.info(f"No active session found for user {user_id}, creating new session")
            self.create_session(user_id)
            session = self.sheets_manager.get_active_session(user_id)
            
            if not session:
                logger.error(f"Failed to create session for user {user_id}")
                return
        
        # Добавляем сообщение к сессии
        session_id = session.get("id")
        self.sheets_manager.add_message(
            telegram_id=user_id,
            role=role,
            content=content,
            session_id=session_id
        )
        
        logger.info(f"Added message from {role} to session for user {user_id}")
    
    def get_messages(self, user_id: int) -> List[Dict[str, str]]:
        """
        Получает все сообщения в текущей сессии отформатированные для модели ИИ.
        
        Args:
            user_id: Telegram ID пользователя
            
        Returns:
            Список словарей сообщений
        """
        if not self.sheets_manager:
            logger.warning(f"Cannot get messages for user {user_id}: sheets_manager not initialized")
            return []
            
        # Получаем активную сессию
        session = self.sheets_manager.get_active_session(user_id)
        
        if not session:
            logger.info(f"No active session found for user {user_id}")
            return []
            
        # Получаем сообщения сессии
        session_id = session.get("id")
        messages = self.sheets_manager.get_session_messages(session_id)
        
        return messages
    
    def clean_expired_sessions(self) -> None:
        """Очищает истекшие сессии в памяти."""
        # В данной реализации не требуется, так как сессии хранятся в Google Sheets
        logger.info("Clean expired sessions called (no action needed for Google Sheets implementation)")