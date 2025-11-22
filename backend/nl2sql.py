"""
Natural Language to SQL Service
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional, Dict, List
import torch

# Import from existing core module
from core import (
    extract_schema,
    extract_enhanced_schema,
    detect_foreign_keys,
    format_schema_for_model,
    generate_sql,
    explain_sql_query
)


# Lazy load models
_nl2sql_tokenizer = None
_nl2sql_model = None
_loaded_model_name = None


def load_nl2sql_model(model_name: str = "mrm8488/t5-base-finetuned-wikiSQL"):
    """Load NL2SQL model lazily"""
    global _nl2sql_tokenizer, _nl2sql_model, _loaded_model_name
    
    if _loaded_model_name == model_name:
        return _nl2sql_tokenizer, _nl2sql_model
    
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    
    hf_token = os.environ.get('HUGGING_FACE_TOKEN', None)
    _nl2sql_tokenizer = AutoTokenizer.from_pretrained(model_name, token=hf_token)
    _nl2sql_model = AutoModelForSeq2SeqLM.from_pretrained(model_name, token=hf_token)
    _loaded_model_name = model_name
    
    # Set num threads to reduce instability
    try:
        torch.set_num_threads(1)
    except:
        pass
    
    return _nl2sql_tokenizer, _nl2sql_model


def generate_sql_from_nl(
    question: str,
    db_path: str,
    model_name: str = "mrm8488/t5-base-finetuned-wikiSQL",
    use_model: bool = True
) -> tuple:
    """
    Generate SQL from natural language question
    Returns: (sql, schema, error)
    """
    try:
        # Extract schema
        schema = extract_schema(db_path)
        if not schema:
            return None, None, "Could not extract database schema"
        
        schema_str = format_schema_for_model(schema)
        
        # Generate SQL
        if use_model:
            try:
                tokenizer, model = load_nl2sql_model(model_name)
                sql = generate_sql(question, schema_str, tokenizer, model, db_path)
            except Exception as e:
                print(f"Model generation failed: {e}. Falling back to templates.")
                # Fallback to template-only mode
                sql = generate_sql(question, schema_str, None, None, db_path)
        else:
            # Template-only mode
            sql = generate_sql(question, schema_str, None, None, db_path)
        
        return sql, schema, None
    
    except Exception as e:
        return None, None, str(e)


def get_query_explanation(sql: str, schema: Dict) -> str:
    """Get human-readable explanation of SQL query"""
    try:
        insights = explain_sql_query(sql, schema)
        # Convert dict to readable string
        parts = []
        if insights.get('tables'):
            parts.append(f"Tables: {', '.join(insights['tables'])}")
        if insights.get('aggregations'):
            parts.append(f"Operations: {', '.join(insights['aggregations'])}")
        if insights.get('has_join'):
            parts.append("Uses table joins")
        if insights.get('filters'):
            parts.append(f"Filtering: {len(insights['filters'])} condition(s)")
        if insights.get('group_by'):
            parts.append(f"Grouped by: {', '.join(insights['group_by'])}")
        if insights.get('order_by'):
            parts.append(f"Sorted by: {', '.join(insights['order_by'])}")
        if insights.get('limit'):
            parts.append(f"Limited to {insights['limit']} results")
        
        return ". ".join(parts) if parts else "Query executed successfully"
    except:
        return "Query explanation unavailable"


def get_database_schema(db_path: str) -> tuple:
    """
    Get database schema and relationships
    Returns: (schema, relationships, error)
    """
    try:
        schema = extract_schema(db_path)
        relationships = detect_foreign_keys(db_path)
        return schema, relationships, None
    except Exception as e:
        return None, None, str(e)
