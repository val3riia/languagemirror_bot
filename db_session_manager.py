import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from flask import Flask
from models import db, User, Session, Message

class DatabaseSessionManager:
    """
    Enhanced session manager for Language Mirror bot that uses database storage.
    This implementation persists sessions and messages in a PostgreSQL database.
    Can be used as a drop-in replacement for the in-memory SessionManager.
    """
    
    def __init__(self, app: Optional[Flask] = None, session_timeout: int = 1800):
        """
        Initialize the database session manager.
        
        Args:
            app: Flask application instance (optional)
            session_timeout: Session timeout in seconds (default 30 minutes)
        """
        self.app = app
        self.session_timeout = session_timeout
        self.in_memory_sessions = {}  # For fallback when DB not available
        
        # If app is provided, set it up right away
        if app is not None and app.config.get("SQLALCHEMY_DATABASE_URI"):
            self.with_database = True
        else:
            self.with_database = False
    
    def create_session(self, user_id: int, initial_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Create a new session for a user.
        
        Args:
            user_id: Telegram user ID
            initial_data: Initial session data (may include language_level, etc)
        """
        # Always maintain in-memory fallback
        self.in_memory_sessions[user_id] = {
            "created_at": time.time(),
            "last_updated": time.time(),
            "messages": [],
            **(initial_data or {})
        }
        
        # If database is available, create a session there as well
        if self.with_database:
            try:
                # Find or create the user
                telegram_user = User.query.filter_by(telegram_id=user_id).first()
                if not telegram_user:
                    telegram_user = User(
                        telegram_id=user_id,
                        username=initial_data.get("username") if initial_data else None,
                        first_name=initial_data.get("first_name") if initial_data else None,
                        last_name=initial_data.get("last_name") if initial_data else None,
                        language_level=initial_data.get("language_level") if initial_data else None
                    )
                    db.session.add(telegram_user)
                    db.session.commit()
                
                # Update user's language level if provided
                if initial_data and "language_level" in initial_data:
                    telegram_user.language_level = initial_data["language_level"]
                    db.session.commit()
                
                # Create a new db session
                db_session = Session(
                    user_id=telegram_user.id,
                    started_at=datetime.utcnow(),
                    is_active=True
                )
                db.session.add(db_session)
                db.session.commit()
                
                # Store the session ID in memory for reference
                self.in_memory_sessions[user_id]["db_session_id"] = db_session.id
                
            except Exception as e:
                print(f"Error creating database session: {e}")
    
    def get_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a user's session if it exists and hasn't expired.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Session data or None if not found/expired
        """
        # Always check in-memory data first
        in_memory_session = self.in_memory_sessions.get(user_id)
        
        if not in_memory_session:
            return None
        
        # Check if session has expired
        if time.time() - in_memory_session["last_updated"] > self.session_timeout:
            self.end_session(user_id)
            return None
        
        # Update last activity timestamp in memory
        in_memory_session["last_updated"] = time.time()
        
        # Update database if available
        if self.with_database and "db_session_id" in in_memory_session:
            try:
                # Update session last activity in database
                db_session = Session.query.get(in_memory_session["db_session_id"])
                if db_session and db_session.is_active:
                    db_session.last_activity = datetime.utcnow()
                    db.session.commit()
            except Exception as e:
                print(f"Error updating session activity: {e}")
        
        return in_memory_session
    
    def update_session(self, user_id: int, data: Dict[str, Any]) -> None:
        """
        Update a user's session with new data.
        
        Args:
            user_id: Telegram user ID
            data: New session data to merge
        """
        session = self.get_session(user_id)
        if session:
            # Update in-memory data
            session.update(data)
            session["last_updated"] = time.time()
            
            # Update database if appropriate and possible
            if self.with_database and "language_level" in data:
                try:
                    # Update user language level
                    telegram_user = User.query.filter_by(telegram_id=user_id).first()
                    if telegram_user:
                        telegram_user.language_level = data["language_level"]
                        db.session.commit()
                except Exception as e:
                    print(f"Error updating user data: {e}")
    
    def end_session(self, user_id: int) -> None:
        """
        End a user's session.
        
        Args:
            user_id: Telegram user ID
        """
        # Check in-memory storage
        if user_id in self.in_memory_sessions:
            session = self.in_memory_sessions[user_id]
            
            # Update database if available
            if self.with_database and "db_session_id" in session:
                try:
                    # Mark session as inactive in database
                    db_session = Session.query.get(session["db_session_id"])
                    if db_session:
                        db_session.is_active = False
                        db_session.ended_at = datetime.utcnow()
                        db_session.messages_count = len(session.get("messages", []))
                        db.session.commit()
                except Exception as e:
                    print(f"Error ending database session: {e}")
            
            # Remove from in-memory storage
            del self.in_memory_sessions[user_id]
    
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
            # Add to in-memory storage
            if "messages" not in session:
                session["messages"] = []
            
            session["messages"].append({
                "role": role,
                "content": content,
                "timestamp": time.time()
            })
            session["last_updated"] = time.time()
            
            # Add to database if available
            if self.with_database and "db_session_id" in session:
                try:
                    # Create new message in database
                    message = Message(
                        session_id=session["db_session_id"],
                        role=role,
                        content=content
                    )
                    db.session.add(message)
                    db.session.commit()
                except Exception as e:
                    print(f"Error adding message to database: {e}")
    
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
        """Clean up expired sessions in memory and database."""
        current_time = time.time()
        expired_user_ids = [
            user_id for user_id, session in self.in_memory_sessions.items()
            if current_time - session["last_updated"] > self.session_timeout
        ]
        
        for user_id in expired_user_ids:
            self.end_session(user_id)
        
        # No need to clean up database sessions separately as they're marked inactive when ended