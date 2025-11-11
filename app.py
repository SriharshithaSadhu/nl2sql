import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import os
import tempfile
from typing import Dict, List, Tuple, Optional

st.set_page_config(
    page_title="AskDB - Natural Language to SQL",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    
    # COUNT queries
    if 'count' in q_lower and not any(word in q_lower for word in ['where', 'above', 'below']):
        if 'by' in q_lower or 'group' in q_lower:
            for col in columns:
                if col in q_lower:
                    quoted_col = quote_identifier(col)
                    return f"SELECT {quoted_col}, COUNT(*) as count FROM {quoted_table} GROUP BY {quoted_col}"
        return f"SELECT COUNT(*) as total FROM {quoted_table}"
    
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
    
    # PRIORITY 4: SHOW ALL queries (default)
    if any(word in q_lower for word in ['all', 'everything', 'show', 'list', 'display']) and \
       not any(word in q_lower for word in ['where', 'above', 'below', 'greater', 'less', 'average', 'count']):
        return f"SELECT * FROM {quoted_table}"
    
    return None

def repair_sql(sql: str, table_name: str, columns: List[str]) -> str:
    """Intelligently repair and validate AI-generated SQL"""
    import re
    
    quoted_table = quote_identifier(table_name)
    
    # Remove artifacts
    sql = sql.strip()
    for artifact in ['|', 'table:', 'Table:', 'CREATE TABLE', 'col =']:
        if artifact in sql:
            sql = sql.split(artifact)[0].strip()
    
    # Fix common table reference issues (but preserve already quoted ones)
    replacements = [
        ('FROM table ', f'FROM {quoted_table} '),
        ('FROM Table ', f'FROM {quoted_table} '),
    ]
    # Only replace unquoted table name
    if f'FROM {table_name}' in sql and f'FROM "{table_name}"' not in sql:
        sql = sql.replace(f'FROM {table_name}', f'FROM {quoted_table}')
    for old, new in replacements:
        sql = sql.replace(old, new)
    
    # Quote column names ONLY if they're not already quoted
    for col in columns:
        quoted_col = quote_identifier(col)
        
        # Skip if column is already quoted in SQL
        if quoted_col in sql or f'"{col}"' in sql:
            continue
        
        # Match bare (unquoted) column names in various SQL contexts
        # Use negative lookbehind/lookahead to avoid matching quoted identifiers
        patterns = [
            # SELECT column, WHERE column, etc. (not preceded/followed by quotes)
            (rf'(?<!["\w])({re.escape(col)})(?=\s*[,\s=<>)])', quoted_col),
            (rf'(?<!["\w])({re.escape(col)})(?=\s+FROM)', quoted_col),
            (rf'(?<!["\w])({re.escape(col)})$', quoted_col),
        ]
        for pattern, replacement in patterns:
            sql = re.sub(pattern, replacement, sql, flags=re.IGNORECASE)
    
    # Ensure it's a SELECT query
    if not sql.upper().startswith('SELECT') and not sql.upper().startswith('WITH'):
        sql = f"SELECT * FROM {quoted_table}"
    
    return sql

def generate_sql(question: str, schema_str: str, tokenizer, model, db_path: str = None) -> str:
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
    
    table_name = table_names[0]
    columns = all_columns.get(table_name, [])
    quoted_table = quote_identifier(table_name)
    
    # Fast-path: Try templates for common queries (with value-aware matching)
    template_sql = get_template_sql(question, table_name, columns, db_path)
    if template_sql:
        print(f"[TEMPLATE FAST-PATH] {question}")
        return template_sql
    
    # AI-first approach with enhanced prompting
    print(f"[AI-FIRST DYNAMIC] {question}")
    
    # Get enhanced schema with sample values if available
    enhanced_schema = {}
    if db_path:
        try:
            enhanced_schema = extract_enhanced_schema(db_path)
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
    
    # Few-shot prompt with examples
    prompt = f"""Generate SQLite query.

Table {quoted_table}: {schema_detail}

Examples:
Q: Show all records
A: SELECT * FROM {quoted_table}

Q: Count by category
A: SELECT category, COUNT(*) FROM {quoted_table} GROUP BY category

Q: Where score above 90
A: SELECT * FROM {quoted_table} WHERE score > 90

Question: {question}
SQL:"""
    
    inputs = tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_length=150,
            num_beams=5,
            early_stopping=True,
            temperature=0.2,
            do_sample=True,
            top_p=0.95,
            repetition_penalty=1.2
        )
    
    sql = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Repair and validate the generated SQL
    sql = repair_sql(sql, table_name, columns)
    
    print(f"[GENERATED] {sql}")
    return sql

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

