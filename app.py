from dotenv import load_dotenv
load_dotenv()

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))


import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go


try:
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
except ImportError:
    st.error("⚠️ Installing transformers package... Please wait and refresh the page.")
    st.stop()

import torch
import os
import tempfile
from typing import Dict, List, Tuple, Optional
import database
from core import generate_sql as core_generate_sql

try:
    from ui_enhancements import inject_custom_css, render_app_header, render_stat_card, render_feature_card
    UI_ENHANCEMENTS_AVAILABLE = True
except ImportError as e:
    print(f"UI enhancements not available: {e}")
    UI_ENHANCEMENTS_AVAILABLE = False
    # Fallback functions
    def inject_custom_css():
        pass
    def render_app_header(title, subtitle):
        st.title(title)
        st.markdown(subtitle)
    def render_stat_card(value, label):
        st.metric(label, value)
    def render_feature_card(title, description, icon="✨"):
        st.markdown(f"**{icon} {title}**")
        st.write(description)

st.set_page_config(
    page_title="AskDB - Natural Language to SQL",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom CSS for stunning UI
try:
    inject_custom_css()
except Exception as e:
    print(f"CSS injection error (non-critical): {e}")

@st.cache_resource
def load_nl2sql_model(model_name: str = "mrm8488/t5-base-finetuned-wikiSQL"):
    hf_token = os.environ.get('HUGGING_FACE_TOKEN', None)
    tokenizer = AutoTokenizer.from_pretrained(model_name, token=hf_token)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name, token=hf_token)
    return tokenizer, model

@st.cache_resource
def load_summarization_model(model_name: str = "t5-small"):
    hf_token = os.environ.get('HUGGING_FACE_TOKEN', None)
    tokenizer = AutoTokenizer.from_pretrained(model_name, token=hf_token)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name, token=hf_token)
    return tokenizer, model

# --- GLOBAL MODEL LOAD (prevents Streamlit rerun crash) ---
@st.cache_resource
def get_nl2sql():
    return load_nl2sql_model()

@st.cache_resource
def get_summarizer():
    return load_summarization_model()

# ----------------------------------------------------------


def extract_schema(db_path: str) -> Dict[str, List[str]]:
    """Extract schema with column names"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    schema = {}
    for table in tables:
        table_name = table[0]
        try:
            # Properly quote table names to handle spaces and reserved words
            quoted_table = quote_identifier(table_name)
            cursor.execute(f"PRAGMA table_info({quoted_table})")
            columns = cursor.fetchall()
            schema[table_name] = [col[1] for col in columns]
        except Exception as e:
            # Log error but continue with other tables
            print(f"Warning: Could not extract schema for table '{table_name}': {str(e)}")
            schema[table_name] = []
    
    conn.close()
    return schema

def detect_foreign_keys(db_path: str) -> Dict[str, List[Dict]]:
    """Detect foreign key relationships between tables using PRAGMA and heuristics"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]
    
    relationships = {}  # {table_name: [{from_col, to_table, to_col}]}
    
    for table_name in tables:
        quoted_table = quote_identifier(table_name)
        relationships[table_name] = []
        
        try:
            # Use PRAGMA foreign_key_list to get explicit foreign keys
            cursor.execute(f"PRAGMA foreign_key_list({quoted_table})")
            fks = cursor.fetchall()
            
            for fk in fks:
                relationships[table_name].append({
                    'from_column': fk[3],  # 'from' column
                    'to_table': fk[2],     # 'table' column
                    'to_column': fk[4]     # 'to' column
                })
        except:
            pass
        
        # Heuristic matching: column names like "customer_id" → "customers" table
        try:
            cursor.execute(f"PRAGMA table_info({quoted_table})")
            columns = cursor.fetchall()
            
            for col in columns:
                col_name = col[1].lower()
                
                # Check for common foreign key patterns
                if col_name.endswith('_id'):
                    potential_table = col_name[:-3]  # Remove "_id"
                    
                    # Try to find matching table (exact or plural)
                    for other_table in tables:
                        other_lower = other_table.lower()
                        if other_lower == potential_table or \
                           other_lower == potential_table + 's' or \
                           other_lower + 's' == potential_table:
                            # Check if this relationship already exists
                            exists = any(r['from_column'].lower() == col_name and 
                                       r['to_table'].lower() == other_table.lower() 
                                       for r in relationships[table_name])
                            if not exists:
                                relationships[table_name].append({
                                    'from_column': col[1],
                                    'to_table': other_table,
                                    'to_column': 'id',  # Assume 'id' as default
                                    'heuristic': True
                                })
        except:
            pass
    
    conn.close()
    return relationships

