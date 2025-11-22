import sqlite3
from typing import Dict, List, Tuple, Optional
import pandas as pd

# Core utilities extracted from app.py to decouple UI from logic

def quote_identifier(name: str) -> str:
    """Properly quote SQL identifiers to handle spaces and reserved words"""
    return f'"{name.replace(chr(34), chr(34)+chr(34))}"'


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
            quoted_table = quote_identifier(table_name)
            cursor.execute(f"PRAGMA table_info({quoted_table})")
            columns = cursor.fetchall()
            schema[table_name] = [col[1] for col in columns]
        except Exception:
            schema[table_name] = []

    conn.close()
    return schema


def detect_foreign_keys(db_path: str) -> Dict[str, List[Dict]]:
    """Detect foreign key relationships between tables using PRAGMA and heuristics"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]

    relationships: Dict[str, List[Dict]] = {}

    for table_name in tables:
        quoted_table = quote_identifier(table_name)
        relationships[table_name] = []

        try:
            cursor.execute(f"PRAGMA foreign_key_list({quoted_table})")
            fks = cursor.fetchall()
            for fk in fks:
                relationships[table_name].append({
                    'from_column': fk[3],
                    'to_table': fk[2],
                    'to_column': fk[4]
                })
        except Exception:
            pass

        try:
            cursor.execute(f"PRAGMA table_info({quoted_table})")
            columns = cursor.fetchall()
            for col in columns:
                col_name = col[1].lower()
                if col_name.endswith('_id'):
                    potential_table = col_name[:-3]
                    for other_table in tables:
                        other_lower = other_table.lower()
                        if other_lower in (potential_table, potential_table + 's') or (other_lower + 's') == potential_table:
                            exists = any(
                                r['from_column'].lower() == col_name and r['to_table'].lower() == other_table.lower()
                                for r in relationships[table_name]
                            )
                            if not exists:
                                relationships[table_name].append({
                                    'from_column': col[1],
                                    'to_table': other_table,
                                    'to_column': 'id',
                                    'heuristic': True
                                })
        except Exception:
            pass

    conn.close()
    return relationships


def _fuzzy_match(query_word: str, target: str, threshold: float = 0.6) -> bool:
    """Fuzzy string matching for abbreviations and partial matches"""
    query_word = query_word.lower().strip()
    target = target.lower().strip()
    
    # Exact match
    if query_word == target:
        return True
    
    # Substring match
    if query_word in target or target in query_word:
        return True
    
    # Abbreviation match (e.g., "math" matches "mathematics")
    if target.startswith(query_word) and len(query_word) >= 3:
        return True
    
    # Common abbreviations
    abbreviations = {
        'math': 'mathematics',
        'maths': 'mathematics',
        'eng': 'engineering',
        'cs': 'computer science',
        'comp': 'computer',
        'sci': 'science',
        'bio': 'biology',
        'chem': 'chemistry',
        'phys': 'physics',
        'hist': 'history',
        'geo': 'geography',
        'econ': 'economics',
        'admin': 'administration',
        'mgmt': 'management',
        'hr': 'human resources',
        'acc': 'accounting',
        'fin': 'finance',
        'ops': 'operations',
        'dev': 'development',
        'prod': 'product',
        'qty': 'quantity',
        'amt': 'amount',
        'dept': 'department',
        'emp': 'employee',
        'cust': 'customer',
        'addr': 'address',
        'desc': 'description',
    }
    
    if query_word in abbreviations and abbreviations[query_word] in target:
        return True
    
    # Simple Levenshtein-like similarity for typos (very basic)
    if len(query_word) >= 4 and len(target) >= 4:
        matches = sum(1 for a, b in zip(query_word, target) if a == b)
        similarity = matches / max(len(query_word), len(target))
        if similarity >= threshold:
            return True
    
    return False


def extract_enhanced_schema(db_path: str) -> Dict[str, Dict]:
    """Extract rich schema with column types and sample values for AI"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    enhanced_schema: Dict[str, Dict] = {}
    for table in tables:
        table_name = table[0]
        try:
            quoted_table = quote_identifier(table_name)
            cursor.execute(f"PRAGMA table_info({quoted_table})")
            columns_info = cursor.fetchall()

            columns: Dict[str, Dict] = {}
            for col in columns_info:
                col_name = col[1]
                col_type = col[2]
                quoted_col = quote_identifier(col_name)
                try:
                    cursor.execute(f"SELECT DISTINCT {quoted_col} FROM {quoted_table} LIMIT 50")
                    samples = [str(row[0]) for row in cursor.fetchall() if row[0] is not None]
                except Exception:
                    samples = []
                columns[col_name] = {
                    'type': col_type if col_type else 'text',
                    'samples': samples
                }

            enhanced_schema[table_name] = {'columns': columns}
        except Exception:
            enhanced_schema[table_name] = {'columns': {}}

    conn.close()
    return enhanced_schema


def format_schema_for_model(schema: Dict[str, List[str]]) -> str:
    schema_lines = []
    for table_name, columns in schema.items():
        column_list = ', '.join(columns)
        schema_lines.append(f"Table {table_name} has columns: {column_list}")
    return '\n'.join(schema_lines)


