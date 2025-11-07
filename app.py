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
def load_nl2sql_model(model_name: str = "cssupport/t5-small-awesome-text-to-sql"):
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
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    schema = {}
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        schema[table_name] = [col[1] for col in columns]
    
    conn.close()
    return schema

def format_schema_for_model(schema: Dict[str, List[str]]) -> str:
    schema_lines = []
    for table_name, columns in schema.items():
        column_list = ', '.join(columns)
        schema_lines.append(f"Table {table_name} has columns: {column_list}")
    schema_str = '\n'.join(schema_lines)
    return schema_str

def generate_sql(question: str, schema_str: str, tokenizer, model) -> str:
    prompt = f"Schema: {schema_str}\nQuestion: {question}\nSQL:"
    
    inputs = tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_length=128,
            num_beams=4,
            early_stopping=True
        )
    
    sql = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return sql

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
        return None, f"SQL Execution Error: {str(e)}"

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
    
    if 'db_path' not in st.session_state:
        st.session_state.db_path = None
    if 'schema' not in st.session_state:
        st.session_state.schema = None
    if 'query_history' not in st.session_state:
        st.session_state.query_history = []
    
    with st.sidebar:
        st.header("📁 Database Upload")
        
        uploaded_file = st.file_uploader(
            "Upload your database",
            type=['csv', 'db', 'sqlite', 'sqlite3'],
            help="Upload a CSV file or SQLite database"
        )
        
        if uploaded_file:
            file_ext = uploaded_file.name.split('.')[-1].lower()
            
            temp_dir = tempfile.gettempdir()
            
            if file_ext == 'csv':
                st.info("Converting CSV to SQLite database...")
                
                df = pd.read_csv(uploaded_file)
                
                db_path = os.path.join(temp_dir, "uploaded_db.sqlite")
                
                if os.path.exists(db_path):
                    os.remove(db_path)
                
                conn = sqlite3.connect(db_path)
                
                table_name = uploaded_file.name.replace('.csv', '').replace(' ', '_').replace('-', '_')
                df.to_sql(table_name, conn, if_exists='replace', index=False)
                conn.close()
                
                st.session_state.db_path = db_path
                st.session_state.schema = extract_schema(db_path)
                st.success(f"✅ CSV converted to database with table: `{table_name}`")
            
            else:
                db_path = os.path.join(temp_dir, uploaded_file.name)
                with open(db_path, 'wb') as f:
                    f.write(uploaded_file.getbuffer())
                
                st.session_state.db_path = db_path
                st.session_state.schema = extract_schema(db_path)
                st.success("✅ Database uploaded successfully!")
        
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
        st.code("""
• Show all records
• List the top 10 entries
• What is the average of column_name?
• Count records grouped by category
• Find all entries where value > 100
        """)
        return
    
    st.success(f"🗄️ Database loaded with {len(st.session_state.schema)} table(s)")
    
    tab1, tab2 = st.tabs(["💬 Ask a Question", "📜 Query History"])
    
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
                sql = generate_sql(question, schema_str, nl2sql_tokenizer, nl2sql_model)
            
            st.subheader("Generated SQL Query")
            st.code(sql, language="sql")
            
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
    
    with tab2:
        st.subheader("Query History")
        
        if not st.session_state.query_history:
            st.info("No queries yet. Ask a question to get started!")
        else:
            for idx, query in enumerate(reversed(st.session_state.query_history)):
                with st.expander(f"Query #{len(st.session_state.query_history) - idx}: {query['question']}", expanded=False):
                    st.markdown(f"**Question:** {query['question']}")
                    st.code(query['sql'], language="sql")
                    
                    if query['success']:
                        st.success(f"✅ Success - {query['rows']} rows returned")
                    else:
                        st.error(f"❌ Failed - {query.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()