def extract_enhanced_schema(db_path: str) -> Dict[str, Dict]:
    """Extract rich schema with column types and sample values for AI"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    enhanced_schema = {}
    for table in tables:
        table_name = table[0]
        try:
            quoted_table = quote_identifier(table_name)
            
            # Get column info with types
            cursor.execute(f"PRAGMA table_info({quoted_table})")
            columns_info = cursor.fetchall()
            
            columns = {}
            for col in columns_info:
                col_name = col[1]
                col_type = col[2]
                quoted_col = quote_identifier(col_name)
                
                # Get sample values (all distinct values, limited to 50 for performance)
                try:
                    cursor.execute(f"SELECT DISTINCT {quoted_col} FROM {quoted_table} LIMIT 50")
                    samples = [str(row[0]) for row in cursor.fetchall() if row[0] is not None]
                except:
                    samples = []
                
                columns[col_name] = {
                    'type': col_type if col_type else 'text',
                    'samples': samples
                }
            
            enhanced_schema[table_name] = {
                'columns': columns
            }
        except Exception as e:
            print(f"Warning: Could not extract enhanced schema for '{table_name}': {str(e)}")
            enhanced_schema[table_name] = {'columns': {}}
    
    conn.close()
    return enhanced_schema

def quote_identifier(name: str) -> str:
    """Properly quote SQL identifiers to handle spaces and reserved words"""
    return f'"{name.replace(chr(34), chr(34)+chr(34))}"'

def format_schema_for_model(schema: Dict[str, List[str]]) -> str:
    schema_lines = []
    for table_name, columns in schema.items():
        column_list = ', '.join(columns)
        schema_lines.append(f"Table {table_name} has columns: {column_list}")
    schema_str = '\n'.join(schema_lines)
    return schema_str

def get_join_template_sql(question: str, related_tables: List[str], all_columns: Dict, foreign_keys: Dict, db_path: str = None) -> Optional[str]:
    """Generate JOIN SQL based on FK relationships (Stage 2: FK-driven JOIN templates)"""
    if len(related_tables) < 2:
        return None
    
    q_lower = question.lower()
    primary_table = related_tables[0]
    
    # Find FK relationship between tables
    join_clauses = []
    tables_in_join = [primary_table]
    
    for i in range(len(related_tables) - 1):
        current_table = related_tables[i]
        next_table = related_tables[i + 1]
        
        # Look for FK from current_table to next_table
        join_found = False
        if current_table in foreign_keys:
            for fk in foreign_keys[current_table]:
                if fk['to_table'] == next_table:
                    from_col = quote_identifier(fk['from_column'])
                    to_col = quote_identifier(fk.get('to_column', 'id'))
                    join_clauses.append(
                        f"JOIN {quote_identifier(next_table)} ON {quote_identifier(current_table)}.{from_col} = {quote_identifier(next_table)}.{to_col}"
                    )
                    tables_in_join.append(next_table)
                    join_found = True
                    break
        
        # Try reverse: FK from next_table to current_table
        if not join_found and next_table in foreign_keys:
            for fk in foreign_keys[next_table]:
                if fk['to_table'] == current_table:
                    from_col = quote_identifier(fk['from_column'])
                    to_col = quote_identifier(fk.get('to_column', 'id'))
                    join_clauses.append(
                        f"JOIN {quote_identifier(next_table)} ON {quote_identifier(next_table)}.{from_col} = {quote_identifier(current_table)}.{to_col}"
                    )
                    tables_in_join.append(next_table)
                    join_found = True
                    break
        
        if not join_found:
            print(f"[JOIN TEMPLATE] No FK relationship found between {current_table} and {next_table}")
            return None
    
    # Build SELECT clause - prefer * for simplicity, but can be enhanced
    select_clause = "*"
    
    # Check for aggregation keywords
    if any(kw in q_lower for kw in ['count', 'how many', 'number of', 'total number']):
        # COUNT query with JOIN
        group_by_col = None
        # Look for columns from related tables
        for table in tables_in_join:
            table_cols = all_columns.get(table, [])
            for col in table_cols:
                if col.lower() in q_lower:
                    group_by_col = f"{quote_identifier(table)}.{quote_identifier(col)}"
                    break
            if group_by_col:
                break
        
        if group_by_col:
            select_clause = f"{group_by_col}, COUNT(*) as count"
            join_sql = f"SELECT {select_clause} FROM {quote_identifier(primary_table)} {' '.join(join_clauses)} GROUP BY {group_by_col}"
            return join_sql
        else:
            # Simple count with JOIN
            join_sql = f"SELECT COUNT(*) as total FROM {quote_identifier(primary_table)} {' '.join(join_clauses)}"
            return join_sql
    
    # Default: SELECT * with JOIN
    join_sql = f"SELECT * FROM {quote_identifier(primary_table)} {' '.join(join_clauses)}"
    
    # Add WHERE clause if filtering mentioned
    if any(kw in q_lower for kw in ['where', 'greater than', 'less than', 'above', 'below', '>']):
        # Let AI handle complex filtering
        return None
    
    print(f"[JOIN TEMPLATE] Generated: {join_sql}")
    return join_sql


def get_template_sql(question: str, table_name: str, columns: List[str], db_path: str = None) -> Optional[str]:
    """Generate SQL from templates for common query patterns with value-aware matching"""
    q_lower = question.lower()
    import re
    
    quoted_table = quote_identifier(table_name)
    
    # Build value→column mapping from enhanced schema
    # Structure: {lowercase_value: (column_name, original_value)}
    value_to_column = {}
    if db_path:
        try:
            enhanced_schema = extract_enhanced_schema(db_path)
            if table_name in enhanced_schema:
                for col_name, col_info in enhanced_schema[table_name].get('columns', {}).items():
                    samples = col_info.get('samples', [])
                    for sample in samples:
                        # Map lowercase to both column and original value
                        value_to_column[sample.lower()] = (col_name, sample)
        except:
            pass  # If enhanced schema fails, continue without it
    
    # PRIORITY 1: AGGREGATE FUNCTIONS (must come first!)
    # AVERAGE queries
    if 'average' in q_lower or 'avg' in q_lower:
        # Check for "average X by Y" pattern (with GROUP BY)
        if ' by ' in q_lower:
            # Find what to average and what to group by
            avg_col = None
            group_col = None
            
            # Common aggregation columns (expanded for diverse databases)
            agg_keywords = ['score', 'price', 'amount', 'value', 'salary', 'revenue', 'sales', 
                           'cost', 'total', 'quantity', 'qty', 'count', 'number', 'rate',
                           'balance', 'payment', 'profit', 'discount', 'tax', 'fee', 'charge']
            
            # First, try to find numeric columns mentioned in question
            for col in columns:
                if col.lower() in q_lower:
                    # Check if it's likely a numeric column
                    col_lower = col.lower()
                    if any(kw in col_lower for kw in agg_keywords):
                        avg_col = col
                        break
            
            # Fallback: search by keyword
            if not avg_col:
                for keyword in agg_keywords:
                    if keyword in q_lower:
                        for col in columns:
                            if keyword in col.lower():
                                avg_col = col
                                break
                        if avg_col:
                            break
            
            # Find group by column (after "by")
            by_index = q_lower.find(' by ')
            if by_index != -1:
                after_by = q_lower[by_index + 4:].strip()
                for col in columns:
                    if col.lower() in after_by:
                        group_col = col
                        break
            
            if avg_col and group_col:
                quoted_avg = quote_identifier(avg_col)
                quoted_group = quote_identifier(group_col)
                return f"SELECT {quoted_group}, AVG({quoted_avg}) as average_{avg_col} FROM {quoted_table} GROUP BY {quoted_group}"
        
        # Simple average (no GROUP BY)
        for col in columns:
            if col in q_lower:
                quoted_col = quote_identifier(col)
                return f"SELECT AVG({quoted_col}) as average_{col} FROM {quoted_table}"
    
    # COUNT queries (count, how many, number of)
    count_keywords = ['count', 'how many', 'number of', 'total number']
    if any(keyword in q_lower for keyword in count_keywords) and \
       not any(word in q_lower for word in ['where', 'above', 'below', 'average', 'sum', 'total revenue', 'total price']):
        if 'by' in q_lower or 'group' in q_lower:
            for col in columns:
                if col in q_lower:
                    quoted_col = quote_identifier(col)
                    return f"SELECT {quoted_col}, COUNT(*) as count FROM {quoted_table} GROUP BY {quoted_col}"
        return f"SELECT COUNT(*) as total FROM {quoted_table}"
    
    # SUM queries (total, revenue, sum)
    sum_keywords = ['total', 'revenue', 'sum', 'combined']
    if any(keyword in q_lower for keyword in sum_keywords) and \
       not any(word in q_lower for word in ['where', 'above', 'below', 'count', 'average']):
        # Find which numeric column to sum
        sum_col = None
        
        # Look for explicit column mentions
        for col in columns:
            col_lower = col.lower()
            # Check if column name appears in question or is a likely numeric field
            if col_lower in q_lower or \
               any(keyword in col_lower for keyword in ['amount', 'total', 'price', 'cost', 'revenue', 'value', 'quantity', 'sales']):
                # Verify it's a numeric column from enhanced schema if available
                if db_path:
                    try:
                        enhanced_schema = extract_enhanced_schema(db_path)
                        if table_name in enhanced_schema:
                            col_info = enhanced_schema[table_name].get('columns', {}).get(col, {})
                            col_type = col_info.get('type', '').lower()
                            if col_type in ['integer', 'real', 'numeric', 'decimal', 'float']:
                                sum_col = col
                                break
                    except:
                        pass
                # Fallback: assume columns with numeric names are numeric
                if any(keyword in col_lower for keyword in ['amount', 'total', 'price', 'cost', 'revenue', 'value', 'sales']):
                    sum_col = col
                    break
        
        # If found a column to sum, generate SQL
        if sum_col:
            quoted_col = quote_identifier(sum_col)
            return f"SELECT SUM({quoted_col}) as total_{sum_col} FROM {quoted_table}"
    
    # PRIORITY 2: FILTER queries with WHERE conditions
    for col in columns:
        if col in q_lower:
            quoted_col = quote_identifier(col)
            # Greater than queries
            if any(word in q_lower for word in ['greater than', 'more than', 'above', '>']):
                number_match = re.search(r'(\d+(?:\.\d+)?)', q_lower)
                if number_match:
                    value = number_match.group(1)
                    return f"SELECT * FROM {quoted_table} WHERE {quoted_col} > {value}"
            
            # Less than queries
            if any(word in q_lower for word in ['less than', 'below', 'under', '<']):
                number_match = re.search(r'(\d+(?:\.\d+)?)', q_lower)
                if number_match:
                    value = number_match.group(1)
                    return f"SELECT * FROM {quoted_table} WHERE {quoted_col} < {value}"
            
            # Equals queries (explicit)
            if any(word in q_lower for word in ['equals', 'equal to', '=']):
                # Try number first
                number_match = re.search(r'(\d+(?:\.\d+)?)', q_lower)
                if number_match:
                    value = number_match.group(1)
                    return f"SELECT * FROM {quoted_table} WHERE {quoted_col} = {value}"
                # Otherwise look for quoted text
                text_match = re.search(r"['\"]([^'\"]+)['\"]", q_lower)
                if text_match:
                    value = text_match.group(1)
                    return f"SELECT * FROM {quoted_table} WHERE {quoted_col} = '{value}'"
    
    # PRIORITY 3: Value-aware text filter patterns
    # Pattern: "show all Science students" (Science is the filter value)
    if any(word in q_lower for word in ['show', 'list', 'display']) and \
       not any(word in q_lower for word in ['average', 'count', 'sum']):  # Skip if aggregate
        
        # First try value-aware matching using sample data
        if value_to_column:
            words = question.split()
            for word in words:
                word_clean = word.lower().strip('.,!?;:')
                if len(word_clean) <= 2:
                    continue
                
                # Try exact match first
                if word_clean in value_to_column:
                    col_name, original_value = value_to_column[word_clean]
                    quoted_col = quote_identifier(col_name)
                    return f"SELECT * FROM {quoted_table} WHERE {quoted_col} = '{original_value}'"
                
                # Try partial/substring matching (e.g., "Maths" matches "Mathematics")
                for sample_val_lower, (col_name, original_value) in value_to_column.items():
                    # Check if word is substring of sample OR sample is substring of word
                    if (word_clean in sample_val_lower or sample_val_lower in word_clean) and \
                       word_clean not in ['show', 'list', 'display', 'all', 'the', 'students', 'records']:
                        quoted_col = quote_identifier(col_name)
                        # Use the actual sample value (original_value) not the question word
                        return f"SELECT * FROM {quoted_table} WHERE {quoted_col} LIKE '%{original_value}%'"
        
        # Fallback to column name matching (if column name appears in question)
        for col in columns:
            col_lower = col.lower()
            if col_lower in q_lower:
                words = question.split()
                for i, word in enumerate(words):
                    if word.lower() in ['show', 'all', 'the', 'list', 'display', 'get', 'find', 'select']:
                        continue
                    if word.lower() not in ['students', 'records', 'rows', 'entries', 'data'] and \
                       word.lower() != col_lower and \
                       len(word) > 2:
                        word_pos = q_lower.find(word.lower())
                        col_pos = q_lower.find(col_lower)
                        if word_pos < col_pos and word_pos != -1:
                            quoted_col = quote_identifier(col)
                            return f"SELECT * FROM {quoted_table} WHERE {quoted_col} LIKE '%{word}%'"
    
    # PRIORITY 4: SHOW ALL queries (only for genuine "show all" without potential filter values)
    # If the question has specific words that could be values, skip SHOW ALL and fall back to AI
    question_words = [w.lower().strip('.,!?;:') for w in question.split()]
    
    # Exclude table name variations from potential filters
    table_name_lower = table_name.lower()
    table_base = table_name_lower.replace('sample_', '').replace('tbl_', '').replace('tb_', '')
    table_variations = [table_name_lower, table_base]
    if table_base.endswith('s'):
        table_variations.append(table_base[:-1])  # singular
    else:
        table_variations.append(table_base + 's')  # plural
    
    potential_filters = [w for w in question_words if len(w) > 3 and w not in [
        'show', 'all', 'the', 'list', 'display', 'get', 'find', 'select',
        'students', 'records', 'rows', 'entries', 'data', 'everything',
        'items', 'values', 'results', 'table', 'from', 'where', 'customers',
        'orders', 'products', 'people', 'users'
    ] and w not in table_variations]  # Exclude table name variations
    
    # Only use SHOW ALL if there are NO potential filter words (genuine "show all" request)
    if any(word in q_lower for word in ['all', 'everything']) and \
       not any(word in q_lower for word in ['where', 'above', 'below', 'greater', 'less', 'average', 'count']) and \
       len(potential_filters) == 0:
        return f"SELECT * FROM {quoted_table}"
    
    # Return None to fall back to AI for unmatched filter queries
    return None

# Removed - duplicate function replaced with multi-table aware version below

def repair_sql(sql: str, table_name: str, columns: List[str], all_columns: Dict = None, is_multi_table: bool = False) -> str:
    """Multi-table aware SQL repair and validation"""
    import re
    
    quoted_table = quote_identifier(table_name)
    
    print(f"[SQL REPAIR] INPUT SQL: {sql}")
    print(f"[SQL REPAIR] Table: {table_name}, Columns: {columns}, Multi-table: {is_multi_table}")
    
    # Build comprehensive column registry
    valid_columns_lower = set([c.lower() for c in columns])
    valid_tables_lower = set([table_name.lower()])
    
    if is_multi_table and all_columns:
        for tbl, cols in all_columns.items():
            valid_tables_lower.add(tbl.lower())
            for col in cols:
                valid_columns_lower.add(col.lower())
    
    # Clean artifacts
    sql = sql.strip()
    for artifact in ['A:', 'SQL:', '|', 'table:', 'Table:', 'CREATE TABLE', 'col =']:
        if sql.startswith(artifact):
            sql = sql[len(artifact):].strip()
        if artifact in sql and artifact not in ['|', 'A:', 'SQL:']:
            sql = sql.split(artifact)[0].strip()
    
    # Fix table placeholders
    sql = re.sub(r'\bFROM\s+table\b', f'FROM {quoted_table}', sql, flags=re.IGNORECASE)
    
    # Column whitelist check: Multi-table aware validation
    select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
    if select_match and select_match.group(1).strip() not in ['*', 'COUNT(*)', 'COUNT(*)']:
        select_clause = select_match.group(1)
        
        # Check if it's a JOIN query
        has_join = bool(re.search(r'\bJOIN\b', sql, re.IGNORECASE))
        
        # For JOIN queries, skip aggressive validation (preserve structure)
        if has_join:
            print(f"[SQL REPAIR] JOIN detected - preserving multi-table structure")
            print(f"[SQL REPAIR] Final SQL: {sql}")
            return sql
        
        # Single-table validation
        contains_invalid = False
        for word in re.findall(r'\b\w+\b', select_clause):
            if word.upper() not in ['SELECT', 'FROM', 'WHERE', 'COUNT', 'AVG', 'SUM', 'MAX', 'MIN', 'AS', 'DISTINCT', 'BY', 'GROUP']:
                # Check if it's a known column or table (case-insensitive)
                if word.lower() not in valid_columns_lower and word.lower() not in valid_tables_lower:
                    contains_invalid = True
                    print(f"[SQL REPAIR] Unknown column: {word}")
                    break
        
        # If SQL contains invalid columns, fall back to SELECT *
        if contains_invalid:
            # Keep WHERE clause if present
            where_match = re.search(r'WHERE\s+(.+?)(?:ORDER|GROUP|LIMIT|$)', sql, re.IGNORECASE | re.DOTALL)
            if where_match:
                sql = f"SELECT * FROM {quoted_table} WHERE {where_match.group(1).strip()}"
            else:
                sql = f"SELECT * FROM {quoted_table}"
    
    # Ensure it's a SELECT query
    if not sql.upper().startswith('SELECT') and not sql.upper().startswith('WITH'):
        sql = f"SELECT * FROM {quoted_table}"
    
    return sql

def generate_sql(question: str, schema_str: str, tokenizer, model, db_path: str = None, history: Optional[List[Dict]] = None) -> str:
    """AI-first dynamic SQL generation with templates as fast-path"""
    schema_lines = schema_str.split('\n')
    table_names = []
    all_columns = {}
    
    for line in schema_lines:
        if 'Table' in line and 'has columns:' in line:
            parts = line.split('has columns:')
            table_name = parts[0].replace('Table', '').strip()
            columns_str = parts[1].strip()
            columns = [c.strip() for c in columns_str.split(',')]
            table_names.append(table_name)
            all_columns[table_name] = columns
    
    if not table_names:
        return "SELECT 1"
    
    # Detect which tables are mentioned in the question
    # Use smart matching: check full name, base name (without "sample_" prefix), singular/plural
    q_lower = question.lower()
    mentioned_tables = []
    
    for t in table_names:
        t_lower = t.lower()
        # Check full table name
        if t_lower in q_lower:
            mentioned_tables.append(t)
            continue
        
        # Check base name (remove common prefixes like "sample_", "tbl_", etc.)
        base_name = t_lower
        for prefix in ['sample_', 'tbl_', 'tb_']:
            if base_name.startswith(prefix):
                base_name = base_name[len(prefix):]
                break
        
        # Check if base name is in question
        if base_name in q_lower:
            mentioned_tables.append(t)
            continue
        
        # Check singular/plural variations
        if base_name.endswith('s'):
            singular = base_name[:-1]
            if singular in q_lower:
                mentioned_tables.append(t)
        else:
            plural = base_name + 's'
            if plural in q_lower:
                mentioned_tables.append(t)
    
    # Enhanced multi-table detection with FK-driven logic
    # Get foreign keys for analysis
    foreign_keys = {}
    if db_path:
        try:
            foreign_keys = detect_foreign_keys(db_path)
        except:
            pass
    
    # Stage 1: FK-aware multi-table detection
    is_multi_table_query = False
    related_tables = []
    
    # Check 1: Multiple tables explicitly mentioned
    if len(mentioned_tables) > 1:
        is_multi_table_query = True
        related_tables = mentioned_tables[:3]  # Limit to 3 tables max
        print(f"[MULTI-TABLE] Multiple tables mentioned: {related_tables}")
    
    # Check 2: FK relationships detected in question
    elif len(mentioned_tables) == 1 and foreign_keys:
        primary_table = mentioned_tables[0]
        if primary_table in foreign_keys:
            # Look for related table mentions via FK
            for fk in foreign_keys[primary_table]:
                related_table = fk['to_table']
                if related_table in table_names:
                    # Check if related table or its columns mentioned
                    related_cols = all_columns.get(related_table, [])
                    if any(col.lower() in q_lower for col in related_cols):
                        is_multi_table_query = True
                        related_tables = [primary_table, related_table]
                        print(f"[MULTI-TABLE] FK relationship detected: {primary_table} → {related_table}")
                        break
    
    # Check 3: User intent keywords (with FK confirmation)
    if not is_multi_table_query and len(mentioned_tables) == 1:
        intent_keywords = ['with', 'including', 'from both', 'together', 'combined']
        if any(keyword in q_lower for keyword in intent_keywords) and foreign_keys:
            # Only flag as multi-table if FKs exist
            primary_table = mentioned_tables[0] if mentioned_tables else table_names[0]
            if primary_table in foreign_keys and foreign_keys[primary_table]:
                is_multi_table_query = True
                related_tables = [primary_table, foreign_keys[primary_table][0]['to_table']]
                print(f"[MULTI-TABLE] Intent keywords with FK: {related_tables}")
    
    # Use primary table
    if mentioned_tables:
        table_name = mentioned_tables[0]
        print(f"[TABLE DETECTION] Primary table '{table_name}' in question: '{question}'")
    else:
        table_name = table_names[0]
        print(f"[TABLE DETECTION] No table match, using first table '{table_name}' for question: '{question}'")
    
    columns = all_columns.get(table_name, [])
    quoted_table = quote_identifier(table_name)
    
    # Fast-path: Try templates
    if is_multi_table_query and related_tables:
        # Try JOIN template for multi-table queries
        join_template_sql = get_join_template_sql(question, related_tables, all_columns, foreign_keys, db_path)
        if join_template_sql:
            print(f"[JOIN TEMPLATE FAST-PATH] {question}")
            return join_template_sql
    elif not is_multi_table_query:
        # Single-table templates
        template_sql = get_template_sql(question, table_name, columns, db_path)
        if template_sql:
            print(f"[TEMPLATE FAST-PATH] {question}")
            return template_sql
    
    # AI-first approach with enhanced prompting (handles both single and multi-table)
    if is_multi_table_query:
        print(f"[AI-FIRST MULTI-TABLE] {question}")
    else:
        print(f"[AI-FIRST DYNAMIC] {question}")
    
    # Get enhanced schema with sample values and foreign keys if available
    enhanced_schema = {}
    foreign_keys = {}
    if db_path:
        try:
            enhanced_schema = extract_enhanced_schema(db_path)
            foreign_keys = detect_foreign_keys(db_path)
        except:
            pass
    
    # Build rich prompt with few-shot examples
    if table_name in enhanced_schema and enhanced_schema[table_name].get('columns'):
        # Build schema with types and samples
        schema_parts = []
        for col_name, col_info in enhanced_schema[table_name]['columns'].items():
            quoted_col = quote_identifier(col_name)
            col_type = col_info.get('type', 'text')
            samples = col_info.get('samples', [])
            sample_str = f" (e.g. {', '.join(samples[:2])})" if samples else ""
            schema_parts.append(f"{quoted_col} {col_type}{sample_str}")
        schema_detail = ', '.join(schema_parts)
    else:
        # Fallback to simple column list
        schema_detail = ', '.join([quote_identifier(col) for col in columns])
    
    # Build dynamic examples using ACTUAL columns from schema
    example_column = columns[0] if columns else "id"  # Use first actual column
    example_column_quoted = quote_identifier(example_column)
    
    # Find a numeric column for comparison examples
    numeric_col = None
    if table_name in enhanced_schema and enhanced_schema[table_name].get('columns'):
        for col_name, col_info in enhanced_schema[table_name]['columns'].items():
            if col_info.get('type', '').lower() in ['integer', 'real', 'numeric', 'decimal', 'float']:
                numeric_col = col_name
                break
    if not numeric_col and len(columns) > 1:
        numeric_col = columns[1]  # Fallback to second column
    numeric_col_quoted = quote_identifier(numeric_col) if numeric_col else example_column_quoted
    
    # Build multi-table schema info with relationships
    all_tables_schema = ""
    join_examples = ""
    
    if len(table_names) > 1:
        all_tables_schema = "\n\nAvailable Tables:\n"
        for tbl in table_names:
            tbl_cols = all_columns.get(tbl, [])
            all_tables_schema += f"- {quote_identifier(tbl)}: {', '.join([quote_identifier(c) for c in tbl_cols])}\n"
        
        # Add FK relationships with JOIN examples
        if foreign_keys:
            all_tables_schema += "\nTable Relationships:\n"
            for tbl, fk_list in foreign_keys.items():
                if fk_list:
                    for fk in fk_list:
                        from_col = quote_identifier(fk['from_column'])
                        to_table = quote_identifier(fk['to_table'])
                        to_col = quote_identifier(fk.get('to_column', 'id'))
                        all_tables_schema += f"- {quote_identifier(tbl)}.{from_col} → {to_table}.{to_col}\n"
                        
                        # Build JOIN example using actual FK
                        if tbl == table_name or (related_tables and tbl in related_tables):
                            join_examples += f"\nQ: Show {tbl} with {to_table} details\n"
                            join_examples += f"A: SELECT * FROM {quote_identifier(tbl)} JOIN {to_table} ON {quote_identifier(tbl)}.{from_col} = {to_table}.{to_col}\n"
    
    # Build conversation context from history (last up to 5 turns)
    history_str = ""
    if history:
        ctx = []
        for turn in history[-5:]:
            q = turn.get('question', '').strip()
            a = turn.get('answer', '').strip()
            if q:
                ctx.append(f"Q: {q}")
            if a:
                ctx.append(f"A: {a}")
        if ctx:
            history_str = "\n\nConversation Context:\n" + "\n".join(ctx)

    # Few-shot prompt with ACTUAL schema-based examples (including JOINs)
    prompt = f"""Generate SQLite query using the exact table and column names provided.

