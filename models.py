from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON

# Инициализация SQLAlchemy извне (в main.py)
db = SQLAlchemy()

class User(db.Model):
    """Модель пользователя Telegram-бота"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=False)
    username = db.Column(db.String(255), nullable=True)
    first_name = db.Column(db.String(255), nullable=True)
    last_name = db.Column(db.String(255), nullable=True)
    language_level = db.Column(db.String(10), nullable=True)  # A1, A2, B1, B2, C1, C2
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_discussion_date = db.Column(db.Date, nullable=True)  # Дата последнего запроса /discussion
    discussions_count = db.Column(db.Integer, default=0)  # Количество использований /discussion
    feedback_bonus_used = db.Column(db.Boolean, default=False)  # Получал ли уже бонус за фидбек
    
    sessions = db.relationship('Session', back_populates='user', cascade='all, delete-orphan')
    feedback = db.relationship('Feedback', back_populates='user', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.telegram_id} ({self.username or "No username"})>'

class Session(db.Model):
    """Модель сессии обучения"""
    __tablename__ = 'sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)
    messages_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    user = db.relationship('User', back_populates='sessions')
    messages = db.relationship('Message', back_populates='session', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Session {self.id} for User {self.user_id}>'

class Message(db.Model):
    """Модель сообщений в сессии"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    corrections = db.Column(JSON, nullable=True)  # JSON объект с исправлениями
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    session = db.relationship('Session', back_populates='messages')
    
    def __repr__(self):
        return f'<Message {self.id} ({self.role}) for Session {self.session_id}>'

class Feedback(db.Model):
    """Модель обратной связи"""
    __tablename__ = 'feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=True)
    rating = db.Column(db.String(50), nullable=False)  # 'helpful', 'okay', 'not_helpful'
    comment = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', back_populates='feedback')
    
    def __repr__(self):
        return f'<Feedback {self.id} ({self.rating}) from User {self.user_id}>'