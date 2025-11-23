import os
import bcrypt
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from typing import Optional, List

def _load_env_database_url() -> str:
    try:
        from dotenv import load_dotenv, find_dotenv
        env_path = find_dotenv()
        if env_path:
            load_dotenv(env_path)
    except Exception:
        pass
    return os.getenv("DATABASE_URL")

# Defer engine creation to allow graceful error handling
engine = None
SessionLocal = None
Base = declarative_base()

def init_db_connection():
    """Initialize database connection lazily"""
    global engine, SessionLocal
    if engine is not None:
        return True

    db_url = os.getenv("DATABASE_URL") or _load_env_database_url()
    if not db_url:
        print("WARNING: DATABASE_URL environment variable is not set. Using SQLite fallback.")
        # Fallback to SQLite for local development
        fallback_url = "sqlite:///./askdb_auth.sqlite3"
        try:
            engine = create_engine(fallback_url, pool_pre_ping=True)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            print(f"Using SQLite fallback: {fallback_url}")
            return True
        except Exception as e:
            print(f"ERROR: Failed to initialize SQLite fallback: {e}")
            return False
    
    try:
        # Handle PostgreSQL connection string with special characters
        db_url = db_url
        # For PostgreSQL, use psycopg2 connection args properly
        if db_url.startswith('postgresql://'):
            # For psycopg2, SSL mode should be in the URL, not connect_args
            # Remove channel_binding if present (not supported by all drivers)
            if 'channel_binding=require' in db_url:
                db_url = db_url.replace('&channel_binding=require', '').replace('channel_binding=require&', '').replace('?channel_binding=require', '?').replace('&channel_binding=require', '')
                if db_url.endswith('?'):
                    db_url = db_url[:-1]
            
            # Create engine with connection timeout
            engine = create_engine(
                db_url, 
                pool_pre_ping=True,
                pool_timeout=5,  # 5 second timeout
                connect_args={
                    "connect_timeout": 5
                }
            )
        else:
            engine = create_engine(db_url, pool_pre_ping=True)
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        # Test connection with timeout
        from sqlalchemy import text
        import signal
        
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()  # Actually fetch to test
            print(f"Successfully connected to database")
            return True
        except Exception as conn_error:
            print(f"Connection test failed: {conn_error}")
            raise
    except Exception as e:
        print(f"ERROR: Failed to initialize database: {e}")
        print(f"Attempting SQLite fallback...")
        # Fallback to SQLite
        try:
            fallback_url = "sqlite:///./askdb_auth.sqlite3"
            engine = create_engine(fallback_url, pool_pre_ping=True)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            print(f"Using SQLite fallback: {fallback_url}")
            return True
        except Exception as fallback_error:
            print(f"ERROR: SQLite fallback also failed: {fallback_error}")
            return False

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    
    def set_password(self, password: str):
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))


class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(500), default="New Conversation")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    sql_query = Column(Text)  # Store generated SQL (server-side only, never shown to user)
    rows_returned = Column(Integer, default=0)
    success = Column(Integer, default=1)  # 1 for success, 0 for failure
    created_at = Column(DateTime, default=datetime.utcnow)
    
    chat = relationship("Chat", back_populates="messages")

class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    action = Column(String(100), nullable=False)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)



def init_db():
    """Initialize database tables"""
    if not init_db_connection():
        return False
    try:
        Base.metadata.create_all(bind=engine)
        return True
    except Exception as e:
        print(f"ERROR: Failed to create tables: {e}")
        return False


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_user(username: str, email: str, password: str, display_name: Optional[str] = None) -> Optional[User]:
    """Create new user with error handling"""
    if not init_db_connection():
        print("ERROR: Cannot create user - database not connected")
        return None
    
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            print(f"User already exists: {username}")
            return None
        
        user = User(
            username=username,
            email=email,
            display_name=display_name or username
        )
        user.set_password(password)
        
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Successfully created user: {username}")
        return user
    except Exception as e:
        db.rollback()
        print(f"ERROR creating user: {e}")
        return None
    finally:
        db.close()


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate user with error handling"""
    if not init_db_connection():
        print("ERROR: Cannot authenticate - database not connected")
        return None
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user and user.check_password(password):
            print(f"Successfully authenticated user: {username}")
            return user
        print(f"Authentication failed for user: {username}")
        return None
    except Exception as e:
        print(f"ERROR during authentication: {e}")
        return None
    finally:
        db.close()


def get_user_by_id(user_id: int) -> Optional[User]:
    db = SessionLocal()
    try:
        return db.query(User).filter(User.id == user_id).first()
    finally:
        db.close()


def create_chat(user_id: int, title: str = "New Conversation") -> Optional[Chat]:
    db = SessionLocal()
    try:
        chat = Chat(user_id=user_id, title=title)
        db.add(chat)
        db.commit()
        db.refresh(chat)
        return chat
    except Exception as e:
        db.rollback()
        print(f"Error creating chat: {e}")
        return None
    finally:
        db.close()


def get_user_chats(user_id: int, limit: int = 20) -> List[Chat]:
    """Get user chats with pagination limit"""
    if not init_db_connection():
        return []
    db = SessionLocal()
    try:
        return db.query(Chat).filter(Chat.user_id == user_id).order_by(Chat.updated_at.desc()).limit(limit).all()
    except Exception as e:
        print(f"ERROR: Failed to get user chats: {e}")
        return []
    finally:
        db.close()


def get_chat_messages(chat_id: int) -> List[Message]:
    db = SessionLocal()
    try:
        return db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at).all()
    finally:
        db.close()


def add_message(chat_id: int, role: str, content: str, sql_query: Optional[str] = None, 
                rows_returned: int = 0, success: bool = True) -> Optional[Message]:
    db = SessionLocal()
    try:
        message = Message(
            chat_id=chat_id,
            role=role,
            content=content,
            sql_query=sql_query,
            rows_returned=rows_returned,
            success=1 if success else 0
        )
        db.add(message)
        
        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        if chat:
            chat.updated_at = datetime.utcnow()
            if role == 'user' and chat.title.startswith("New"):
                chat.title = content[:100]
        
        db.commit()
        db.refresh(message)
        return message
    except Exception as e:
        db.rollback()
        print(f"Error adding message: {e}")
        return None
    finally:
        db.close()


def delete_chat(chat_id: int, user_id: int) -> bool:
    db = SessionLocal()
    try:
        chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
        if chat:
            db.delete(chat)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        print(f"Error deleting chat: {e}")
        return False
    finally:
        db.close()

def update_chat_title(chat_id: int, user_id: int, new_title: str) -> bool:
    db = SessionLocal()
    try:
        chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
        if not chat:
            return False
        chat.title = new_title[:500]
        chat.updated_at = datetime.utcnow()
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Error updating chat title: {e}")
        return False
    finally:
        db.close()

def create_log(user_id: Optional[int], action: str, detail: str) -> bool:
    if not init_db_connection():
        return False
    
    db = SessionLocal()
    try:
        log = Log(
            user_id=user_id,
            action=action,
            detail=detail
        )
        db.add(log)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"ERROR creating log: {e}")
        return False
    finally:
        db.close()