def _build_fk_graph(foreign_keys: Dict[str, List[Dict]]) -> Dict[str, List[Tuple[str, Tuple[str, str]]]]:
    """Build an undirected graph of table relationships.
    Returns: {table: [(neighbor_table, (from_col, to_col))]}
    """
    graph: Dict[str, List[Tuple[str, Tuple[str, str]]]] = {}
    for tbl, fks in foreign_keys.items():
        graph.setdefault(tbl, [])
        for fk in fks or []:
            to_tbl = fk.get('to_table')
            from_col = fk.get('from_column')
            to_col = fk.get('to_column', 'id')
            if to_tbl:
                graph.setdefault(to_tbl, [])
                # Edge both ways with appropriate col mapping
                graph[tbl].append((to_tbl, (from_col, to_col)))
                graph[to_tbl].append((tbl, (to_col, from_col)))
    return graph


def _find_join_path(graph: Dict[str, List[Tuple[str, Tuple[str, str]]]], start: str, targets: List[str]) -> Optional[List[str]]:
    """Find a simple path from start that covers all targets (greedy BFS).
    Returns list of tables in join order including start.
    """
    from collections import deque
    targets_set = set(targets)
    if not targets_set:
        return None
    # BFS to each target sequentially, accumulating path.
    path = [start]
    current = start
    remaining = [t for t in targets if t != start]
    while remaining:
        goal = remaining[0]
        # BFS from current to goal
        prev: Dict[str, Optional[str]] = {current: None}
        q = deque([current])
        found = False
        while q and not found:
            node = q.popleft()
            for neigh, _cols in graph.get(node, []):
                if neigh not in prev:
                    prev[neigh] = node
                    if neigh == goal:
                        found = True
                        break
                    q.append(neigh)
        if not found:
            return None
        # reconstruct
        chain = []
        n = goal
        while n is not None:
            chain.append(n)
            n = prev[n]
        chain.reverse()
        # append chain excluding current duplicate
        for t in chain[1:]:
            path.append(t)
        current = goal
        remaining.pop(0)
    return path


def get_join_template_sql(
    question: str,
    related_tables: List[str],
    all_columns: Dict,
    foreign_keys: Dict,
    db_path: str = None
) -> Optional[str]:
    """Generate JOIN SQL using FK graph with aliasing and smarter SELECT/GROUP BY.
    Supports: INNER, LEFT, RIGHT, FULL OUTER, CROSS JOINs"""
    if len(related_tables) < 2:
        return None

    q_lower = question.lower()
    primary_table = related_tables[0]

    # Detect JOIN type from question
    try:
        from advanced_sql import detect_join_type, build_join_clause
        join_type = detect_join_type(question)
    except ImportError:
        join_type = 'INNER'
        build_join_clause = None

    # Build FK graph and compute a join path that connects all mentioned tables
    graph = _build_fk_graph(foreign_keys)
    path = _find_join_path(graph, primary_table, related_tables)
    if not path:
        return None

    # Assign aliases t0, t1, ... for readability
    alias_of: Dict[str, str] = {tbl: f"t{i}" for i, tbl in enumerate(path)}

    # Build JOIN clauses from path edges
    join_clauses: List[str] = []
    tables_in_join = [path[0]]
    for i in range(len(path) - 1):
        a = path[i]
        b = path[i + 1]
        # find edge details
        edge = None
        for neigh, cols in graph.get(a, []):
            if neigh == b:
                edge = cols
                break
        if not edge:
            return None
        from_col, to_col = edge
        
        # Use advanced JOIN builder if available
        if build_join_clause:
            join_clause = build_join_clause(
                a, b, from_col, to_col,
                join_type=join_type,
                alias_from=alias_of[a],
                alias_to=alias_of[b]
            )
        else:
            # Fallback to INNER JOIN
            join_keyword = 'INNER JOIN' if join_type == 'INNER' else 'LEFT JOIN'
            if join_type == 'CROSS':
                join_clause = f"CROSS JOIN {quote_identifier(b)} {alias_of[b]}"
            else:
                join_clause = (
                    f"{join_keyword} {quote_identifier(b)} {alias_of[b]} "
                    f"ON {alias_of[a]}.{quote_identifier(from_col)} = {alias_of[b]}.{quote_identifier(to_col)}"
                )
        
        join_clauses.append(join_clause)
        tables_in_join.append(b)

    # Build SELECT list: prefer human-friendly fields if present
    preferred_cols = ['name', 'title', 'email', 'category', 'status']
    numeric_cols = ['total', 'amount', 'price', 'score', 'revenue', 'quantity']

    def pick_cols(tbl: str, limit: int = 3) -> List[str]:
        cols = all_columns.get(tbl, [])
        picks: List[str] = []
        # pick id
        if 'id' in [c.lower() for c in cols]:
            # get the original case
            for c in cols:
                if c.lower() == 'id':
                    picks.append(f"{alias_of[tbl]}.{quote_identifier(c)} AS {tbl}_id")
                    break
        # preferred
        for pref in preferred_cols:
            for c in cols:
                if c.lower() == pref and f"{alias_of[tbl]}.{quote_identifier(c)} AS {tbl}_{c}" not in picks:
                    picks.append(f"{alias_of[tbl]}.{quote_identifier(c)} AS {tbl}_{c}")
                    break
        # numeric if asked for totals
        if any(k in q_lower for k in ['sum', 'total', 'revenue', 'amount', 'price']):
            for num in numeric_cols:
                for c in cols:
                    if c.lower() == num and f"{alias_of[tbl]}.{quote_identifier(c)} AS {tbl}_{c}" not in picks:
                        picks.append(f"{alias_of[tbl]}.{quote_identifier(c)} AS {tbl}_{c}")
                        break
        # fill remaining few
        for c in cols:
            if len(picks) >= limit:
                break
            expr = f"{alias_of[tbl]}.{quote_identifier(c)} AS {tbl}_{c}"
            if expr not in picks:
                picks.append(expr)
        return picks[:limit]

    select_items: List[str] = []
    for tbl in tables_in_join:
        select_items.extend(pick_cols(tbl))

    # COUNT intent with GROUP BY best matching dimension
    if any(kw in q_lower for kw in ['count', 'how many', 'number of', 'total number']):
        # choose a grouping column based on mentioned table/col keywords
        group_by = None
        for tbl in tables_in_join:
            for col in all_columns.get(tbl, []):
                if col.lower() in q_lower and col.lower() not in ['id']:
                    group_by = f"{alias_of[tbl]}.{quote_identifier(col)}"
                    break
            if group_by:
                break
        if not group_by:
            # fallback: first non-id from primary
            for col in all_columns.get(primary_table, []):
                if col.lower() != 'id':
                    group_by = f"{alias_of[primary_table]}.{quote_identifier(col)}"
                    break
        if group_by:
            return (
                f"SELECT {group_by} AS group_value, COUNT(*) AS count "
                f"FROM {quote_identifier(primary_table)} {alias_of[primary_table]} "
                f"{' '.join(join_clauses)} GROUP BY {group_by}"
            )
        else:
            return (
                f"SELECT COUNT(*) AS total FROM {quote_identifier(primary_table)} {alias_of[primary_table]} "
                f"{' '.join(join_clauses)}"
            )

    # Optional value-aware filtering across tables using sample values
    where_clauses: List[str] = []
    if db_path:
        try:
            enhanced = extract_enhanced_schema(db_path)
            words = [w.lower().strip('.,!?;:') for w in question.split() if len(w) > 2]
            for tbl in tables_in_join:
                alias = alias_of[tbl]
                for col_name, meta in enhanced.get(tbl, {}).get('columns', {}).items():
                    for sample in meta.get('samples', [])[:20]:
                        sval = str(sample).lower()
                        if any((w in sval or sval in w) for w in words):
                            where_clauses.append(f"{alias}.{quote_identifier(col_name)} LIKE '%{sample}%'" )
                            break
        except Exception:
            pass

    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    return (
        f"SELECT {', '.join(select_items)} FROM {quote_identifier(primary_table)} {alias_of[primary_table]} "
        f"{' '.join(join_clauses)}{where_sql}"
    )


