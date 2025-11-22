"""
AskDB FastAPI Backend
Handles authentication, database uploads, and NL2SQL queries
"""
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import modules
from database import init_db, create_user, create_chat, add_message, get_user_chats, get_chat_messages, create_log
from backend.auth import (
    authenticate_user_jwt,
    create_access_token,
    get_current_user,
    get_password_hash
)
from backend.models import (
    UserSignup,
    UserLogin,
    Token,
    UserResponse,
    ChatCreate,
    ChatResponse,
    MessageCreate,
    MessageResponse,
    QueryRequest,
    QueryResponse,
    UploadResponse,
    SchemaResponse
)
from backend.upload import (
    save_uploaded_db,
    add_table_to_session,
    get_db_path,
    cleanup_session,
    cleanup_old_sessions
)
from backend.nl2sql import generate_sql_from_nl, get_database_schema, get_query_explanation
from backend.query_runner import execute_query, get_table_preview, get_table_stats

app = FastAPI(
    title="AskDB API",
    description="Natural Language to SQL Query System with PostgreSQL backend",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    success = init_db()
    if not success:
        print("WARNING: Database initialization failed. Check DATABASE_URL.")
    else:
        print("Database initialized successfully")
    
    # Cleanup old uploaded databases
    cleanup_old_sessions(max_age_hours=24)


# ===== AUTH ROUTES =====

@app.post("/api/auth/signup", response_model=Token, tags=["Authentication"])
async def signup(user_data: UserSignup):
    """Register a new user"""
    user = create_user(
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        display_name=user_data.display_name
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    # Log registration
    create_log("info", "auth", f"User registered: {user.username}", user_id=user.id)
    
    return Token(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
        display_name=user.display_name or user.username
    )


@app.post("/api/auth/login", response_model=Token, tags=["Authentication"])
async def login(credentials: UserLogin):
    """Login with username and password"""
    user = authenticate_user_jwt(credentials.username, credentials.password)
    
    if not user:
        create_log("warning", "auth", f"Failed login attempt: {credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    # Log successful login
    create_log("info", "auth", f"User logged in: {user.username}", user_id=user.id)
    
    return Token(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
        display_name=user.display_name or user.username
    )


@app.get("/api/auth/me", response_model=UserResponse, tags=["Authentication"])
async def get_me(current_user = Depends(get_current_user)):
    """Get current user info"""
    return current_user


# ===== UPLOAD ROUTES =====

@app.post("/api/upload", response_model=UploadResponse, tags=["Upload"])
async def upload_database(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    current_user = Depends(get_current_user)
):
    """Upload a database file (SQLite, CSV, or Excel)"""
    try:
        # Read file content
        content = await file.read()
        
        if session_id:
            # Add to existing session
            tables = add_table_to_session(content, file.filename, session_id)
            message = f"Added {len(tables)} table(s) to existing session"
        else:
            # Create new session
            session_id, db_path, tables = save_uploaded_db(content, file.filename)
            message = f"Created new session with {len(tables)} table(s)"
        
        # Log upload
        create_log("info", "upload", f"File uploaded: {file.filename}", user_id=current_user.id)
        
        return UploadResponse(
            success=True,
            db_session_id=session_id,
            tables=tables,
            message=message
        )
    
    except Exception as e:
        create_log("error", "upload", f"Upload failed: {str(e)}", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload failed: {str(e)}"
        )


@app.delete("/api/upload/{session_id}", tags=["Upload"])
async def delete_session(session_id: str, current_user = Depends(get_current_user)):
    """Delete an uploaded database session"""
    cleanup_session(session_id)
    return {"message": "Session deleted successfully"}


# ===== SCHEMA ROUTES =====

@app.get("/api/schema/{session_id}", response_model=SchemaResponse, tags=["Schema"])
async def get_schema(session_id: str, current_user = Depends(get_current_user)):
    """Get database schema and relationships"""
    db_path = get_db_path(session_id)
    if not db_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Database session not found"
        )
    
    schema, relationships, error = get_database_schema(db_path)
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error
        )
    
    return SchemaResponse(tables=schema, relationships=relationships)


@app.get("/api/table/{session_id}/{table_name}/preview", tags=["Schema"])
async def preview_table(
    session_id: str,
    table_name: str,
    limit: int = 10,
    current_user = Depends(get_current_user)
):
    """Get a preview of a table"""
    db_path = get_db_path(session_id)
    if not db_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Database session not found"
        )
    
    df, error = get_table_preview(db_path, table_name, limit)
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"data": df.to_dict('records'), "columns": list(df.columns)}


# ===== QUERY ROUTES =====

@app.post("/api/query", response_model=QueryResponse, tags=["Query"])
async def execute_nl_query(
    request: QueryRequest,
    chat_id: Optional[int] = None,
    current_user = Depends(get_current_user)
):
    """Execute a natural language query"""
    # Get database path
    db_path = get_db_path(request.db_session_id)
    if not db_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Database session not found"
        )
    
    try:
        # Generate SQL
        sql, schema, error = generate_sql_from_nl(request.question, db_path)
        if error:
            create_log("error", "query", f"SQL generation failed: {error}", user_id=current_user.id, chat_id=chat_id)
            return QueryResponse(
                success=False,
                sql_query=None,
                results=None,
                rows_returned=0,
                error=error
            )
        
        # Execute query
        df, error = execute_query(sql, db_path)
        if error:
            create_log("error", "query", f"Query execution failed: {error}", user_id=current_user.id, chat_id=chat_id)
            
            # Save to chat if chat_id provided
            if chat_id:
                add_message(chat_id, "user", request.question)
                add_message(chat_id, "assistant", f"Error: {error}", sql_query=sql, rows_returned=0, success=False)
            
            return QueryResponse(
                success=False,
                sql_query=sql,
                results=None,
                rows_returned=0,
                error=error
            )
        
        # Success
        results = df.to_dict('records') if df is not None else []
        rows_returned = len(df) if df is not None else 0
        
        # Get explanation
        explanation = get_query_explanation(sql, schema)
        
        # Log success
        create_log("info", "query", f"Query executed: {rows_returned} rows", user_id=current_user.id, chat_id=chat_id)
        
        # Save to chat if chat_id provided
        if chat_id:
            add_message(chat_id, "user", request.question)
            add_message(chat_id, "assistant", explanation, sql_query=sql, rows_returned=rows_returned, success=True)
        
        return QueryResponse(
            success=True,
            sql_query=sql,
            results=results,
            rows_returned=rows_returned,
            explanation=explanation
        )
    
    except Exception as e:
        create_log("error", "query", f"Unexpected error: {str(e)}", user_id=current_user.id, chat_id=chat_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}"
        )


# ===== CHAT ROUTES =====

@app.post("/api/chats", response_model=ChatResponse, tags=["Chats"])
async def create_new_chat(
    chat_data: ChatCreate,
    current_user = Depends(get_current_user)
):
    """Create a new chat"""
    chat = create_chat(current_user.id, chat_data.title)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chat"
        )
    return chat


@app.get("/api/chats", response_model=List[ChatResponse], tags=["Chats"])
async def list_chats(current_user = Depends(get_current_user)):
    """Get all chats for current user"""
    chats = get_user_chats(current_user.id)
    return chats


@app.get("/api/chats/{chat_id}/messages", response_model=List[MessageResponse], tags=["Chats"])
async def get_messages(chat_id: int, current_user = Depends(get_current_user)):
    """Get all messages in a chat"""
    messages = get_chat_messages(chat_id)
    return messages


# ===== HEALTH CHECK =====

@app.get("/", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AskDB API",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
