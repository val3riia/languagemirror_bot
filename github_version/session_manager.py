import time
import logging
from typing import Dict, List, Any, Optional

# Настройка логирования
logger = logging.getLogger(__name__)

class SessionManager:
    """
    Manages user sessions for the Language Mirror bot.
    This is an in-memory implementation that only keeps session data
    during active dialogues.
    """
    
    def __init__(self, session_timeout: int = 1800):
        """
        Initialize the session manager.
        
        Args:
            session_timeout: Session timeout in seconds (default 30 minutes)
        """
        self.sessions: Dict[int, Dict[str, Any]] = {}
        self.session_timeout = session_timeout
        logger.info(f"Session manager initialized with timeout: {session_timeout} seconds")
    
    def create_session(self, user_id: int, initial_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Create a new session for a user.
        
        Args:
            user_id: Telegram user ID
            initial_data: Initial session data
        """
        self.sessions[user_id] = {
            "created_at": time.time(),
            "last_updated": time.time(),
            "messages": [],
            **(initial_data or {})
        }
        logger.debug(f"Created session for user {user_id}")
    
    def get_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a user's session if it exists and hasn't expired.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Session data or None if not found/expired
        """
        session = self.sessions.get(user_id)
        
        if not session:
            return None
        
        # Check if session has expired
        if time.time() - session["last_updated"] > self.session_timeout:
            logger.debug(f"Session for user {user_id} has expired")
            self.end_session(user_id)
            return None
        
        # Update last activity timestamp
        session["last_updated"] = time.time()
        return session
    
    def update_session(self, user_id: int, data: Dict[str, Any]) -> None:
        """
        Update a user's session with new data.
        
        Args:
            user_id: Telegram user ID
            data: New session data to merge
        """
        session = self.get_session(user_id)
        if session:
            session.update(data)
            session["last_updated"] = time.time()
            logger.debug(f"Updated session for user {user_id}")
    
    def end_session(self, user_id: int) -> None:
        """
        End a user's session.
        
        Args:
            user_id: Telegram user ID
        """
        if user_id in self.sessions:
            del self.sessions[user_id]
            logger.debug(f"Ended session for user {user_id}")
    
    def add_message_to_session(self, user_id: int, role: str, content: str) -> None:
        """
        Add a message to the session conversation history.
        
        Args:
            user_id: Telegram user ID
            role: Message role ('user' or 'assistant')
            content: Message content
        """
        session = self.get_session(user_id)
        if session:
            if "messages" not in session:
                session["messages"] = []
            
            session["messages"].append({
                "role": role,
                "content": content,
                "timestamp": time.time()
            })
            session["last_updated"] = time.time()
            logger.debug(f"Added {role} message to session for user {user_id}")
    
    def get_messages(self, user_id: int) -> List[Dict[str, str]]:
        """
        Get all messages in the current session formatted for the AI model.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            List of message dictionaries
        """
        session = self.get_session(user_id)
        if not session or "messages" not in session:
            return []
        
        # Format messages for the AI model (only role and content)
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in session["messages"]
        ]
    
    def clean_expired_sessions(self) -> None:
        """Clean up expired sessions."""
        current_time = time.time()
        expired_user_ids = [
            user_id for user_id, session in self.sessions.items()
            if current_time - session["last_updated"] > self.session_timeout
        ]
        
        for user_id in expired_user_ids:
            self.end_session(user_id)
        
        if expired_user_ids:
            logger.debug(f"Cleaned up {len(expired_user_ids)} expired sessions")