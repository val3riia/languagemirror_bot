import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sheets_manager import get_sheets_manager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SheetSessionManager:
    """
    Менеджер сессий, использующий Google Sheets для хранения данных.
    Используется для управления сессиями пользователей и сохранения истории сообщений.
    Может быть использован как замена в памяти SessionManager.
    """

    def __init__(self, sheets_mgr=None, session_timeout: int = 1800):
        """
        Инициализация менеджера сессий.
        
        Args:
            sheets_mgr: Экземпляр SheetsManager для работы с Google Sheets
            session_timeout: Таймаут сессии в секундах (по умолчанию 30 минут)
        """
        self.session_timeout = session_timeout
        
        # Используем уже существующий экземпляр или создаем новый
        if sheets_mgr is not None:
            self.sheets_manager = sheets_mgr
        else:
            self.sheets_manager = get_sheets_manager()
        
        # Проверяем доступность Google Sheets
        if not self.sheets_manager or not self.sheets_manager.spreadsheet:
            logger.warning("Google Sheets недоступен, использую локальное хранилище")
            # Резервное хранилище в памяти
            self.in_memory_sessions = {}
            self.use_sheets = False
        else:
            self.in_memory_sessions = None
            self.use_sheets = True
            logger.info("SheetSessionManager использует Google Sheets для хранения")
            
    def update_user_info(self, user_id: int, user_data: Dict[str, Any]) -> bool:
        """
        Обновляет информацию о пользователе в Google Sheets.
        
        Args:
            user_id: ID пользователя в Telegram
            user_data: Данные пользователя для обновления
            
        Returns:
            True при успешном обновлении, False при ошибке
        """
        try:
            if not self.use_sheets or not self.sheets_manager:
                logger.warning("Google Sheets недоступен для обновления информации о пользователе")
                return False
                
            # Получаем пользователя по telegram_id
            user = self.sheets_manager.get_user_by_telegram_id(user_id)
            
            if user:
                # Обновляем данные существующего пользователя
                result = self.sheets_manager.update_user(user['id'], user_data)
                if result:
                    logger.info(f"Информация о пользователе обновлена: {user_id}")
                    return True
                else:
                    logger.warning(f"Не удалось обновить информацию о пользователе: {user_id}")
                    return False
            else:
                # Создаем нового пользователя
                new_user = self.sheets_manager.add_user(
                    telegram_id=str(user_id),
                    username=user_data.get('username', ''),
                    first_name=user_data.get('first_name', ''),
                    last_name=user_data.get('last_name', '')
                )
                
                if new_user:
                    logger.info(f"Создан новый пользователь: {user_id}")
                    return True
                else:
                    logger.warning(f"Не удалось создать пользователя: {user_id}")
                    return False
        except Exception as e:
            logger.error(f"Ошибка при обновлении информации о пользователе: {e}")
            return False
            
    def set_feedback_bonus(self, user_id: int, used: bool = False) -> bool:
        """
        Устанавливает статус бонусного запроса для пользователя.
        
        Args:
            user_id: ID пользователя в Telegram
            used: True если бонус использован, False если доступен для использования
            
        Returns:
            True при успешном обновлении, False при ошибке
        """
        try:
            if not self.use_sheets or not self.sheets_manager:
                logger.warning("Google Sheets недоступен для установки бонуса")
                return False
                
            # Получаем пользователя по telegram_id
            user = self.sheets_manager.get_user_by_telegram_id(user_id)
            
            if not user:
                logger.warning(f"Пользователь не найден для установки бонуса: {user_id}")
                return False
                
            # Получаем активную сессию для пользователя
            active_session = self.sheets_manager.get_active_session_for_user(user['id'])
            
            if active_session:
                # Обновляем данные сессии
                session_data = {
                    'has_feedback_bonus': True,
                    'feedback_bonus_used': used
                }
                
                result = self.sheets_manager.update_session(active_session['id'], session_data)
                if result:
                    logger.info(f"Бонус обратной связи установлен для пользователя {user_id}: использован={used}")
                    return True
            
            # Если нет активной сессии, обновляем данные пользователя
            user_data = {
                'has_feedback_bonus': True,
                'feedback_bonus_used': used
            }
            
            result = self.sheets_manager.update_user(user['id'], user_data)
            if result:
                logger.info(f"Бонус обратной связи установлен через данные пользователя {user_id}: использован={used}")
                return True
                
            logger.warning(f"Не удалось установить бонус обратной связи для пользователя: {user_id}")
            return False
        except Exception as e:
            logger.error(f"Ошибка при установке бонуса обратной связи: {e}")
            return False

    def create_session(self, user_id: int, initial_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Создает новую сессию для пользователя.
        
        Args:
            user_id: ID пользователя в Telegram
            initial_data: Начальные данные сессии (может включать language_level и т.д.)
        """
        if self.use_sheets:
            try:
                # Проверяем, существует ли пользователь
                user = self.sheets_manager.get_user_by_telegram_id(user_id)
                
                if not user:
                    # Создаем нового пользователя
                    user = self.sheets_manager.create_user(telegram_id=user_id)
                    if not user:
                        raise Exception(f"Не удалось создать пользователя с ID {user_id}")
                
                # Получаем активную сессию
                active_session = self.sheets_manager.get_active_session(user["id"])
                
                # Если есть активная сессия, завершаем её
                if active_session:
                    self.sheets_manager.end_session(active_session["id"])
                
                # Извлекаем language_level, если есть
                language_level = None
                if initial_data and "language_level" in initial_data:
                    language_level = initial_data.get("language_level")
                
                # Создаем новую сессию
                self.sheets_manager.create_session(
                    user_id=user["id"],
                    language_level=language_level,
                    session_data=initial_data
                )
            except Exception as e:
                logger.error(f"Ошибка при создании сессии в Google Sheets: {e}")
                # Fallback to in-memory
                self._init_memory_storage()
                self.in_memory_sessions[user_id] = {
                    "created_at": datetime.now(),
                    "updated_at": datetime.now(),
                    "data": initial_data or {},
                    "messages": []
                }
        else:
            # Используем хранилище в памяти
            self.in_memory_sessions[user_id] = {
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "data": initial_data or {},
                "messages": []
            }

    def get_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает сессию пользователя, если она существует и не истекла.
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            Данные сессии или None, если не найдена/истекла
        """
        if self.use_sheets:
            try:
                # Получаем пользователя
                user = self.sheets_manager.get_user_by_telegram_id(user_id)
                if not user:
                    return None
                
                # Получаем активную сессию
                session = self.sheets_manager.get_active_session(user["id"])
                if not session:
                    return None
                
                # Проверяем таймаут сессии
                updated_at = session.get("updated_at")
                if updated_at:
                    try:
                        updated_time = datetime.fromisoformat(updated_at)
                        if datetime.now() - updated_time > timedelta(seconds=self.session_timeout):
                            # Сессия истекла, завершаем её
                            self.sheets_manager.end_session(session["id"])
                            return None
                    except (ValueError, TypeError):
                        pass  # Ошибка парсинга даты, игнорируем
                
                # Возвращаем данные сессии
                return session.get("data", {})
            except Exception as e:
                logger.error(f"Ошибка при получении сессии из Google Sheets: {e}")
                # Fallback to in-memory
                self._init_memory_storage()
                return self._get_memory_session(user_id)
        else:
            # Используем хранилище в памяти
            return self._get_memory_session(user_id)

    def _get_memory_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает сессию из хранилища в памяти.
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            Данные сессии или None, если не найдена/истекла
        """
        session = self.in_memory_sessions.get(user_id)
        if not session:
            return None
            
        # Проверяем таймаут сессии
        updated_at = session.get("updated_at")
        if updated_at and datetime.now() - updated_at > timedelta(seconds=self.session_timeout):
            # Сессия истекла, удаляем её
            del self.in_memory_sessions[user_id]
            return None
            
        return session.get("data", {})

    def update_session(self, user_id: int, data: Dict[str, Any]) -> None:
        """
        Обновляет данные сессии пользователя.
        
        Args:
            user_id: ID пользователя в Telegram
            data: Новые данные сессии для слияния
        """
        if self.use_sheets:
            try:
                # Получаем пользователя
                user = self.sheets_manager.get_user_by_telegram_id(user_id)
                if not user:
                    return
                
                # Получаем активную сессию
                session = self.sheets_manager.get_active_session(user["id"])
                if not session:
                    return
                
                # Обновляем данные сессии
                current_data = session.get("data", {})
                if isinstance(current_data, str):
                    try:
                        current_data = json.loads(current_data)
                    except json.JSONDecodeError:
                        current_data = {}
                
                # Объединяем текущие данные с новыми
                merged_data = {**current_data, **data}
                
                # Обновляем сессию
                self.sheets_manager.update_session(
                    session_id=session["id"],
                    data={
                        "data": merged_data,
                        "updated_at": datetime.now().isoformat()
                    }
                )
            except Exception as e:
                logger.error(f"Ошибка при обновлении сессии в Google Sheets: {e}")
                # Fallback to in-memory
                self._init_memory_storage()
                self._update_memory_session(user_id, data)
        else:
            # Используем хранилище в памяти
            self._update_memory_session(user_id, data)

    def _update_memory_session(self, user_id: int, data: Dict[str, Any]) -> None:
        """
        Обновляет сессию в хранилище в памяти.
        
        Args:
            user_id: ID пользователя в Telegram
            data: Новые данные сессии для слияния
        """
        session = self.in_memory_sessions.get(user_id)
        if not session:
            # Если сессии нет, создаем новую
            self.in_memory_sessions[user_id] = {
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "data": data,
                "messages": []
            }
        else:
            # Обновляем существующую сессию
            session["updated_at"] = datetime.now()
            session["data"].update(data)

    def end_session(self, user_id: int) -> None:
        """
        Завершает сессию пользователя.
        
        Args:
            user_id: ID пользователя в Telegram
        """
        if self.use_sheets:
            try:
                # Получаем пользователя
                user = self.sheets_manager.get_user_by_telegram_id(user_id)
                if not user:
                    return
                
                # Получаем активную сессию
                session = self.sheets_manager.get_active_session(user["id"])
                if not session:
                    return
                
                # Завершаем сессию
                self.sheets_manager.end_session(session["id"])
            except Exception as e:
                logger.error(f"Ошибка при завершении сессии в Google Sheets: {e}")
                # Fallback to in-memory
                self._init_memory_storage()
                if user_id in self.in_memory_sessions:
                    del self.in_memory_sessions[user_id]
        else:
            # Используем хранилище в памяти
            if user_id in self.in_memory_sessions:
                del self.in_memory_sessions[user_id]

    def add_message_to_session(self, user_id: int, role: str, content: str) -> None:
        """
        Добавляет сообщение в историю сессии.
        
        Args:
            user_id: ID пользователя в Telegram
            role: Роль отправителя ('user' или 'assistant')
            content: Содержание сообщения
        """
        if self.use_sheets:
            try:
                # Получаем пользователя
                user = self.sheets_manager.get_user_by_telegram_id(user_id)
                if not user:
                    return
                
                # Получаем активную сессию
                session = self.sheets_manager.get_active_session(user["id"])
                if not session:
                    return
                
                # Добавляем сообщение
                self.sheets_manager.add_message(
                    session_id=session["id"],
                    role=role,
                    content=content
                )
                
                # Обновляем время последнего обновления сессии
                self.sheets_manager.update_session(
                    session_id=session["id"],
                    data={"updated_at": datetime.now().isoformat()}
                )
            except Exception as e:
                logger.error(f"Ошибка при добавлении сообщения в Google Sheets: {e}")
                # Fallback to in-memory
                self._init_memory_storage()
                self._add_message_to_memory_session(user_id, role, content)
        else:
            # Используем хранилище в памяти
            self._add_message_to_memory_session(user_id, role, content)

    def _add_message_to_memory_session(self, user_id: int, role: str, content: str) -> None:
        """
        Добавляет сообщение в хранилище в памяти.
        
        Args:
            user_id: ID пользователя в Telegram
            role: Роль отправителя ('user' или 'assistant')
            content: Содержание сообщения
        """
        session = self.in_memory_sessions.get(user_id)
        if not session:
            # Если сессии нет, создаем новую
            self.in_memory_sessions[user_id] = {
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "data": {},
                "messages": [{"role": role, "content": content}]
            }
        else:
            # Добавляем сообщение к существующей сессии
            session["updated_at"] = datetime.now()
            if "messages" not in session:
                session["messages"] = []
            session["messages"].append({"role": role, "content": content})

    def get_messages(self, user_id: int) -> List[Dict[str, str]]:
        """
        Получает все сообщения текущей сессии в формате для модели AI.
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            Список словарей с сообщениями
        """
        if self.use_sheets:
            try:
                # Получаем пользователя
                user = self.sheets_manager.get_user_by_telegram_id(user_id)
                if not user:
                    return []
                
                # Получаем активную сессию
                session = self.sheets_manager.get_active_session(user["id"])
                if not session:
                    return []
                
                # Получаем сообщения сессии
                messages = self.sheets_manager.get_session_messages(session["id"])
                
                # Преобразуем в формат для модели AI
                formatted_messages = [
                    {"role": msg.get("role", ""), "content": msg.get("content", "")}
                    for msg in messages
                ]
                
                return formatted_messages
            except Exception as e:
                logger.error(f"Ошибка при получении сообщений из Google Sheets: {e}")
                # Fallback to in-memory
                self._init_memory_storage()
                return self._get_memory_messages(user_id)
        else:
            # Используем хранилище в памяти
            return self._get_memory_messages(user_id)

    def _get_memory_messages(self, user_id: int) -> List[Dict[str, str]]:
        """
        Получает сообщения из хранилища в памяти.
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            Список словарей с сообщениями
        """
        session = self.in_memory_sessions.get(user_id)
        if not session or "messages" not in session:
            return []
        return session["messages"]

    def clean_expired_sessions(self) -> None:
        """Очищает истекшие сессии в памяти и в базе данных."""
        if self.use_sheets:
            # Google Sheets не требует очистки, мы просто помечаем сессии как неактивные
            pass
        else:
            # Очищаем истекшие сессии в памяти
            current_time = datetime.now()
            expired_user_ids = []
            
            for user_id, session in self.in_memory_sessions.items():
                updated_at = session.get("updated_at")
                if updated_at and current_time - updated_at > timedelta(seconds=self.session_timeout):
                    expired_user_ids.append(user_id)
            
            for user_id in expired_user_ids:
                del self.in_memory_sessions[user_id]

    def _init_memory_storage(self) -> None:
        """Инициализирует хранилище в памяти, если оно еще не существует."""
        if self.in_memory_sessions is None:
            self.in_memory_sessions = {}
            self.use_sheets = False

    def add_feedback(self, user_id: int, rating: int, comment: Optional[str] = None) -> bool:
        """
        Добавляет обратную связь от пользователя.
        
        Args:
            user_id: ID пользователя в Telegram
            rating: Оценка (1-5)
            comment: Комментарий пользователя
            
        Returns:
            True при успешном добавлении, False при ошибке
        """
        if self.use_sheets:
            try:
                # Получаем пользователя
                user = self.sheets_manager.get_user_by_telegram_id(user_id)
                if not user:
                    return False
                
                # Получаем активную сессию
                session = self.sheets_manager.get_active_session(user["id"])
                session_id = session["id"] if session else None
                
                # Добавляем обратную связь
                feedback = self.sheets_manager.add_feedback(
                    user_id=user["id"],
                    rating=rating,
                    comment=comment,
                    session_id=session_id
                )
                
                return feedback is not None
            except Exception as e:
                logger.error(f"Ошибка при добавлении обратной связи в Google Sheets: {e}")
                return False
        else:
            # В версии в памяти обратная связь не сохраняется
            logger.warning("Обратная связь не сохранена: используется хранилище в памяти")
            return False

    def health_check(self) -> Dict[str, bool]:
        """
        Проверяет доступность хранилища.
        
        Returns:
            Словарь с состоянием компонентов
        """
        status = {
            "sheets_available": False,
            "memory_fallback": self.in_memory_sessions is not None
        }
        
        if self.sheets_manager:
            status["sheets_available"] = self.sheets_manager.health_check()
            
        return status


# Глобальный экземпляр менеджера сессий
session_manager = None


def get_session_manager(session_timeout: int = 1800):
    """
    Возвращает глобальный экземпляр SheetSessionManager, при необходимости инициализируя его.
    
    Args:
        session_timeout: Таймаут сессии в секундах (по умолчанию 30 минут)
        
    Returns:
        Экземпляр SheetSessionManager
    """
    global session_manager
    
    if session_manager is None:
        session_manager = SheetSessionManager(session_timeout=session_timeout)
        
    return session_manager


if __name__ == "__main__":
    # Тестирование функциональности
    manager = get_session_manager()
    
    # Создаем сессию для пользователя
    user_id = 123456789
    manager.create_session(user_id, {"language_level": "B2"})
    
    # Добавляем сообщения
    manager.add_message_to_session(user_id, "user", "Hello, I want to practice English")
    manager.add_message_to_session(user_id, "assistant", "Hi there! What would you like to talk about?")
    
    # Получаем сообщения
    messages = manager.get_messages(user_id)
    print(f"Сообщения: {messages}")
    
    # Обновляем данные сессии
    manager.update_session(user_id, {"topic": "travel"})
    
    # Получаем сессию
    session = manager.get_session(user_id)
    print(f"Сессия: {session}")
    
    # Проверяем состояние хранилища
    status = manager.health_check()
    print(f"Статус хранилища: {status}")
    
    # Завершаем сессию
    manager.end_session(user_id)
    
    # Проверяем, что сессия завершена
    session = manager.get_session(user_id)
    print(f"Сессия после завершения: {session}")  # Должно быть None