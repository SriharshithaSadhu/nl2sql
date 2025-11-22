"""
Advanced SQL Generation Module
Supports: Multiple JOIN types, Subqueries, Window Functions, Advanced Filtering
"""
import re
from typing import Dict, List, Optional, Tuple

# Import core functions locally to avoid circular imports
def _quote_identifier(name: str) -> str:
    """Properly quote SQL identifiers to handle spaces and reserved words"""
    return f'"{name.replace(chr(34), chr(34)+chr(34))}"'

def _extract_enhanced_schema(db_path: str):
    """Extract enhanced schema - imported locally when needed"""
    try:
        from core import extract_enhanced_schema
        return extract_enhanced_schema(db_path)
    except ImportError:
        return {}


def detect_join_type(question: str) -> str:
    """
    Detect JOIN type from natural language
    Returns: 'INNER', 'LEFT', 'RIGHT', 'FULL', 'CROSS'
    """
    q_lower = question.lower()
    
    # LEFT JOIN indicators
    if any(word in q_lower for word in ['all', 'including', 'even if', 'with or without', 'left join']):
        return 'LEFT'
    
    # RIGHT JOIN indicators
    if any(word in q_lower for word in ['right join', 'from right']):
        return 'RIGHT'
    
    # FULL OUTER JOIN indicators
    if any(word in q_lower for word in ['all from both', 'combine all', 'full outer', 'everything from']):
        return 'FULL'
    
    # CROSS JOIN indicators
    if any(word in q_lower for word in ['cross join', 'cartesian', 'all combinations', 'every combination']):
        return 'CROSS'
    
    # Default to INNER JOIN
    return 'INNER'


def build_join_clause(
    from_table: str,
    to_table: str,
    from_col: str,
    to_col: str,
    join_type: str = 'INNER',
    alias_from: str = None,
    alias_to: str = None
) -> str:
    """Build JOIN clause with specified type"""
    join_type_map = {
        'INNER': 'INNER JOIN',
        'LEFT': 'LEFT JOIN',
        'RIGHT': 'RIGHT JOIN',
        'FULL': 'FULL OUTER JOIN',
        'CROSS': 'CROSS JOIN'
    }
    
    join_keyword = join_type_map.get(join_type.upper(), 'INNER JOIN')
    from_alias = alias_from or _quote_identifier(from_table)
    to_alias = alias_to or _quote_identifier(to_table)
    
    if join_type == 'CROSS':
        return f"{join_keyword} {_quote_identifier(to_table)} {to_alias}"
    else:
        return (
            f"{join_keyword} {_quote_identifier(to_table)} {to_alias} "
            f"ON {from_alias}.{_quote_identifier(from_col)} = {to_alias}.{_quote_identifier(to_col)}"
        )


def detect_subquery_intent(question: str) -> Optional[Dict]:
    """
    Detect if question requires a subquery
    Returns: {'type': 'correlated'|'scalar'|'in'|'not_in', 'pattern': ...}
    """
    q_lower = question.lower()
    
    # Correlated subquery patterns
    if any(phrase in q_lower for phrase in [
        'more than the average', 'higher than average', 'above average',
        'more than their', 'higher than their', 'above their',
        'earn more than', 'score higher than'
    ]):
        return {'type': 'correlated', 'pattern': 'comparison_with_aggregate'}
    
    # IN subquery patterns
    if any(phrase in q_lower for phrase in [
        'who have', 'that have', 'which have',
        'in the list of', 'among those who'
    ]):
        return {'type': 'in', 'pattern': 'membership_check'}
    
    # NOT IN subquery patterns
    if any(phrase in q_lower for phrase in [
        'who do not have', 'that do not have', 'without',
        'not in the list', 'excluding those'
    ]):
        return {'type': 'not_in', 'pattern': 'exclusion_check'}
    
    # Scalar subquery patterns
    if any(phrase in q_lower for phrase in [
        'the average', 'the total', 'the maximum', 'the minimum',
        'the count of', 'the sum of'
    ]):
        return {'type': 'scalar', 'pattern': 'aggregate_value'}
    
    return None


