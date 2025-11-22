"""
Pydantic models for FastAPI request/response validation
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# Auth Models
class UserSignup(BaseModel):
    username: str
    email: EmailStr
    password: str
    display_name: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    display_name: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    display_name: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Chat Models
class ChatCreate(BaseModel):
    title: str = "New Conversation"


class ChatResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Message Models
class MessageCreate(BaseModel):
    chat_id: int
    role: str  # 'user' or 'assistant'
    content: str
    sql_query: Optional[str] = None
    rows_returned: int = 0
    success: bool = True


class MessageResponse(BaseModel):
    id: int
    chat_id: int
    role: str
    content: str
    sql_query: Optional[str]
    rows_returned: int
    success: int
    created_at: datetime

    class Config:
        from_attributes = True


# Query Models
class QueryRequest(BaseModel):
    question: str
    db_session_id: str  # Unique ID for uploaded database session


class QueryResponse(BaseModel):
    success: bool
    sql_query: Optional[str]
    results: Optional[List[dict]]
    rows_returned: int
    error: Optional[str] = None
    explanation: Optional[str] = None


# Upload Models
class UploadResponse(BaseModel):
    success: bool
    db_session_id: str
    tables: List[str]
    message: str


# Schema Models
class SchemaResponse(BaseModel):
    tables: dict  # {table_name: [columns]}
    relationships: dict  # {table: [{from_col, to_table, to_col}]}