def main():
    st.title("🗄️ AskDB - Natural Language to SQL Query System")
    st.markdown("Ask questions about your database in plain English and get SQL-powered answers!")
    
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
        st.header("📁 Database Upload")
        
        uploaded_file = st.file_uploader(
            "Upload your database",
            type=['csv', 'xls', 'xlsx', 'db', 'sqlite', 'sqlite3'],
            help="Upload a CSV, Excel (XLS/XLSX), or SQLite database"
        )
        
        if uploaded_file:
            file_ext = uploaded_file.name.split('.')[-1].lower()
            
            temp_dir = tempfile.gettempdir()
            
            if file_ext in ['csv', 'xls', 'xlsx']:
                # Convert CSV or Excel to SQLite
                if file_ext == 'csv':
                    st.info("Converting CSV to SQLite database...")
                    df = pd.read_csv(uploaded_file)
                    file_type = "CSV"
                elif file_ext in ['xls', 'xlsx']:
                    st.info("Converting Excel to SQLite database...")
                    df = pd.read_excel(uploaded_file, engine='openpyxl' if file_ext == 'xlsx' else 'xlrd')
                    file_type = "Excel"
                
                db_path = os.path.join(temp_dir, "uploaded_db.sqlite")
                
                if os.path.exists(db_path):
                    os.remove(db_path)
                
                conn = sqlite3.connect(db_path)
                
                # Clean table name
                table_name = uploaded_file.name.rsplit('.', 1)[0]  # Remove extension
                table_name = table_name.replace(' ', '_').replace('-', '_').replace('.', '_')
                df.to_sql(table_name, conn, if_exists='replace', index=False)
                conn.close()
                
                st.session_state.db_path = db_path
                st.session_state.schema = extract_schema(db_path)
                
                # Add to upload history
                import datetime
                upload_entry = {
                    'filename': uploaded_file.name,
                    'type': file_type,
                    'table': table_name,
                    'rows': len(df),
                    'columns': list(df.columns),
                    'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                st.session_state.upload_history.append(upload_entry)
                
                st.success(f"✅ {file_type} converted to database with table: `{table_name}`")
            
            else:
                db_path = os.path.join(temp_dir, uploaded_file.name)
                with open(db_path, 'wb') as f:
                    f.write(uploaded_file.getbuffer())
                
                st.session_state.db_path = db_path
                st.session_state.schema = extract_schema(db_path)
                
                # Add to upload history with complete metadata
                import datetime
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Calculate total rows across all tables with proper quoting
                total_rows = 0
                all_columns = []
                for table_name in st.session_state.schema.keys():
                    try:
                        # Properly quote table names to handle spaces and reserved words
                        quoted_table = quote_identifier(table_name)
                        cursor.execute(f"SELECT COUNT(*) FROM {quoted_table}")
                        table_rows = cursor.fetchone()[0]
                        total_rows += table_rows
                        all_columns.extend(st.session_state.schema[table_name])
                    except Exception as e:
                        # Log error but continue with other tables
                        st.warning(f"Could not count rows in table '{table_name}': {str(e)}")
                        all_columns.extend(st.session_state.schema[table_name])
                
                conn.close()
                
                upload_entry = {
                    'filename': uploaded_file.name,
                    'type': 'SQLite',
                    'rows': total_rows,
                    'columns': all_columns,
                    'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                st.session_state.upload_history.append(upload_entry)
                
                st.success("✅ Database uploaded successfully!")
        
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
            for table_name, columns in st.session_state.schema.items():
                with st.expander(f"📊 Table: {table_name}"):
                    st.code(f"{table_name}(\n  " + ",\n  ".join(columns) + "\n)")
    
    if st.session_state.db_path is None:
        st.info("👈 Please upload a database (CSV or SQLite) from the sidebar to get started.")
        
        st.markdown("### ✨ Features")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**🤖 AI-Powered SQL Generation**")
            st.write("Convert natural language questions to SQL using Hugging Face T5 models")
        
        with col2:
            st.markdown("**🔒 Safe Query Execution**")
            st.write("Only SELECT queries allowed to protect your data")
        
        with col3:
            st.markdown("**📊 Auto Visualizations**")
            st.write("Automatic chart generation for numeric data")
        
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
        return
    
    if st.session_state.schema:
        st.success(f"🗄️ Database loaded with {len(st.session_state.schema)} table(s)")
    else:
        st.error("Database uploaded but schema could not be extracted")
    
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
        
        if generate_button and question:
            with st.spinner("🤖 Loading AI model..."):
                nl2sql_tokenizer, nl2sql_model = load_nl2sql_model()
            
            schema_str = format_schema_for_model(st.session_state.schema)
            
            with st.spinner("🧠 Generating SQL query..."):
                # Pass db_path for enhanced schema with sample values
                sql = generate_sql(question, schema_str, nl2sql_tokenizer, nl2sql_model, st.session_state.db_path)
            
            with st.spinner("⚙️ Executing query..."):
                df, error = execute_sql(sql, st.session_state.db_path)
            
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
                st.session_state.chat_history.append({
                    'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'question': question,
                    'answer': f"Error: {error}",
                    'rows': 0,
                    'success': False
                })
            elif df is not None:
                st.success(f"✅ Query executed successfully! Found {len(df)} rows.")
                
                st.subheader("📋 Query Results")
                st.dataframe(df, use_container_width=True)
                
                if not df.empty:
                    create_visualizations(df)
                    
                    with st.spinner("📝 Generating natural language summary..."):
                        summary_tokenizer, summary_model = load_summarization_model()
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
    main()