def generate_subquery_sql(
    question: str,
    main_table: str,
    main_columns: List[str],
    subquery_table: str,
    subquery_columns: List[str],
    subquery_type: str,
    db_path: str = None
) -> Optional[str]:
    """Generate SQL with subquery"""
    q_lower = question.lower()
    quoted_main = _quote_identifier(main_table)
    
    if subquery_type == 'correlated':
        # Example: "employees who earn more than the average salary of their department"
        # Find the comparison column
        comparison_col = None
        for col in main_columns:
            if any(kw in col.lower() for kw in ['salary', 'score', 'price', 'amount']) and col.lower() in q_lower:
                comparison_col = col
                break
        
        if not comparison_col:
            comparison_col = main_columns[1] if len(main_columns) > 1 else main_columns[0]
        
        # Find grouping column (department, category, etc.)
        group_col = None
        for col in main_columns:
            if any(kw in col.lower() for kw in ['department', 'category', 'group', 'type']) and col.lower() in q_lower:
                group_col = col
                break
        
        if comparison_col and group_col:
            quoted_comp = _quote_identifier(comparison_col)
            quoted_group = _quote_identifier(group_col)
            
            # Detect comparison operator
            if any(word in q_lower for word in ['more than', 'greater than', 'above', 'higher than']):
                op = '>'
            elif any(word in q_lower for word in ['less than', 'below', 'lower than']):
                op = '<'
            else:
                op = '>'
            
            # Detect aggregation
            if 'average' in q_lower or 'avg' in q_lower:
                agg_func = 'AVG'
            elif 'total' in q_lower or 'sum' in q_lower:
                agg_func = 'SUM'
            elif 'maximum' in q_lower or 'max' in q_lower:
                agg_func = 'MAX'
            elif 'minimum' in q_lower or 'min' in q_lower:
                agg_func = 'MIN'
            else:
                agg_func = 'AVG'
            
            return (
                f"SELECT * FROM {quoted_main} t1 "
                f"WHERE t1.{quoted_comp} {op} ("
                f"SELECT {agg_func}(t2.{quoted_comp}) "
                f"FROM {quoted_main} t2 "
                f"WHERE t2.{quoted_group} = t1.{quoted_group}"
                f")"
            )
    
    elif subquery_type == 'in':
        # Example: "customers who have placed orders"
        # Find relationship column
        main_id_col = 'id'
        for col in main_columns:
            if col.lower() in ['id', 'customer_id', 'employee_id', 'product_id']:
                main_id_col = col
                break
        
        subquery_fk_col = None
        for col in subquery_columns:
            if main_table.lower()[:-1] in col.lower() or main_table.lower() in col.lower():
                subquery_fk_col = col
                break
        
        if subquery_fk_col:
            return (
                f"SELECT * FROM {quoted_main} "
                f"WHERE {_quote_identifier(main_id_col)} IN ("
                f"SELECT DISTINCT {_quote_identifier(subquery_fk_col)} FROM {_quote_identifier(subquery_table)}"
                f")"
            )
    
    elif subquery_type == 'not_in':
        # Similar to IN but with NOT
        main_id_col = 'id'
        for col in main_columns:
            if col.lower() in ['id', 'customer_id', 'employee_id']:
                main_id_col = col
                break
        
        subquery_fk_col = None
        for col in subquery_columns:
            if main_table.lower()[:-1] in col.lower():
                subquery_fk_col = col
                break
        
        if subquery_fk_col:
            return (
                f"SELECT * FROM {quoted_main} "
                f"WHERE {_quote_identifier(main_id_col)} NOT IN ("
                f"SELECT DISTINCT {_quote_identifier(subquery_fk_col)} FROM {_quote_identifier(subquery_table)}"
                f")"
            )
    
    return None


