"""
Upload and manage user-uploaded SQLite databases
"""
import os
import shutil
import tempfile
import uuid
from typing import Dict, List
from pathlib import Path
import sqlite3
import pandas as pd


# Store mapping of session_id -> database path
# In production, use Redis or a database for this
DB_SESSIONS: Dict[str, str] = {}

# Temp directory for uploaded databases
TEMP_DB_DIR = os.path.join(tempfile.gettempdir(), "askdb_uploads")
os.makedirs(TEMP_DB_DIR, exist_ok=True)


def create_db_session() -> str:
    """Create a new database session ID"""
    session_id = str(uuid.uuid4())
    return session_id


def get_db_path(session_id: str) -> str:
    """Get the database path for a session"""
    if session_id in DB_SESSIONS:
        return DB_SESSIONS[session_id]
    return None


def save_uploaded_db(file_bytes: bytes, filename: str, session_id: str = None) -> tuple:
    """
    Save uploaded database file
    Returns: (session_id, db_path, tables_created)
    """
    if not session_id:
        session_id = create_db_session()
    
    # Create unique path for this session
    db_path = os.path.join(TEMP_DB_DIR, f"{session_id}.sqlite")
    
    # Determine file type
    file_ext = filename.split('.')[-1].lower()
    tables_created = []
    
    if file_ext in ['db', 'sqlite', 'sqlite3']:
        # Direct SQLite file
        with open(db_path, 'wb') as f:
            f.write(file_bytes)
        
        # Extract table names
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        tables_created = [t[0] for t in tables]
        conn.close()
    
    elif file_ext in ['csv', 'xls', 'xlsx']:
        # Convert to SQLite
        if file_ext == 'csv':
            # Save to temp file first
            temp_path = os.path.join(TEMP_DB_DIR, f"temp_{uuid.uuid4()}.csv")
            with open(temp_path, 'wb') as f:
                f.write(file_bytes)
            df = pd.read_csv(temp_path)
            os.remove(temp_path)
        else:
            # Excel file
            temp_path = os.path.join(TEMP_DB_DIR, f"temp_{uuid.uuid4()}.{file_ext}")
            with open(temp_path, 'wb') as f:
                f.write(file_bytes)
            df = pd.read_excel(temp_path)
            os.remove(temp_path)
        
        # Create table name from filename
        table_name = filename.rsplit('.', 1)[0]
        table_name = table_name.replace(' ', '_').replace('-', '_')
        
        # Create or append to SQLite database
        conn = sqlite3.connect(db_path)
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        conn.close()
        
        tables_created = [table_name]
    
    else:
        raise ValueError(f"Unsupported file type: {file_ext}")
    
    # Store session
    DB_SESSIONS[session_id] = db_path
    
    return session_id, db_path, tables_created


def add_table_to_session(file_bytes: bytes, filename: str, session_id: str) -> List[str]:
    """
    Add another table to an existing session
    Returns: list of tables created
    """
    db_path = get_db_path(session_id)
    if not db_path:
        raise ValueError(f"Session {session_id} not found")
    
    file_ext = filename.split('.')[-1].lower()
    tables_created = []
    
    if file_ext in ['db', 'sqlite', 'sqlite3']:
        # Merge SQLite databases
        temp_db_path = os.path.join(TEMP_DB_DIR, f"temp_{uuid.uuid4()}.sqlite")
        with open(temp_db_path, 'wb') as f:
            f.write(file_bytes)
        
        # Attach and copy tables
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"ATTACH DATABASE '{temp_db_path}' AS source_db")
        
        cursor.execute("SELECT name FROM source_db.sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            try:
                cursor.execute(f'CREATE TABLE IF NOT EXISTS "{table_name}" AS SELECT * FROM source_db."{table_name}"')
                tables_created.append(table_name)
            except Exception as e:
                print(f"Warning: Could not copy table {table_name}: {e}")
        
        cursor.execute("DETACH DATABASE source_db")
        conn.commit()
        conn.close()
        
        os.remove(temp_db_path)
    
    elif file_ext in ['csv', 'xls', 'xlsx']:
        # Add CSV/Excel as new table
        if file_ext == 'csv':
            temp_path = os.path.join(TEMP_DB_DIR, f"temp_{uuid.uuid4()}.csv")
            with open(temp_path, 'wb') as f:
                f.write(file_bytes)
            df = pd.read_csv(temp_path)
            os.remove(temp_path)
        else:
            temp_path = os.path.join(TEMP_DB_DIR, f"temp_{uuid.uuid4()}.{file_ext}")
            with open(temp_path, 'wb') as f:
                f.write(file_bytes)
            df = pd.read_excel(temp_path)
            os.remove(temp_path)
        
        table_name = filename.rsplit('.', 1)[0]
        table_name = table_name.replace(' ', '_').replace('-', '_')
        
        conn = sqlite3.connect(db_path)
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        conn.close()
        
        tables_created = [table_name]
    
    return tables_created


def cleanup_session(session_id: str):
    """Remove a database session"""
    if session_id in DB_SESSIONS:
        db_path = DB_SESSIONS[session_id]
        if os.path.exists(db_path):
            os.remove(db_path)
        del DB_SESSIONS[session_id]


def cleanup_old_sessions(max_age_hours: int = 24):
    """Clean up old database sessions"""
    import time
    current_time = time.time()
    
    for session_id, db_path in list(DB_SESSIONS.items()):
        if os.path.exists(db_path):
            file_age_hours = (current_time - os.path.getmtime(db_path)) / 3600
            if file_age_hours > max_age_hours:
                cleanup_session(session_id)