def get_template_sql(question: str, table_name: str, columns: List[str], db_path: str = None) -> Optional[str]:
    import re
    q_lower = question.lower()

    quoted_table = quote_identifier(table_name)
    value_to_column = {}
    if db_path:
        try:
            enhanced_schema = extract_enhanced_schema(db_path)
            if table_name in enhanced_schema:
                for col_name, col_info in enhanced_schema[table_name].get('columns', {}).items():
                    samples = col_info.get('samples', [])
                    for sample in samples:
                        value_to_column[sample.lower()] = (col_name, sample)
        except Exception:
            pass

    if 'average' in q_lower or 'avg' in q_lower:
        if ' by ' in q_lower:
            avg_col = None
            group_col = None
            agg_keywords = ['score', 'price', 'amount', 'value', 'salary', 'revenue', 'sales',
                           'cost', 'total', 'quantity', 'qty', 'count', 'number', 'rate',
                           'balance', 'payment', 'profit', 'discount', 'tax', 'fee', 'charge']
            for col in columns:
                if col.lower() in q_lower:
                    col_lower = col.lower()
                    if any(kw in col_lower for kw in agg_keywords):
                        avg_col = col
                        break
            if not avg_col:
                for keyword in agg_keywords:
                    if keyword in q_lower:
                        for col in columns:
                            if keyword in col.lower():
                                avg_col = col
                                break
                        if avg_col:
                            break
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
                base_sql = f"SELECT {quoted_group}, AVG({quoted_avg}) as average_{avg_col} FROM {quoted_table} GROUP BY {quoted_group}"
                
                # Add HAVING clause if comparison is mentioned
                having_sql = ""
                if any(word in q_lower for word in ['having', 'greater than', 'more than', 'above', 'less than', 'below']):
                    number_match = re.search(r'(\d+(?:\.\d+)?)', q_lower)
                    if number_match:
                        value = number_match.group(1)
                        if any(word in q_lower for word in ['greater than', 'more than', 'above', '>']):
                            having_sql = f" HAVING AVG({quoted_avg}) > {value}"
                        elif any(word in q_lower for word in ['less than', 'below', '<']):
                            having_sql = f" HAVING AVG({quoted_avg}) < {value}"
                
                    # Add ORDER BY (support multiple columns)
                    order_sql = ""
                    if any(word in q_lower for word in ['order', 'sort', 'highest', 'lowest']):
                        order_dir = 'DESC' if any(word in q_lower for word in ['desc', 'highest', 'descending']) else 'ASC'
                        # Support multiple ORDER BY columns
                        order_cols = []
                        # First column: the aggregated value
                        order_cols.append(f"average_{avg_col}")
                        # Check for secondary sort columns
                        for col in columns:
                            if col != avg_col and col != group_col:
                                col_lower = col.lower()
                                if col_lower in q_lower and any(word in q_lower for word in ['then', 'and', 'also']):
                                    order_cols.append(quote_identifier(col))
                        if order_cols:
                            order_sql = f" ORDER BY {', '.join(order_cols)} {order_dir}"
                
                return f"{base_sql}{having_sql}{order_sql}"
        for col in columns:
            if col in q_lower:
                quoted_col = quote_identifier(col)
                return f"SELECT AVG({quoted_col}) as average_{col} FROM {quoted_table}"

    count_keywords = ['count', 'how many', 'number of', 'total number']
    if any(keyword in q_lower for keyword in count_keywords) and not any(word in q_lower for word in ['where', 'above', 'below', 'average', 'sum', 'total revenue', 'total price']):
        if 'by' in q_lower or 'group' in q_lower:
            for col in columns:
                if col.lower() in q_lower:
                    quoted_col = quote_identifier(col)
                    base_sql = f"SELECT {quoted_col}, COUNT(*) as count FROM {quoted_table} GROUP BY {quoted_col}"
                    
                    # Add HAVING clause (enhanced with multiple conditions)
                    having_sql = ""
                    having_conditions = []
                    
                    # Detect HAVING with COUNT
                    if any(word in q_lower for word in ['having', 'where count', 'with count']):
                        number_match = re.search(r'(\d+)', q_lower)
                        if number_match:
                            value = number_match.group(1)
                            if any(word in q_lower for word in ['greater', 'more', 'above', '>', 'at least']):
                                having_conditions.append(f"COUNT(*) > {value}")
                            elif any(word in q_lower for word in ['less', 'below', '<', 'at most']):
                                having_conditions.append(f"COUNT(*) < {value}")
                            elif any(word in q_lower for word in ['equal', 'exactly', '=']):
                                having_conditions.append(f"COUNT(*) = {value}")
                    
                    # Support multiple HAVING conditions with AND/OR
                    if having_conditions:
                        having_sql = f" HAVING {' AND '.join(having_conditions)}"
                    
                    # Add ORDER BY (support multiple columns)
                    order_sql = ""
                    if any(word in q_lower for word in ['order', 'sort', 'highest', 'lowest', 'descending', 'ascending']):
                        order_dir = 'DESC' if any(word in q_lower for word in ['desc', 'highest', 'most', 'descending']) else 'ASC'
                        # Support multiple ORDER BY columns
                        order_cols = ['count']
                        # Check for secondary sort columns
                        for col in columns:
                            if col != group_col:
                                col_lower = col.lower()
                                if col_lower in q_lower and any(word in q_lower for word in ['then', 'and', 'also']):
                                    order_cols.append(quote_identifier(col))
                        if order_cols:
                            order_sql = f" ORDER BY {', '.join(order_cols)} {order_dir}"
                    
                    return f"{base_sql}{having_sql}{order_sql}"
        return f"SELECT COUNT(*) as total FROM {quoted_table}"

    sum_keywords = ['total', 'revenue', 'sum', 'combined']
    if any(keyword in q_lower for keyword in sum_keywords) and not any(word in q_lower for word in ['where', 'above', 'below', 'count', 'average']):
        sum_col = None
        for col in columns:
            col_lower = col.lower()
            if col_lower in q_lower or any(keyword in col_lower for keyword in ['amount', 'total', 'price', 'cost', 'revenue', 'value', 'quantity', 'sales']):
                if db_path:
                    try:
                        enhanced_schema = extract_enhanced_schema(db_path)
                        if table_name in enhanced_schema:
                            col_info = enhanced_schema[table_name].get('columns', {}).get(col, {})
                            col_type = col_info.get('type', '').lower()
                            if col_type in ['integer', 'real', 'numeric', 'decimal', 'float']:
                                sum_col = col
                                break
                    except Exception:
                        pass
                if any(keyword in col_lower for keyword in ['amount', 'total', 'price', 'cost', 'revenue', 'value', 'sales']):
                    sum_col = col
                    break
        if sum_col:
            quoted_col = quote_identifier(sum_col)
            return f"SELECT SUM({quoted_col}) as total_{sum_col} FROM {quoted_table}"

    # PRIORITY: Filter queries with WHERE conditions (check BEFORE show/list patterns)
    # When comparison operators are present, prioritize numeric-sounding columns
    has_comparison = any(word in q_lower for word in ['greater than', 'more than', 'above', '>', 'greater', 'less than', 'below', 'under', '<', 'lesser', 'equals', 'equal'])
    
    if has_comparison:
        # Extract number from question
        number_match = re.search(r'(\d+(?:\.\d+)?)', q_lower)
        if number_match:
            value = number_match.group(1)
            
            # Find the right column - prioritize numeric columns that appear in question
            target_col = None
            numeric_keywords = ['salary', 'price', 'amount', 'score', 'revenue', 'cost', 'total', 'value', 'age', 'quantity', 'balance']
            
            # First, look for numeric-sounding columns mentioned in question
            for col in columns:
                col_lower = col.lower()
                if col_lower in q_lower and any(kw in col_lower for kw in numeric_keywords):
                    target_col = col
                    break
            
            # If not found, look for any column that sounds numeric
            if not target_col:
                for col in columns:
                    col_lower = col.lower()
                    if any(kw in col_lower for kw in numeric_keywords):
                        target_col = col
                        break
            
            # If still not found, use any column mentioned in the question
            if not target_col:
                for col in columns:
                    if col.lower() in q_lower:
                        target_col = col
                        break
            
            if target_col:
                quoted_col = quote_identifier(target_col)
                
                # Build WHERE clause
                where_sql = ""
                if any(word in q_lower for word in ['greater than', 'more than', 'above', '>', 'greater']):
                    where_sql = f" WHERE {quoted_col} > {value}"
                elif any(word in q_lower for word in ['less than', 'below', 'under', '<', 'lesser']):
                    where_sql = f" WHERE {quoted_col} < {value}"
                elif any(word in q_lower for word in ['equals', 'equal to', 'equal', '=']):
                    where_sql = f" WHERE {quoted_col} = {value}"
                
                # Add ORDER BY if present
                order_sql = ""
                if any(word in q_lower for word in ['order by', 'sort by', 'sorted', 'highest', 'lowest', 'top']):
                    order_dir = 'DESC' if any(word in q_lower for word in ['desc', 'highest', 'largest', 'top']) else 'ASC'
                    # Try to find order column
                    order_col = target_col  # Default to filter column
                    for col in columns:
                        if col.lower() in q_lower and col != target_col:
                            order_col = col
                            break
                    order_sql = f" ORDER BY {quote_identifier(order_col)} {order_dir}"
                
                # Add LIMIT if present
                limit_sql = ""
                limit_match = re.search(r'(?:top|first|limit)\s+(\d+)', q_lower)
                if limit_match:
                    limit_sql = f" LIMIT {limit_match.group(1)}"
                
                return f"SELECT * FROM {quoted_table}{where_sql}{order_sql}{limit_sql}"

    # Natural date phrases on date-like columns
    date_like_cols = [c for c in columns if c.lower() in ['date', 'created_at', 'updated_at', 'timestamp', 'time', 'order_date', 'sale_date'] or c.lower().endswith('_date')]
    if date_like_cols:
        dcol = quote_identifier(date_like_cols[0])
        if 'last month' in q_lower:
            return f"SELECT * FROM {quoted_table} WHERE strftime('%Y-%m', {dcol}) = strftime('%Y-%m', date('now','start of month','-1 month'))"
        if 'this month' in q_lower or 'current month' in q_lower:
            return f"SELECT * FROM {quoted_table} WHERE strftime('%Y-%m', {dcol}) = strftime('%Y-%m', 'now')"
        if 'last year' in q_lower:
            return f"SELECT * FROM {quoted_table} WHERE strftime('%Y', {dcol}) = strftime('%Y', date('now','-1 year'))"
        if 'this year' in q_lower or 'current year' in q_lower:
            return f"SELECT * FROM {quoted_table} WHERE strftime('%Y', {dcol}) = strftime('%Y', 'now')"
        if 'today' in q_lower:
            return f"SELECT * FROM {quoted_table} WHERE date({dcol}) = date('now')"
        if 'yesterday' in q_lower:
            return f"SELECT * FROM {quoted_table} WHERE date({dcol}) = date('now','-1 day')"

    if any(word in q_lower for word in ['show', 'list', 'display']) and not any(word in q_lower for word in ['average', 'count', 'sum']):
        if value_to_column:
            words = question.split()
            for word in words:
                word_clean = word.lower().strip('.,!?;:')
                if len(word_clean) <= 2:
                    continue
                
                # Exact match
                if word_clean in value_to_column:
                    col_name, original_value = value_to_column[word_clean]
                    quoted_col = quote_identifier(col_name)
                    return f"SELECT * FROM {quoted_table} WHERE {quoted_col} = '{original_value}'"
                
                # Fuzzy match on values
                for sample_val_lower, (col_name, original_value) in value_to_column.items():
                    if word_clean not in ['show', 'list', 'display', 'all', 'the', 'students', 'records', 'employees', 'customers']:
                        # Try fuzzy matching
                        if _fuzzy_match(word_clean, sample_val_lower):
                            quoted_col = quote_identifier(col_name)
                            return f"SELECT * FROM {quoted_table} WHERE {quoted_col} LIKE '%{original_value}%'"
                        # Original substring matching
                        if (word_clean in sample_val_lower or sample_val_lower in word_clean):
                            quoted_col = quote_identifier(col_name)
                            return f"SELECT * FROM {quoted_table} WHERE {quoted_col} LIKE '%{original_value}%'"
        for col in columns:
            col_lower = col.lower()
            if col_lower in q_lower:
                words = question.split()
                for word in words:
                    w = word.lower()
                    if w in ['show', 'all', 'the', 'list', 'display', 'get', 'find', 'select']:
                        continue
                    if w not in ['students', 'records', 'rows', 'entries', 'data'] and w != col_lower and len(word) > 2:
                        quoted_col = quote_identifier(col)
                        return f"SELECT * FROM {quoted_table} WHERE {quoted_col} LIKE '%{word}%'"

    # ORDER BY detection
    order_clause = ""
    if any(word in q_lower for word in ['order by', 'sort by', 'sorted by', 'arrange by', 'sorted', 'order', ' by ']):
        order_col = None
        order_dir = 'ASC'
        
        # Detect direction
        if any(word in q_lower for word in ['descending', 'desc', 'highest', 'largest', 'top', 'descending']):
            order_dir = 'DESC'
        
        # Find column to order by - check both exact match and with spaces replaced by underscores
        for col in columns:
            col_lower = col.lower()
            # Match column name directly
            if col_lower in q_lower:
                order_col = col
                break
            # Try replacing underscores with spaces to match natural language
            col_with_spaces = col_lower.replace('_', ' ')
            if col_with_spaces in q_lower:
                order_col = col
                break
        
        if order_col:
            order_clause = f" ORDER BY {quote_identifier(order_col)} {order_dir}"
    
    # LIMIT detection  
    limit_clause = ""
    limit_match = re.search(r'(?:top|first|limit)\s+(\d+)', q_lower)
    if limit_match:
        limit_clause = f" LIMIT {limit_match.group(1)}"
    
    # Build base query
    question_words = [w.lower().strip('.,!?;:') for w in question.split()]
    potential_filters = [w for w in question_words if len(w) > 3 and w not in [
        'show', 'all', 'the', 'list', 'display', 'get', 'find', 'select',
        'students', 'records', 'rows', 'entries', 'data', 'everything',
        'items', 'values', 'results', 'table', 'from', 'where', 'order', 'sort', 'limit', 'first'
    ]]
    
    # Handle "show all" with ORDER BY/LIMIT
    if any(word in q_lower for word in ['show all', 'list all', 'all']) and not any(word in q_lower for word in ['where', 'above', 'below', 'greater', 'less', 'average', 'count']):
        return f"SELECT * FROM {quoted_table}{order_clause}{limit_clause}"
    
    # If only ORDER BY or LIMIT is present, return SELECT * with those clauses
    if (order_clause or limit_clause) and not has_comparison:
        return f"SELECT * FROM {quoted_table}{order_clause}{limit_clause}"

    return None