def detect_window_function(question: str) -> Optional[Dict]:
    """
    Detect if question requires window functions
    Returns: {'function': 'ROW_NUMBER'|'RANK'|'DENSE_RANK'|'LEAD'|'LAG'|'SUM_OVER', 'partition_by': ..., 'order_by': ...}
    """
    q_lower = question.lower()
    
    # ROW_NUMBER patterns
    if any(phrase in q_lower for phrase in [
        'row number', 'first in each', 'top in each', 'one per',
        'numbered within', 'ranked within'
    ]):
        return {'function': 'ROW_NUMBER', 'partition_by': None, 'order_by': None}
    
    # RANK patterns
    if any(phrase in q_lower for phrase in [
        'rank', 'ranking', 'ranked', 'position',
        'top ranked', 'highest ranked'
    ]):
        return {'function': 'RANK', 'partition_by': None, 'order_by': None}
    
    # DENSE_RANK patterns
    if any(phrase in q_lower for phrase in [
        'dense rank', 'consecutive rank', 'no gaps'
    ]):
        return {'function': 'DENSE_RANK', 'partition_by': None, 'order_by': None}
    
    # LEAD/LAG patterns
    if any(phrase in q_lower for phrase in [
        'next', 'previous', 'before', 'after', 'following',
        'lead', 'lag', 'compare with next', 'compare with previous'
    ]):
        if 'next' in q_lower or 'following' in q_lower:
            return {'function': 'LEAD', 'partition_by': None, 'order_by': None}
        else:
            return {'function': 'LAG', 'partition_by': None, 'order_by': None}
    
    # SUM OVER / Running total patterns
    if any(phrase in q_lower for phrase in [
        'running total', 'cumulative', 'running sum', 'over time',
        'sum over', 'total so far', 'accumulated'
    ]):
        return {'function': 'SUM_OVER', 'partition_by': None, 'order_by': None}
    
    return None


def generate_window_function_sql(
    question: str,
    table_name: str,
    columns: List[str],
    window_spec: Dict,
    db_path: str = None
) -> Optional[str]:
    """Generate SQL with window function"""
    quoted_table = _quote_identifier(table_name)
    q_lower = question.lower()
    
    func_name = window_spec['function']
    
    # Find partition column
    partition_col = None
    for col in columns:
        if any(kw in col.lower() for kw in ['department', 'category', 'group', 'class', 'type']) and col.lower() in q_lower:
            partition_col = col
            break
    
    # Find order column
    order_col = None
    for col in columns:
        if any(kw in col.lower() for kw in ['score', 'salary', 'price', 'date', 'time']) and col.lower() in q_lower:
            order_col = col
            break
    
    if not order_col and len(columns) > 1:
        order_col = columns[1]
    
    # Build window function
    if func_name == 'ROW_NUMBER':
        window_clause = f"ROW_NUMBER() OVER ("
        if partition_col:
            window_clause += f"PARTITION BY {_quote_identifier(partition_col)} "
        if order_col:
            window_clause += f"ORDER BY {_quote_identifier(order_col)} DESC"
        window_clause += ")"
        
        return (
            f"SELECT *, {window_clause} AS row_num "
            f"FROM {quoted_table} "
            f"WHERE {window_clause} = 1"
        )
    
    elif func_name in ['RANK', 'DENSE_RANK']:
        window_clause = f"{func_name}() OVER ("
        if partition_col:
            window_clause += f"PARTITION BY {_quote_identifier(partition_col)} "
        if order_col:
            window_clause += f"ORDER BY {_quote_identifier(order_col)} DESC"
        window_clause += ")"
        
        return (
            f"SELECT *, {window_clause} AS rank_value "
            f"FROM {quoted_table}"
        )
    
    elif func_name in ['LEAD', 'LAG']:
        offset = 1
        offset_match = re.search(r'(\d+)\s*(?:next|previous|before|after)', q_lower)
        if offset_match:
            offset = int(offset_match.group(1))
        
        window_clause = f"{func_name}({__quote_identifier(order_col) if order_col else columns[0]}, {offset}) OVER ("
        if partition_col:
            window_clause += f"PARTITION BY {__quote_identifier(partition_col)} "
        if order_col:
            window_clause += f"ORDER BY {__quote_identifier(order_col)}"
        window_clause += ")"
        
        return (
            f"SELECT *, {window_clause} AS {func_name.lower()}_value "
            f"FROM {quoted_table}"
        )
    
    elif func_name == 'SUM_OVER':
        # Find sum column
        sum_col = None
        for col in columns:
            if any(kw in col.lower() for kw in ['amount', 'total', 'price', 'revenue', 'sales']) and col.lower() in q_lower:
                sum_col = col
                break
        
        if not sum_col:
            sum_col = columns[1] if len(columns) > 1 else columns[0]
        
        window_clause = f"SUM({_quote_identifier(sum_col)}) OVER ("
        if partition_col:
            window_clause += f"PARTITION BY {__quote_identifier(partition_col)} "
        if order_col:
            window_clause += f"ORDER BY {__quote_identifier(order_col)}"
        window_clause += ")"
        
        return (
            f"SELECT *, {window_clause} AS running_total "
            f"FROM {quoted_table}"
        )
    
    return None


