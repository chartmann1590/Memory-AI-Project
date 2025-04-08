# app/models.py

from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=True)  # Local users provide a username; SSO users may leave this null
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=True)  # May be null for SSO-only users

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'
    
class Recording(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    transcript = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, nullable=False)
    # New field for speaker tags, stored as a JSON string; keys can be line numbers
    speaker_tags = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Recording {self.id} at {self.timestamp}>"

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    archived = db.Column(db.Boolean, default=False)  # New field to mark archived tasks
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Todo {self.id} - {self.description}>"

# Association table for ChatSession <-> Recording
chat_session_recording = db.Table(
    'chat_session_recording',
    db.Column('chat_session_id', db.Integer, db.ForeignKey('chat_session.id'), primary_key=True),
    db.Column('recording_id', db.Integer, db.ForeignKey('recording.id'), primary_key=True)
)

class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Add the relationship to Recording
    recordings = db.relationship('Recording', secondary=chat_session_recording, backref='chat_sessions')

    def __repr__(self):
        return f"<ChatSession {self.id} - {self.title}>"

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'system', 'assistant', 'user'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to parent session
    session = db.relationship('ChatSession', backref='messages')

    def __repr__(self):
        return f"<ChatMessage {self.id} in Session {self.session_id}>"