def repair_sql(sql: str, table_name: str, columns: List[str], all_columns: Dict = None, is_multi_table: bool = False) -> str:
    import re

    quoted_table = quote_identifier(table_name)
    valid_columns_lower = set([c.lower() for c in columns])
    valid_tables_lower = set([table_name.lower()])

    if is_multi_table and all_columns:
        for tbl, cols in all_columns.items():
            valid_tables_lower.add(tbl.lower())
            for col in cols:
                valid_columns_lower.add(col.lower())

    sql = sql.strip()
    for artifact in ['A:', 'SQL:', '|', 'table:', 'Table:', 'CREATE TABLE', 'col =']:
        if sql.startswith(artifact):
            sql = sql[len(artifact):].strip()
        if artifact in sql and artifact not in ['|', 'A:', 'SQL:']:
            sql = sql.split(artifact)[0].strip()

    sql = re.sub(r'\bFROM\s+table\b', f'FROM {quoted_table}', sql, flags=re.IGNORECASE)

    select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
    if select_match and select_match.group(1).strip() not in ['*', 'COUNT(*)', 'COUNT(*)']:
        has_join = bool(re.search(r'\bJOIN\b', sql, re.IGNORECASE))
        if has_join:
            return sql
        contains_invalid = False
        for word in re.findall(r'\b\w+\b', select_match.group(1)):
            if word.upper() not in ['SELECT', 'FROM', 'WHERE', 'COUNT', 'AVG', 'SUM', 'MAX', 'MIN', 'AS', 'DISTINCT', 'BY', 'GROUP']:
                if word.lower() not in valid_columns_lower and word.lower() not in valid_tables_lower:
                    contains_invalid = True
                    break
        if contains_invalid:
            where_match = re.search(r'WHERE\s+(.+?)(?:ORDER|GROUP|LIMIT|$)', sql, re.IGNORECASE | re.DOTALL)
            if where_match:
                sql = f"SELECT * FROM {quoted_table} WHERE {where_match.group(1).strip()}"
            else:
                sql = f"SELECT * FROM {quoted_table}"

    if not sql.upper().startswith('SELECT') and not sql.upper().startswith('WITH'):
        sql = f"SELECT * FROM {quoted_table}"
    return sql