def detect_advanced_filtering(question: str) -> Optional[Dict]:
    """
    Detect advanced filtering patterns
    Returns: {'type': 'BETWEEN'|'LIKE'|'CASE'|'IN'|'AND_OR', 'conditions': [...]}
    """
    q_lower = question.lower()
    
    # BETWEEN pattern
    if any(phrase in q_lower for phrase in [
        'between', 'from ... to', 'range', 'from X to Y'
    ]):
        return {'type': 'BETWEEN', 'conditions': []}
    
    # LIKE pattern (already handled, but can enhance)
    if any(phrase in q_lower for phrase in [
        'contains', 'starts with', 'ends with', 'like', 'matches'
    ]):
        return {'type': 'LIKE', 'conditions': []}
    
    # CASE WHEN pattern
    if any(phrase in q_lower for phrase in [
        'if', 'when', 'case', 'categorize', 'classify', 'label as'
    ]):
        return {'type': 'CASE', 'conditions': []}
    
    # IN pattern (list of values)
    if any(phrase in q_lower for phrase in [
        'in', 'one of', 'either', 'any of'
    ]) and not 'subquery' in q_lower:
        return {'type': 'IN', 'conditions': []}
    
    # AND/OR combinations
    if any(word in q_lower for word in ['and', 'or', 'also', 'plus', 'but not']):
        return {'type': 'AND_OR', 'conditions': []}
    
    return None


def build_advanced_filter(
    question: str,
    column: str,
    filter_spec: Dict,
    db_path: str = None
) -> Optional[str]:
    """Build advanced filter clause"""
    q_lower = question.lower()
    quoted_col = _quote_identifier(column)
    
    if filter_spec['type'] == 'BETWEEN':
        # Extract two numbers
        numbers = re.findall(r'(\d+(?:\.\d+)?)', q_lower)
        if len(numbers) >= 2:
            return f"{quoted_col} BETWEEN {numbers[0]} AND {numbers[1]}"
        elif len(numbers) == 1:
            # Assume range from 0 or use single value
            return f"{quoted_col} >= {numbers[0]}"
    
    elif filter_spec['type'] == 'LIKE':
        # Extract pattern
        if 'starts with' in q_lower:
            pattern_match = re.search(r"starts? with ['\"]?(\w+)", q_lower)
            if pattern_match:
                return f"{quoted_col} LIKE '{pattern_match.group(1)}%'"
        elif 'ends with' in q_lower:
            pattern_match = re.search(r"ends? with ['\"]?(\w+)", q_lower)
            if pattern_match:
                return f"{quoted_col} LIKE '%{pattern_match.group(1)}'"
        elif 'contains' in q_lower:
            pattern_match = re.search(r"contains? ['\"]?(\w+)", q_lower)
            if pattern_match:
                return f"{quoted_col} LIKE '%{pattern_match.group(1)}%'"
    
    elif filter_spec['type'] == 'IN':
        # Extract list of values
        values = []
        # Try to find quoted values
        quoted_values = re.findall(r"['\"](\w+)['\"]", q_lower)
        if quoted_values:
            values = quoted_values
        else:
            # Try to find common words that might be values
            common_values = ['active', 'inactive', 'pending', 'completed', 'cancelled']
            for val in common_values:
                if val in q_lower:
                    values.append(val)
        
        if values:
            value_list = ', '.join([f"'{v}'" for v in values])
            return f"{quoted_col} IN ({value_list})"
    
    elif filter_spec['type'] == 'CASE':
        # Build CASE WHEN statement
        case_parts = []
        
        if 'high' in q_lower or 'above' in q_lower:
            number_match = re.search(r'(\d+)', q_lower)
            if number_match:
                threshold = number_match.group(1)
                return (
                    f"CASE WHEN {quoted_col} > {threshold} THEN 'High' "
                    f"WHEN {quoted_col} > {int(threshold) * 0.5} THEN 'Medium' "
                    f"ELSE 'Low' END"
                )
    
    return None