IMPORTANT: Use table and column names EXACTLY as listed below. Never use the word "table" as a placeholder.

Primary Table: {quoted_table} has columns: {schema_detail}{all_tables_schema}

Examples with ACTUAL column names:
Q: Show all records
A: SELECT * FROM {quoted_table}

Q: Count by {example_column}
A: SELECT {example_column_quoted}, COUNT(*) FROM {quoted_table} GROUP BY {example_column_quoted}

Q: Total {numeric_col if numeric_col else example_column}
A: SELECT SUM({numeric_col_quoted}) FROM {quoted_table}

Q: Where {numeric_col if numeric_col else example_column} above 90
A: SELECT * FROM {quoted_table} WHERE {numeric_col_quoted} > 90{join_examples}

IMPORTANT: Use correct SQL syntax with parentheses for aggregations: SUM(column), AVG(column), COUNT(*).
Do NOT add WHERE clauses unless the question explicitly requests filtering.
For JOIN queries, use the relationships listed above to connect tables properly.

{history_str}

Question: {question}
SQL:"""
    
    try:
        inputs = tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_length=128,
                num_beams=4,
                early_stopping=True,
                temperature=0.2,
                do_sample=True,
                top_p=0.9,
                repetition_penalty=1.2
            )
        sql = tokenizer.decode(outputs[0], skip_special_tokens=True)
    except Exception as e:
        print(f"[AI GENERATE ERROR] {e}")
        # Safe fallback to avoid crashing the app
        return f"SELECT * FROM {quoted_table}"
    
    # Repair and validate the generated SQL
    sql = repair_sql(sql, table_name, columns, all_columns, is_multi_table_query)
    
    print(f"[GENERATED] {sql}")
    return sql

def explain_sql_query(sql: str, question: str, schema: Dict) -> str:
    """Convert SQL query to plain English explanation without revealing SQL code.
    Enhanced with detailed explanations for advanced features."""
    import re
    
    sql_upper = sql.upper()
    explanation_parts = []
    
    # Extract table names from schema
    table_names = list(schema.keys())
    
    # Detect JOIN types
    has_inner_join = 'INNER JOIN' in sql_upper or ('JOIN' in sql_upper and 'LEFT' not in sql_upper and 'RIGHT' not in sql_upper and 'FULL' not in sql_upper and 'CROSS' not in sql_upper)
    has_left_join = 'LEFT JOIN' in sql_upper
    has_right_join = 'RIGHT JOIN' in sql_upper
    has_full_join = 'FULL OUTER JOIN' in sql_upper or 'FULL JOIN' in sql_upper
    has_cross_join = 'CROSS JOIN' in sql_upper
    has_join = any([has_inner_join, has_left_join, has_right_join, has_full_join, has_cross_join])
    
    # Detect subqueries
    has_subquery = sql_upper.count('SELECT') > 1
    has_correlated_subquery = 'WHERE' in sql_upper and sql_upper.count('SELECT') > 1 and any(t.upper() + '.' in sql_upper for t in table_names)
    
    # Detect window functions
    has_window = any(func in sql_upper for func in ['ROW_NUMBER()', 'RANK()', 'DENSE_RANK()', 'LEAD(', 'LAG(', 'OVER ('])
    
    # Detect aggregations
    has_count = 'COUNT(' in sql_upper
    has_avg = 'AVG(' in sql_upper or 'AVERAGE' in sql_upper
    has_sum = 'SUM(' in sql_upper
    has_max = 'MAX(' in sql_upper
    has_min = 'MIN(' in sql_upper
    
    # Detect filtering
    has_where = 'WHERE' in sql_upper
    has_group_by = 'GROUP BY' in sql_upper
    has_having = 'HAVING' in sql_upper
    has_order_by = 'ORDER BY' in sql_upper
    has_limit = 'LIMIT' in sql_upper
    has_between = 'BETWEEN' in sql_upper
    has_case = 'CASE' in sql_upper and 'WHEN' in sql_upper
    has_in = ' IN (' in sql_upper and not has_subquery
    
    # Build explanation
    if has_join:
        # Multi-table query with JOIN type
        involved_tables = [t for t in table_names if t.lower() in sql.lower()]
        if len(involved_tables) >= 2:
            join_type_desc = ""
            if has_left_join:
                join_type_desc = " (including all records from the first table)"
            elif has_right_join:
                join_type_desc = " (including all records from the second table)"
            elif has_full_join:
                join_type_desc = " (including all records from both tables)"
            elif has_cross_join:
                join_type_desc = " (all combinations)"
            explanation_parts.append(f"This query combines data from {len(involved_tables)} related tables: {', '.join(involved_tables)}{join_type_desc}.")
    
    if has_subquery:
        if has_correlated_subquery:
            explanation_parts.append("It uses a correlated subquery to compare values within groups.")
        else:
            explanation_parts.append("It uses a subquery to filter or compare data.")
    
    if has_window:
        explanation_parts.append("It uses window functions to calculate values across rows within partitions.")
    
    if has_count:
        explanation_parts.append("It counts the number of matching records.")
    elif has_avg:
        explanation_parts.append("It calculates the average value.")
    elif has_sum:
        explanation_parts.append("It calculates the total sum.")
    elif has_max:
        explanation_parts.append("It finds the maximum value.")
    elif has_min:
        explanation_parts.append("It finds the minimum value.")
    else:
        explanation_parts.append("It retrieves the matching records.")
    
    if has_where:
        explanation_parts.append("Results are filtered based on your specified conditions.")
    
    if has_group_by:
        explanation_parts.append("Data is grouped and aggregated by categories.")
    
    if has_having:
        explanation_parts.append("Groups are filtered based on aggregate conditions.")
    
    if has_between:
        explanation_parts.append("Results are filtered using a range condition.")
    
    if has_case:
        explanation_parts.append("Data is categorized using conditional logic.")
    
    if has_in:
        explanation_parts.append("Results are filtered to match a list of values.")
    
    if has_order_by:
        explanation_parts.append("Results are sorted in a specific order.")
    
    if has_limit:
        # Extract limit number
        limit_match = re.search(r'LIMIT\s+(\d+)', sql_upper)
        if limit_match:
            limit_num = limit_match.group(1)
            explanation_parts.append(f"Only the top {limit_num} results are shown.")
    
    # Combine explanation
    if explanation_parts:
        return " ".join(explanation_parts)
    else:
        return "This query retrieves data from your database based on your question."

def sanitize_error_message(error_msg: str) -> str:
    """Remove SQL query content from error messages to keep queries hidden from users."""
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

def execute_sql(sql: str, db_path: str) -> Tuple[pd.DataFrame, Optional[str]]:
    sql_clean = sql.strip().upper()
    
    dangerous_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 
                          'TRUNCATE', 'REPLACE', 'PRAGMA', 'ATTACH', 'DETACH']
    
    for keyword in dangerous_keywords:
        if keyword in sql_clean:
            return None, f"Error: {keyword} statements are not allowed for safety reasons. Only read-only queries (SELECT, WITH) are permitted."
    
    if not (sql_clean.startswith("SELECT") or sql_clean.startswith("WITH")):
        return None, "Error: Only SELECT and WITH (CTE) queries are allowed for safety reasons."
    
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(sql, conn)
        conn.close()
        return df, None
    except Exception as e:
        sanitized_error = sanitize_error_message(str(e))
        return None, sanitized_error

def generate_summary(df: pd.DataFrame, question: str, tokenizer, model) -> str:
    if df.empty:
        return "No results found."
    
    if len(df) > 10:
        sample_data = df.head(10)
        suffix = f"... and {len(df) - 10} more rows"
    else:
        sample_data = df
        suffix = ""
    
    data_text = f"Question: {question}\nResults: {len(df)} rows found.\n"
    data_text += sample_data.to_string(index=False)
    if suffix:
        data_text += f"\n{suffix}"
    
    prompt = f"Summarize the following query results in natural language:\n{data_text[:500]}\n\nSummary:"
    
    inputs = tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_length=100,
            num_beams=2,
            early_stopping=True
        )
    
    summary = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return summary

def create_schema_graph(schema: Dict, db_path: str):
    """Create an interactive graph visualization of database schema with relationships"""
    import plotly.graph_objects as go
    
    # Detect foreign keys
    fk_relationships = detect_foreign_keys(db_path)
    
    if not schema:
        st.warning("No schema available for visualization")
        return
    
    # Create nodes (tables) and edges (relationships)
    tables = list(schema.keys())
    num_tables = len(tables)
    
    if num_tables == 0:
        return
    
    # Position tables in a circle
    import math
    angle_step = 2 * math.pi / num_tables
    radius = max(2, num_tables * 0.5)
    
    node_x = []
    node_y = []
    node_text = []
    node_hover = []
    
    for i, table in enumerate(tables):
        angle = i * angle_step
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        node_x.append(x)
        node_y.append(y)
        node_text.append(table)
        
        # Hover info with column details
        columns = schema[table]
        hover_info = f"<b>{table}</b><br>"
        hover_info += f"Columns: {len(columns)}<br>"
        hover_info += "<br>".join(columns[:10])  # Show first 10 columns
        if len(columns) > 10:
            hover_info += f"<br>... and {len(columns) - 10} more"
        node_hover.append(hover_info)
    
    # Create edges for relationships
    edge_x = []
    edge_y = []
    edge_labels = []
    
    # fk_relationships is a dict: {table_name: [{'from_column': ..., 'to_table': ..., 'to_column': ...}]}
    for from_table, fk_list in fk_relationships.items():
        if from_table not in tables:
            continue
        for fk in fk_list:
            to_table = fk.get('to_table')
            from_col = fk.get('from_column')
            to_col = fk.get('to_column')
            
            if to_table and to_table in tables:
                from_idx = tables.index(from_table)
                to_idx = tables.index(to_table)
                
                edge_x.extend([node_x[from_idx], node_x[to_idx], None])
                edge_y.extend([node_y[from_idx], node_y[to_idx], None])
                edge_labels.append(f"{from_col} → {to_col}")
    
    # Create figure
    fig = go.Figure()
    
    # Add edges
    if edge_x:
        fig.add_trace(go.Scatter(
            x=edge_x, y=edge_y,
            mode='lines',
            line=dict(width=2, color='#888'),
            hoverinfo='none',
            showlegend=False
        ))
    
    # Add nodes
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        marker=dict(
            size=30,
            color='#1f77b4',
            line=dict(width=2, color='white')
        ),
        text=node_text,
        textposition="bottom center",
        hovertext=node_hover,
        hoverinfo='text',
        showlegend=False
    ))
    
    # Update layout
    fig.update_layout(
        title=dict(
            text=f"Database Schema: {num_tables} table(s), {len(fk_relationships)} relationship(s)",
            font=dict(size=16)
        ),
        showlegend=False,
        hovermode='closest',
        margin=dict(b=20, l=5, r=5, t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=400,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Show relationship details
    if fk_relationships:
        with st.expander("🔗 Relationship Details"):
            for from_table, fk_list in fk_relationships.items():
                for fk in fk_list:
                    to_table = fk.get('to_table')
                    from_col = fk.get('from_column')
                    to_col = fk.get('to_column')
                    if to_table:
                        st.caption(f"• `{from_table}.{from_col}` → `{to_table}.{to_col}`")

def create_visualizations(df: pd.DataFrame):
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
    
    if len(numeric_cols) == 0:
        st.info("No numeric columns available for visualization.")
        return
    
    st.subheader("📊 Data Visualizations")
    
    if len(numeric_cols) >= 2:
        col1, col2 = st.columns(2)
        
        with col1:
            x_axis = st.selectbox("Select X-axis", df.columns.tolist(), key="x_axis")
            y_axis = st.selectbox("Select Y-axis", numeric_cols, key="y_axis")
        
        with col2:
            chart_type = st.selectbox("Chart Type", ["Bar", "Line", "Scatter"], key="chart_type")
        
        if chart_type == "Bar":
            fig = px.bar(df, x=x_axis, y=y_axis, title=f"{y_axis} by {x_axis}")
        elif chart_type == "Line":
            fig = px.line(df, x=x_axis, y=y_axis, title=f"{y_axis} over {x_axis}")
        else:
            fig = px.scatter(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis}")
        
        st.plotly_chart(fig, use_container_width=True)
    
    elif len(numeric_cols) == 1:
        fig = px.histogram(df, x=numeric_cols[0], title=f"Distribution of {numeric_cols[0]}")
        st.plotly_chart(fig, use_container_width=True)

def show_login_page():
    render_app_header("Welcome to AskDB", "Sign in to access your AI-powered SQL assistant")
    
    tab1, tab2 = st.tabs(["Sign In", "Sign Up"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign In")
            
            if submit:
                if not username or not password:
                    st.error("Please enter both username and password")
                else:
                    try:
                        user = database.authenticate_user(username, password)
                        if user:
                            st.session_state.user_id = user.id
                            st.session_state.username = user.username
                            st.session_state.display_name = user.display_name
                            st.session_state.current_chat_id = None
                            st.success(f"Welcome back, {user.display_name}!")
                            st.rerun()
                        else:
                            st.error("Invalid username or password")
                    except Exception as e:
                        st.error("Login failed. Please try again or contact the administrator.")
                        print(f"Login error: {e}")
    
    with tab2:
        with st.form("signup_form"):
            new_username = st.text_input("Username*")
            new_email = st.text_input("Email*")
            new_display_name = st.text_input("Display Name (optional)")
            new_password = st.text_input("Password*", type="password")
            confirm_password = st.text_input("Confirm Password*", type="password")
            signup_submit = st.form_submit_button("Sign Up")
            
            if signup_submit:
                if not new_username or not new_email or not new_password:
                    st.error("Please fill in all required fields")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters long")
                else:
                    try:
                        user = database.create_user(
                            username=new_username,
                            email=new_email,
                            password=new_password,
                            display_name=new_display_name or new_username
                        )
                        if user:
                            st.success("✅ Account created successfully! Please sign in.")
                        else:
                            st.error("Username or email already exists")
                    except Exception as e:
                        st.error("Signup failed. Please try again or contact the administrator.")
                        print(f"Signup error: {e}")


def main():
    # Initialize database with graceful error handling - NEVER stop execution
    db_initialized = False
    try:
        db_initialized = database.init_db()
        if db_initialized:
            # Success - continue silently
            pass
        else:
            # Failed but continue with fallback
            st.warning("⚠️ Database connection failed. Using SQLite fallback mode.")
    except Exception as e:
        # Error but continue anyway
        st.warning(f"⚠️ Database initialization error: {str(e)}")
        st.info("💡 Continuing with SQLite fallback mode.")
        print(f"Database init error: {e}")
        # Try fallback
        try:
            db_initialized = database.init_db()
        except:
            pass
    
    # Initialize session state for authentication - ALWAYS continue
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'current_chat_id' not in st.session_state:
        st.session_state.current_chat_id = None
    
    # Show login page if not authenticated - ALWAYS render something
    if not st.session_state.user_id:
        try:
            show_login_page()
        except Exception as e:
            # Fallback if login page fails
            st.error(f"Error loading login page: {str(e)}")
            st.info("Please refresh the page or check the console for errors.")
            print(f"Login page error: {e}")
        return
    
    # User is authenticated - show main app
    render_app_header("AskDB", f"Welcome, {st.session_state.get('display_name', st.session_state.username)}! Ask questions in natural language and get instant SQL results.")
    top_chat_placeholder = st.empty()
    # Quick navigation: always provide a way to open the chat view
    nav_cols = st.columns([1, 1, 6])
    with nav_cols[0]:
        if st.button("📂 Open Chat View", use_container_width=True):
            st.session_state.open_chat_now = True
            st.rerun()
    
    # Initialize session state
    if 'db_path' not in st.session_state:
        st.session_state.db_path = None
    if 'schema' not in st.session_state:
        st.session_state.schema = None
    if 'query_history' not in st.session_state:
        st.session_state.query_history = []
    if 'upload_history' not in st.session_state:
        st.session_state.upload_history = []
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    with st.sidebar:
        # Chat Management Section
        st.header("💬 Chat Management")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ New Chat", use_container_width=True):
                # Create new chat
                chat = database.create_chat(st.session_state.user_id, "New Conversation")
                if chat:
                    st.session_state.current_chat_id = chat.id
                    st.session_state.chat_history = []
                    st.session_state.open_chat_now = True
                    st.success("New chat created!")
                    st.rerun()
        
        with col2:
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.user_id = None
                st.session_state.username = None
                st.session_state.current_chat_id = None
                st.rerun()
        
        # Show existing chats with improved navigation
        user_chats = database.get_user_chats(st.session_state.user_id)
        if user_chats:
            st.subheader("Your Chats")
            with st.expander("Browse Chats", expanded=True):
                chat_options = { (c.title if c.title != "New Conversation" else f"Chat {c.id}") : c.id for c in user_chats }
                selected_title = st.selectbox("Select a chat", list(chat_options.keys()), key="select_chat", index=0)
                if st.button("Open Selected Chat", use_container_width=True):
                    st.session_state.current_chat_id = chat_options[selected_title]
                    messages = database.get_chat_messages(st.session_state.current_chat_id)
                    st.session_state.chat_history = []
                    pending_user = None
                    for msg in messages:
                        if msg.role == 'user':
                            pending_user = msg
                            continue
                        if msg.role == 'assistant':
                            question_text = pending_user.content if pending_user else ""
                            st.session_state.chat_history.append({
                                'timestamp': msg.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                                'question': question_text,
                                'answer': msg.content,
                                'rows': msg.rows_returned,
                                'success': msg.success == 1
                            })
                            pending_user = None
                    if pending_user is not None:
                        st.session_state.chat_history.append({
                            'timestamp': pending_user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                            'question': pending_user.content,
                            'answer': "",
                            'rows': 0,
                            'success': True
                        })
                    st.session_state.open_chat_now = True
                    st.rerun()
            # Quick buttons (last 10)
            for chat in user_chats[:10]:
                chat_title = chat.title if chat.title != "New Conversation" else f"Chat {chat.id}"
                is_current = chat.id == st.session_state.current_chat_id
                button_label = f"{'▶ ' if is_current else ''}{chat_title[:30]}"
                if st.button(button_label, key=f"chat_btn_{chat.id}", use_container_width=True):
                    st.session_state.current_chat_id = chat.id
                    messages = database.get_chat_messages(chat.id)
                    st.session_state.chat_history = []
                    pending_user = None
                    for msg in messages:
                        if msg.role == 'user':
                            pending_user = msg
                            continue
                        if msg.role == 'assistant':
                            question_text = pending_user.content if pending_user else ""
                            st.session_state.chat_history.append({
                                'timestamp': msg.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                                'question': question_text,
                                'answer': msg.content,
                                'rows': msg.rows_returned,
                                'success': msg.success == 1
                            })
                            pending_user = None
                    if pending_user is not None:
                        st.session_state.chat_history.append({
                            'timestamp': pending_user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                            'question': pending_user.content,
                            'answer': "",
                            'rows': 0,
                            'success': True
                        })
                    st.session_state.open_chat_now = True
                    st.rerun()
        else:
            st.info("No chats yet. Click 'New Chat' to start!")
        
        st.divider()
        
        st.header("📁 Database Upload")
        
        uploaded_files = st.file_uploader(
            "Upload your database files (multiple files supported for related tables)",
            type=['csv', 'xls', 'xlsx', 'db', 'sqlite', 'sqlite3'],
            help="Upload CSV, Excel (XLS/XLSX), or SQLite databases. You can upload multiple files to create related tables.",
            accept_multiple_files=True
        )
        
        if uploaded_files:
            import datetime
            temp_dir = tempfile.gettempdir()
            db_path = os.path.join(temp_dir, "uploaded_db.sqlite")
            
            # Remove existing database to start fresh
            if os.path.exists(db_path):
                os.remove(db_path)
            
            # Create new database
            conn = sqlite3.connect(db_path)
            tables_created = []
            
            # Process each uploaded file
            for uploaded_file in uploaded_files:
                file_ext = uploaded_file.name.split('.')[-1].lower()
                
                if file_ext in ['csv', 'xls', 'xlsx']:
                    # Convert CSV or Excel to SQLite table
                    if file_ext == 'csv':
                        df = pd.read_csv(uploaded_file)
                        file_type = "CSV"
                    elif file_ext in ['xls', 'xlsx']:
                        df = pd.read_excel(uploaded_file, engine='openpyxl' if file_ext == 'xlsx' else 'xlrd')
                        file_type = "Excel"
                    
                    # Clean table name
                    table_name = uploaded_file.name.rsplit('.', 1)[0]  # Remove extension
                    table_name = table_name.replace(' ', '_').replace('-', '_').replace('.', '_')
                    
                    # Add table to database
                    df.to_sql(table_name, conn, if_exists='replace', index=False)
                    tables_created.append({
                        'name': table_name,
                        'filename': uploaded_file.name,
                        'type': file_type,
                        'rows': len(df),
                        'columns': list(df.columns)
                    })
                
                elif file_ext in ['db', 'sqlite', 'sqlite3']:
                    # For SQLite files, copy tables to main database
                    temp_sqlite_path = os.path.join(temp_dir, uploaded_file.name)
                    with open(temp_sqlite_path, 'wb') as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Attach and copy tables
                    cursor = conn.cursor()
                    cursor.execute(f"ATTACH DATABASE '{temp_sqlite_path}' AS source_db")
                    
                    cursor.execute("SELECT name FROM source_db.sqlite_master WHERE type='table'")
                    source_tables = cursor.fetchall()
                    
                    for table in source_tables:
                        table_name = table[0]
                        quoted_table = quote_identifier(table_name)
                        
                        try:
                            # Copy table structure and data
                            cursor.execute(f"CREATE TABLE IF NOT EXISTS {quoted_table} AS SELECT * FROM source_db.{quoted_table}")
                            
                            cursor.execute(f"SELECT COUNT(*) FROM {quoted_table}")
                            row_count = cursor.fetchone()[0]
                            
                            cursor.execute(f"PRAGMA table_info({quoted_table})")
                            cols = cursor.fetchall()
                            col_names = [col[1] for col in cols]
                            
                            tables_created.append({
                                'name': table_name,
                                'filename': uploaded_file.name,
                                'type': 'SQLite',
                                'rows': row_count,
                                'columns': col_names
                            })
                        except Exception as e:
                            st.warning(f"Could not import table '{table_name}': {str(e)}")
                    
                    cursor.execute("DETACH DATABASE source_db")
                    conn.commit()
            
            conn.close()
            
            # Update session state
            st.session_state.db_path = db_path
            st.session_state.schema = extract_schema(db_path)

            # Auto-create a chat on upload and open it
            if st.session_state.user_id:
                try:
                    default_title = f"Upload: {tables_created[0]['name']}" if tables_created else "New Conversation"
                    chat = database.create_chat(st.session_state.user_id, default_title)
                    if chat:
                        st.session_state.current_chat_id = chat.id
                        st.session_state.chat_history = []
                        st.session_state.open_chat_now = True
                except Exception:
                    pass
            
            # Add to upload history
            for table_info in tables_created:
                upload_entry = {
                    'filename': table_info['filename'],
                    'type': table_info['type'],
                    'table': table_info['name'],
                    'rows': table_info['rows'],
                    'columns': table_info['columns'],
                    'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                st.session_state.upload_history.append(upload_entry)
            
            # Success message
            if len(tables_created) == 1:
                st.success(f"✅ Uploaded 1 table: `{tables_created[0]['name']}`")
            else:
                table_names = ', '.join([f"`{t['name']}`" for t in tables_created])
                st.success(f"✅ Uploaded {len(tables_created)} tables: {table_names}")
        
        # Upload History
        if st.session_state.upload_history:
            st.subheader("📂 Upload History")
            for upload in reversed(st.session_state.upload_history[-5:]):  # Show last 5
                with st.expander(f"📄 {upload['filename']}", expanded=False):
                    st.write(f"**Type:** {upload['type']}")
                    st.write(f"**Time:** {upload['timestamp']}")
                    if 'rows' in upload:
                        st.write(f"**Rows:** {upload['rows']}")
                    if 'columns' in upload:
                        st.write(f"**Columns:** {len(upload['columns'])}")
        
        if st.session_state.schema:
            st.subheader("📋 Database Schema")
            
            # Visual schema graph
            if len(st.session_state.schema) > 1:
                with st.expander("🗺️ Visual Schema Graph", expanded=True):
                    create_schema_graph(st.session_state.schema, st.session_state.db_path)
            
            # Table details
            for table_name, columns in st.session_state.schema.items():
                with st.expander(f"📊 Table: {table_name}"):
                    st.code(f"{table_name}(\n  " + ",\n  ".join(columns) + "\n)")
    
    if st.session_state.db_path is None:
        st.info("👈 Please upload a database (CSV or SQLite) from the sidebar to get started.")
        
        st.markdown("### ✨ Features")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            render_feature_card("AI-Powered SQL Generation", "Convert natural language questions to SQL using advanced T5 models with template fallback", "🤖")
        
        with col2:
            render_feature_card("Safe Query Execution", "Read-only queries with automatic validation. Your data is always protected.", "🔒")
        
        with col3:
            render_feature_card("Auto Visualizations", "Automatic chart generation for numeric data with interactive Plotly charts", "📊")
        
        col4, col5, col6 = st.columns(3)
        with col4:
            render_feature_card("Multi-Table JOINs", "Intelligent foreign key detection and automatic JOIN generation across related tables", "🔗")
        with col5:
            render_feature_card("Advanced SQL", "Support for HAVING clauses, complex ORDER BY, GROUP BY, and aggregations", "⚡")
        with col6:
            render_feature_card("Natural Summaries", "AI-generated plain English explanations of your query results", "💡")
        
        st.markdown("### 📝 Example Questions")
        st.markdown("**📊 For any database (orders, customers, products, etc.):**")
        st.code("""