def generate_sql(question: str, schema_str: str, tokenizer, model, db_path: str = None, history: Optional[List[Dict]] = None) -> str:
    """Generate SQL with support for advanced features:
    - Multiple JOIN types (INNER, LEFT, RIGHT, FULL, CROSS)
    - Subqueries (correlated, scalar, IN/NOT IN)
    - Window functions (ROW_NUMBER, RANK, LEAD/LAG, SUM OVER)
    - Advanced filtering (BETWEEN, CASE WHEN, complex AND/OR)
    - Enhanced date/time functions
    """
    # Try advanced SQL features first
    try:
        from advanced_sql import (
            detect_subquery_intent, generate_subquery_sql,
            detect_window_function, generate_window_function_sql,
            detect_advanced_filtering, build_advanced_filter,
            enhance_date_functions, optimize_query, correct_schema_errors
        )
        use_advanced = True
    except ImportError:
        use_advanced = False
    
    schema_lines = schema_str.split('\n')
    table_names: List[str] = []
    all_columns: Dict[str, List[str]] = {}

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

    q_lower = question.lower()
    
    # Check for window functions
    if use_advanced:
        window_spec = detect_window_function(question)
        if window_spec and table_names:
            sql = generate_window_function_sql(
                question, table_names[0], all_columns.get(table_names[0], []),
                window_spec, db_path
            )
            if sql:
                return optimize_query(sql, question)
    
    # Check for subqueries
    if use_advanced and len(table_names) >= 2:
        subquery_intent = detect_subquery_intent(question)
        if subquery_intent:
            sql = generate_subquery_sql(
                question, table_names[0], all_columns.get(table_names[0], []),
                table_names[1] if len(table_names) > 1 else table_names[0],
                all_columns.get(table_names[1] if len(table_names) > 1 else table_names[0], []),
                subquery_intent['type'], db_path
            )
            if sql:
                return optimize_query(sql, question)
    q_words = [w.strip('.,!?;:') for w in q_lower.split()]
    mentioned_tables: List[str] = []

    for t in table_names:
        t_lower = t.lower()
        if t_lower in q_lower:
            mentioned_tables.append(t)
            continue
        base_name = t_lower
        for prefix in ['sample_', 'tbl_', 'tb_']:
            if base_name.startswith(prefix):
                base_name = base_name[len(prefix):]
                break
        if base_name in q_lower:
            mentioned_tables.append(t)
            continue
        
        # Fuzzy match table names
        for word in q_words:
            if len(word) >= 3 and _fuzzy_match(word, base_name):
                mentioned_tables.append(t)
                break
        
        if t in mentioned_tables:
            continue
        
        # Singular/plural
        if base_name.endswith('s'):
            singular = base_name[:-1]
            if singular in q_lower:
                mentioned_tables.append(t)
        else:
            plural = base_name + 's'
            if plural in q_lower:
                mentioned_tables.append(t)

    foreign_keys: Dict[str, List[Dict]] = {}
    if db_path:
        try:
            foreign_keys = detect_foreign_keys(db_path)
        except Exception:
            pass

    is_multi_table_query = False
    related_tables: List[str] = []

    if len(mentioned_tables) > 1:
        is_multi_table_query = True
        related_tables = mentioned_tables[:3]
    elif len(mentioned_tables) == 1 and foreign_keys:
        primary_table = mentioned_tables[0]
        if primary_table in foreign_keys:
            for fk in foreign_keys[primary_table]:
                related_table = fk['to_table']
                if related_table in table_names:
                    related_cols = all_columns.get(related_table, [])
                    if any(col.lower() in q_lower for col in related_cols):
                        is_multi_table_query = True
                        related_tables = [primary_table, related_table]
                        break

    if not is_multi_table_query and len(mentioned_tables) == 1:
        intent_keywords = ['with', 'including', 'from both', 'together', 'combined']
        if any(keyword in q_lower for keyword in intent_keywords) and foreign_keys:
            primary_table = mentioned_tables[0] if mentioned_tables else table_names[0]
            if primary_table in foreign_keys and foreign_keys[primary_table]:
                is_multi_table_query = True
                related_tables = [primary_table, foreign_keys[primary_table][0]['to_table']]

    if mentioned_tables:
        table_name = mentioned_tables[0]
    else:
        table_name = table_names[0]

    columns = all_columns.get(table_name, [])

    if is_multi_table_query and related_tables:
        join_template_sql = get_join_template_sql(question, related_tables, all_columns, foreign_keys, db_path)
        if join_template_sql:
            return join_template_sql
    elif not is_multi_table_query:
        template_sql = get_template_sql(question, table_name, columns, db_path)
        if template_sql:
            return template_sql

    # AI path: only used when templates don't match and a tokenizer/model are provided
    if tokenizer is None or model is None:
        return f"SELECT * FROM {quote_identifier(table_name)}"

    # Build optional conversation context (last few turns)
    history_lines: List[str] = []
    if history:
        for turn in history[-3:]:
            q = turn.get('question') or ''
            a = turn.get('answer') or ''
            if q:
                history_lines.append(f"Prev Q: {q}")
            if a:
                history_lines.append(f"Prev A: {a}")
    history_block = ("\n" + "\n".join(history_lines) + "\n") if history_lines else "\n"

    enhanced_schema: Dict[str, Dict] = {}
    if db_path:
        try:
            enhanced_schema = extract_enhanced_schema(db_path)
        except Exception:
            pass

    if table_name in enhanced_schema and enhanced_schema[table_name].get('columns'):
        schema_parts = []
        for col_name, col_info in enhanced_schema[table_name]['columns'].items():
            quoted_col = quote_identifier(col_name)
            col_type = col_info.get('type', 'text')
            samples = col_info.get('samples', [])
            sample_str = f" (e.g. {', '.join(samples[:2])})" if samples else ""
            schema_parts.append(f"{quoted_col} {col_type}{sample_str}")
        schema_detail = ', '.join(schema_parts)
    else:
        schema_detail = ', '.join([quote_identifier(col) for col in columns])

    example_column = columns[0] if columns else "id"
    example_column_quoted = quote_identifier(example_column)

    numeric_col = None
    if table_name in enhanced_schema and enhanced_schema[table_name].get('columns'):
        for col_name, col_info in enhanced_schema[table_name]['columns'].items():
            if col_info.get('type', '').lower() in ['integer', 'real', 'numeric', 'decimal', 'float']:
                numeric_col = col_name
                break
    if not numeric_col and len(columns) > 1:
        numeric_col = columns[1]
    numeric_col_quoted = quote_identifier(numeric_col) if numeric_col else example_column_quoted

    all_tables_schema = ""
    join_examples = ""
    if len(table_names) > 1 and foreign_keys:
        all_tables_schema = "\n\nAvailable Tables:\n"
        for tbl in table_names:
            tbl_cols = all_columns.get(tbl, [])
            all_tables_schema += f"- {quote_identifier(tbl)}: {', '.join([quote_identifier(c) for c in tbl_cols])}\n"
        all_tables_schema += "\nTable Relationships:\n"
        for tbl, fk_list in foreign_keys.items():
            if fk_list:
                for fk in fk_list:
                    from_col = quote_identifier(fk['from_column'])
                    to_table = quote_identifier(fk['to_table'])
                    to_col = quote_identifier(fk.get('to_column', 'id'))
                    join_examples += f"\nQ: Show {tbl} with {to_table} details\n"
                    join_examples += f"A: SELECT * FROM {quote_identifier(tbl)} JOIN {to_table} ON {quote_identifier(tbl)}.{from_col} = {to_table}.{to_col}\n"

    prompt = f"""Generate SQLite query using the exact table and column names provided.
{history_block}
IMPORTANT: Use table and column names EXACTLY as listed below. Never use the word "table" as a placeholder.

IMPORTANT: Use table and column names EXACTLY as listed below. Never use the word "table" as a placeholder.

Primary Table: {quote_identifier(table_name)} has columns: {schema_detail}{all_tables_schema}

Examples with ACTUAL column names:
Q: Show all records
A: SELECT * FROM {quote_identifier(table_name)}

Q: Count by {example_column}
A: SELECT {example_column_quoted}, COUNT(*) FROM {quote_identifier(table_name)} GROUP BY {example_column_quoted}

Q: Total {numeric_col if numeric_col else example_column}
A: SELECT SUM({numeric_col_quoted}) FROM {quote_identifier(table_name)}

Q: Where {numeric_col if numeric_col else example_column} above 90
A: SELECT * FROM {quote_identifier(table_name)} WHERE {numeric_col_quoted} > 90{join_examples}

IMPORTANT: Use correct SQL syntax with parentheses for aggregations: SUM(column), AVG(column), COUNT(*).
Do NOT add WHERE clauses unless the question explicitly requests filtering.
For JOIN queries, use the relationships listed above to connect tables properly.

Question: {question}
SQL:"""

    # Import torch only if we actually need to generate via model
    import torch  # type: ignore

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
    sql = repair_sql(sql, table_name, columns, all_columns, is_multi_table_query)
    return sql