def enhance_date_functions(question: str, date_column: str) -> Optional[str]:
    """
    Enhanced date/time function detection
    """
    q_lower = question.lower()
    quoted_col = _quote_identifier(date_column)
    
    # Last N days
    days_match = re.search(r'last (\d+) days?', q_lower)
    if days_match:
        days = days_match.group(1)
        return f"date({quoted_col}) >= date('now', '-{days} days')"
    
    # Next N days
    days_match = re.search(r'next (\d+) days?', q_lower)
    if days_match:
        days = days_match.group(1)
        return f"date({quoted_col}) <= date('now', '+{days} days')"
    
    # Last week
    if 'last week' in q_lower:
        return f"date({quoted_col}) >= date('now', '-7 days')"
    
    # This week
    if 'this week' in q_lower:
        return f"date({quoted_col}) >= date('now', 'start of week')"
    
    # Last month
    if 'last month' in q_lower:
        return f"strftime('%Y-%m', {quoted_col}) = strftime('%Y-%m', date('now', 'start of month', '-1 month'))"
    
    # This month
    if 'this month' in q_lower or 'current month' in q_lower:
        return f"strftime('%Y-%m', {quoted_col}) = strftime('%Y-%m', 'now')"
    
    # Last year
    if 'last year' in q_lower:
        return f"strftime('%Y', {quoted_col}) = strftime('%Y', date('now', '-1 year'))"
    
    # This year
    if 'this year' in q_lower or 'current year' in q_lower:
        return f"strftime('%Y', {quoted_col}) = strftime('%Y', 'now')"
    
    # Quarter
    quarter_match = re.search(r'q(\d)', q_lower)
    if quarter_match:
        quarter = quarter_match.group(1)
        month_start = (int(quarter) - 1) * 3 + 1
        return f"CAST(strftime('%m', {quoted_col}) AS INTEGER) BETWEEN {month_start} AND {month_start + 2}"
    
    return None


def optimize_query(sql: str, question: str) -> str:
    """
    Query optimization layer
    - Add LIMIT for safety
    - Simplify nested queries when possible
    - Remove unnecessary JOINs
    """
    sql_upper = sql.upper()
    
    # Add LIMIT if not present and no aggregation
    if 'LIMIT' not in sql_upper and 'COUNT(' not in sql_upper and 'GROUP BY' not in sql_upper:
        # Check if it's a simple SELECT
        if sql_upper.strip().startswith('SELECT') and 'JOIN' not in sql_upper:
            # Add reasonable limit
            sql = sql.rstrip(';') + " LIMIT 1000"
    
    # Remove redundant WHERE 1=1 if present
    sql = re.sub(r'WHERE\s+1\s*=\s*1\s*(AND|$)', 'WHERE ', sql, flags=re.IGNORECASE)
    
    return sql


def correct_schema_errors(
    sql: str,
    valid_tables: List[str],
    valid_columns: Dict[str, List[str]],
    all_columns: Dict[str, List[str]] = None
) -> str:
    """
    Schema-aware query correction
    - Replace unknown columns with closest match
    - Map synonyms
    - Correct datatype mismatches
    """
    import difflib
    
    sql_upper = sql.upper()
    
    # Fix table names
    for invalid_table in ['TABLE', 'TABLES', 'DATA']:
        if invalid_table in sql_upper and valid_tables:
            # Replace with first valid table
            sql = re.sub(
                rf'\b{re.escape(invalid_table)}\b',
                valid_tables[0],
                sql,
                flags=re.IGNORECASE
            )
    
    # Fix column names using fuzzy matching
    if all_columns:
        all_valid_cols = []
        for cols in all_columns.values():
            all_valid_cols.extend([c.lower() for c in cols])
        
        # Find potential invalid columns in SQL
        words = re.findall(r'\b\w+\b', sql)
        for word in words:
            word_lower = word.lower()
            if word_lower not in all_valid_cols and len(word) > 3:
                # Try to find closest match
                matches = difflib.get_close_matches(word_lower, all_valid_cols, n=1, cutoff=0.6)
                if matches:
                    # Replace with closest match
                    sql = re.sub(
                        rf'\b{re.escape(word)}\b',
                        matches[0],
                        sql,
                        flags=re.IGNORECASE
                    )
    
    return sql


