"""
Safe SQL Query Execution on User-Uploaded SQLite Databases
"""
import sqlite3
import pandas as pd
from typing import Tuple, Optional, List, Dict


def execute_query(sql: str, db_path: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Execute SQL query on user's database
    Returns: (dataframe, error_message)
    """
    # Security checks
    sql_clean = sql.strip().upper()
    
    dangerous_keywords = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
        'TRUNCATE', 'REPLACE', 'PRAGMA', 'ATTACH', 'DETACH'
    ]
    
    for keyword in dangerous_keywords:
        if keyword in sql_clean:
            return None, f"Error: {keyword} statements are not allowed. Only read-only queries (SELECT, WITH) are permitted."
    
    if not (sql_clean.startswith("SELECT") or sql_clean.startswith("WITH")):
        return None, "Error: Only SELECT and WITH (CTE) queries are allowed for safety."
    
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(sql, conn)
        conn.close()
        return df, None
    except Exception as e:
        error_msg = sanitize_error_message(str(e))
        return None, error_msg


def sanitize_error_message(error_msg: str) -> str:
    """Remove SQL query content from error messages"""
    error_str = str(error_msg)
    
    if "near" in error_str.lower():
        parts = error_str.split("near")
        if len(parts) > 1:
            return f"Query syntax error near {parts[-1].strip()}"
    
    if "no such table" in error_str.lower():
        return "Database table not found. Please check your data structure."
    
    if "no such column" in error_str.lower():
        return "Column not found in the database. Please rephrase your question."
    
    if "ambiguous column" in error_str.lower():
        return "Ambiguous column reference. Please be more specific in your question."
    
    return "Unable to process your question. Please try rephrasing or asking something simpler."


def get_table_preview(db_path: str, table_name: str, limit: int = 10) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Get preview of a table
    Returns: (dataframe, error_message)
    """
    try:
        conn = sqlite3.connect(db_path)
        # Properly quote table name
        quoted_table = f'"{table_name}"'
        df = pd.read_sql_query(f"SELECT * FROM {quoted_table} LIMIT {limit}", conn)
        conn.close()
        return df, None
    except Exception as e:
        return None, f"Error previewing table: {str(e)}"


def get_table_stats(db_path: str, table_name: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Get statistics for a table
    Returns: (stats_dict, error_message)
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get row count
        quoted_table = f'"{table_name}"'
        cursor.execute(f"SELECT COUNT(*) FROM {quoted_table}")
        row_count = cursor.fetchone()[0]
        
        # Get column info
        cursor.execute(f"PRAGMA table_info({quoted_table})")
        columns = cursor.fetchall()
        
        stats = {
            "table_name": table_name,
            "row_count": row_count,
            "column_count": len(columns),
            "columns": [{"name": col[1], "type": col[2]} for col in columns]
        }
        
        conn.close()
        return stats, None
    except Exception as e:
        return None, f"Error getting table stats: {str(e)}"