def explain_sql_query(sql: str, schema: Dict) -> Dict:
    """Return structured insights about the SQL without exposing it verbatim.
    Output keys: tables, has_join, aggregations, filters, group_by, order_by, limit
    """
    import re
    info = {
        'tables': [],
        'has_join': False,
        'aggregations': [],
        'filters': [],
        'group_by': [],
        'order_by': [],
        'limit': None,
    }
    sql_upper = sql.upper()
    sql_no_ws = ' '.join(sql_upper.split())

    # Tables (intersect with known schema)
    schema_tables = list(schema.keys())
    for t in schema_tables:
        if t.upper() in sql_upper:
            info['tables'].append(t)

    # JOIN
    info['has_join'] = ' JOIN ' in sql_no_ws

    # Aggregations
    for agg in ['COUNT(', 'AVG(', 'SUM(', 'MAX(', 'MIN(']:
        if agg in sql_upper:
            info['aggregations'].append(agg[:-1])

    # WHERE filters (extract simple conditions)
    m_where = re.search(r'WHERE\s+(.+?)(GROUP BY|ORDER BY|LIMIT|$)', sql_upper, re.DOTALL)
    if m_where:
        cond = m_where.group(1).strip()
        # split by AND/OR for display
        parts = re.split(r'\s+(AND|OR)\s+', cond)
        # keep only conditions
        info['filters'] = [p.strip() for i, p in enumerate(parts) if i % 2 == 0 and p.strip()]

    # GROUP BY
    m_group = re.search(r'GROUP BY\s+(.+?)(ORDER BY|LIMIT|$)', sql_upper, re.DOTALL)
    if m_group:
        cols = [c.strip() for c in m_group.group(1).split(',')]
        info['group_by'] = cols

    # ORDER BY
    m_order = re.search(r'ORDER BY\s+(.+?)(LIMIT|$)', sql_upper, re.DOTALL)
    if m_order:
        cols = [c.strip() for c in m_order.group(1).split(',')]
        info['order_by'] = cols

    # LIMIT
    m_limit = re.search(r'LIMIT\s+(\d+)', sql_upper)
    if m_limit:
        info['limit'] = int(m_limit.group(1))

    return info


def sanitize_error_message(error_msg: str) -> str:
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
    dangerous_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE', 'REPLACE', 'PRAGMA', 'ATTACH', 'DETACH']
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