• Show all records
• Get average price by category
• Count orders by customer
• Show customers where total > 1000
• List products with price less than 50
• Average revenue by month
• Top 10 highest sales
        """)
        # Do not return here; allow chat view to render even without a database
    
    if st.session_state.db_path is not None:
        if st.session_state.schema:
            st.success(f"🗄️ Database loaded with {len(st.session_state.schema)} table(s)")
        else:
            st.error("Database uploaded but schema could not be extracted")
    
    # Auto-open chat view when triggered by sidebar actions or upload - render at top
    if st.session_state.get('open_chat_now'):
        with top_chat_placeholder.container():
            st.subheader("💭 Chat History")
            if not st.session_state.chat_history:
                st.info("No messages in this chat yet. Ask a question to start.")
            else:
                for idx, chat in enumerate(reversed(st.session_state.chat_history)):
                    with st.container():
                        st.markdown(f"**🕐 {chat['timestamp']}**")
                        st.markdown(f"**👤 You:** {chat['question']}")
                        if chat.get('answer'):
                            st.markdown(f"**🤖 AskDB:** {chat['answer']}")
                        if chat.get('rows'):
                            st.caption(f"✅ Found {chat['rows']} rows")
                        if chat.get('result_preview'):
                            with st.expander("View result preview"):
                                preview_df = pd.DataFrame(chat['result_preview'])
                                st.dataframe(preview_df, use_container_width=True)
                        st.divider()
                # Continue this chat input
                st.markdown("**Continue this chat**")
                follow_up = st.text_input("Ask a follow-up question:", key="follow_up_top")
                send_follow_up = st.button("Send to this chat", key="send_follow_up_top")
                if send_follow_up and follow_up:
                    with st.spinner("🤖 Loading AI model..."):
                        nl2sql_tokenizer, nl2sql_model = get_nl2sql()
                    schema_str = format_schema_for_model(st.session_state.schema) if st.session_state.schema else ""
                    history_turns = []
                    for turn in st.session_state.chat_history[-5:]:
                        history_turns.append({'question': turn.get('question',''), 'answer': turn.get('answer','')})
                    with st.spinner("🧠 Generating SQL query..."):
                        try:
                            sql = core_generate_sql(follow_up, schema_str, nl2sql_tokenizer, nl2sql_model, st.session_state.db_path, history=history_turns)
                        except Exception as e:
                            st.error(f"Generation error: {e}")
                            sql = None
                with st.spinner("⚙️ Executing query..."):
                    df, error = execute_sql(sql, st.session_state.db_path) if sql else (None, "SQL not generated")
                    import datetime
                    if error:
                        st.error(error)
                        if st.session_state.current_chat_id:
                            database.add_message(st.session_state.current_chat_id, "user", follow_up)
                            database.add_message(st.session_state.current_chat_id, "assistant", f"Error: {error}", sql_query=sql, rows_returned=0, success=False)
                        st.session_state.chat_history.append({
                            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'question': follow_up,
                            'answer': f"Error: {error}",
                            'rows': 0,
                            'success': False
                        })
                    else:
                        st.success(f"✅ Query executed successfully! Found {len(df)} rows.")
                        explanation = explain_sql_query(sql, follow_up, st.session_state.schema) if st.session_state.schema else "Query executed"
                        st.info(explanation)
                        st.dataframe(df, use_container_width=True)
                        if st.session_state.current_chat_id:
                            database.add_message(st.session_state.current_chat_id, "user", follow_up)
                            database.add_message(st.session_state.current_chat_id, "assistant", explanation if not df.empty else "Query executed successfully", sql_query=sql, rows_returned=len(df), success=True)
                        st.session_state.chat_history.append({
                            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'question': follow_up,
                            'answer': explanation if not df.empty else "Query executed successfully",
                            'rows': len(df),
                            'success': True,
                            'result_preview': df.head(3).to_dict('records') if not df.empty else []
                        })
        st.session_state.open_chat_now = False

    tab1, tab2, tab3 = st.tabs(["💬 Ask a Question", "💭 Chat History", "📜 Query History"])
    
    with tab1:
        st.subheader("Ask Your Question")
        
        question = st.text_input(
            "Enter your question in natural language:",
            placeholder="e.g., Show me all records where score is greater than 90",
            key="nl_question"
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            generate_button = st.button("🚀 Generate & Run SQL", type="primary", use_container_width=True)
        continue_toggle = st.checkbox("Continue current chat context", value=bool(st.session_state.get('continue_chat_mode')), help="Use last chat turns for context")
        
        if generate_button and question:
            with st.spinner("🤖 Loading AI model..."):
                nl2sql_tokenizer, nl2sql_model = get_nl2sql()
            
            schema_str = format_schema_for_model(st.session_state.schema) if st.session_state.schema else ""
            history_turns = []
            if continue_toggle and st.session_state.chat_history:
                for turn in st.session_state.chat_history[-5:]:
                    history_turns.append({'question': turn.get('question',''), 'answer': turn.get('answer','')})
            
            with st.spinner("🧠 Generating SQL query..."):
                try:
                    sql = core_generate_sql(question, schema_str, nl2sql_tokenizer, nl2sql_model, st.session_state.db_path, history=history_turns)
                except Exception as e:
                    st.error(f"Generation error: {e}")
                    sql = None
            
            with st.spinner("⚙️ Executing query..."):
                df, error = execute_sql(sql, st.session_state.db_path) if sql else (None, "SQL not generated")
            
            if error:
                st.error(error)
                st.session_state.query_history.append({
                    'question': question,
                    'sql': sql,
                    'rows': 0,
                    'success': False,
                    'error': error
                })
                
                # Add to chat history
                import datetime
                
                # Create chat if none exists
                if not st.session_state.current_chat_id:
                    chat = database.create_chat(st.session_state.user_id, question[:100])
                    if chat:
                        st.session_state.current_chat_id = chat.id
                
                # Save to database
                if st.session_state.current_chat_id:
                    database.add_message(st.session_state.current_chat_id, "user", question)
                    database.add_message(
                        st.session_state.current_chat_id, 
                        "assistant", 
                        f"Error: {error}",
                        sql_query=sql,
                        rows_returned=0,
                        success=False
                    )
                
                st.session_state.chat_history.append({
                    'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'question': question,
                    'answer': f"Error: {error}",
                    'rows': 0,
                    'success': False
                })
            elif df is not None:
                st.success(f"✅ Query executed successfully! Found {len(df)} rows.")
                
                # Show query explanation (without revealing SQL)
                explanation = explain_sql_query(sql, question, st.session_state.schema)
                st.subheader("🔍 What This Query Does")
                st.info(explanation)
                
                # Display stats
                col1, col2, col3 = st.columns(3)
                with col1:
                    render_stat_card(str(len(df)), "Rows Returned")
                with col2:
                    render_stat_card(str(len(df.columns)), "Columns")
                with col3:
                    render_stat_card("✅", "Status")
                
                st.subheader("📋 Query Results")
                st.dataframe(df, use_container_width=True)
                
                # CSV Download
                if not df.empty:
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Results as CSV",
                        data=csv,
                        file_name=f"query_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        type="primary"
                    )
                
                if not df.empty:
                    create_visualizations(df)
                    
                    with st.spinner("📝 Generating natural language summary..."):
                        summary_tokenizer, summary_model = get_summarizer()
                        summary = generate_summary(df, question, summary_tokenizer, summary_model)
                    
                    st.subheader("💡 Summary")
                    st.info(summary)
                
                st.session_state.query_history.append({
                    'question': question,
                    'sql': sql,
                    'rows': len(df),
                    'success': True
                })
                
                # Add to chat history
                import datetime
                
                # Create chat if none exists
                if not st.session_state.current_chat_id:
                    chat = database.create_chat(st.session_state.user_id, question[:100])
                    if chat:
                        st.session_state.current_chat_id = chat.id
                
                # Save to database
                if st.session_state.current_chat_id:
                    database.add_message(st.session_state.current_chat_id, "user", question)
                    database.add_message(
                        st.session_state.current_chat_id,
                        "assistant",
                        summary if not df.empty else "Query executed successfully",
                        sql_query=sql,
                        rows_returned=len(df),
                        success=True
                    )
                
                st.session_state.chat_history.append({
                    'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'question': question,
                    'answer': summary if not df.empty else "Query executed successfully",
                    'rows': len(df),
                    'success': True,
                    'result_preview': df.head(3).to_dict('records') if not df.empty else []
                })
    
    with tab2:
        st.subheader("💭 Chat History")
        
        if not st.session_state.chat_history:
            if st.session_state.current_chat_id:
                st.info("No messages in this chat yet. Ask a question to start.")
            else:
                st.info("No conversations yet. Ask a question to start chatting!")
        else:
            for idx, chat in enumerate(reversed(st.session_state.chat_history)):
                with st.container():
                    st.markdown(f"**🕐 {chat['timestamp']}**")
                    
                    # User question
                    st.markdown(f"**👤 You:** {chat['question']}")
                    
                    # System answer
                    if chat['success']:
                        st.markdown(f"**🤖 AskDB:** {chat['answer']}")
                        st.caption(f"✅ Found {chat['rows']} rows")
                        
                        # Show preview of results
                        if chat.get('result_preview'):
                            with st.expander("View result preview"):
                                preview_df = pd.DataFrame(chat['result_preview'])
                                st.dataframe(preview_df, use_container_width=True)
                    else:
                        st.markdown(f"**🤖 AskDB:** ❌ {chat['answer']}")
                    
                    st.divider()
    
    with tab3:
        st.subheader("Query History")
        
        if not st.session_state.query_history:
            st.info("No queries yet. Ask a question to get started!")
        else:
            for idx, query in enumerate(reversed(st.session_state.query_history)):
                with st.expander(f"Query #{len(st.session_state.query_history) - idx}: {query['question']}", expanded=False):
                    st.markdown(f"**Question:** {query['question']}")
                    
                    if query['success']:
                        st.success(f"✅ Success - {query['rows']} rows returned")
                    else:
                        st.error(f"❌ Failed - {query.get('error', 'Unknown error')}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Last resort error handling - show something instead of white screen
        st.error("⚠️ Application Error")
        st.exception(e)
        st.info("Please check the console for detailed error messages.")
        print(f"Fatal error in main(): {e}")
        import traceback
        traceback.print_exc()
