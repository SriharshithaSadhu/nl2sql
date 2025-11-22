# AskDB - Complete SQL Features Documentation

## ✅ Supported DBMS Features

The AskDB application now supports comprehensive SQL capabilities similar to a full DBMS system.

---

## 1. Basic Queries ✅

### SELECT with Filtering

**Supported Patterns:**
```sql
"show products where price less than 50"
→ SELECT * FROM "products" WHERE "price" < 50

"customers where credit limit greater than 70000"
→ SELECT * FROM "customers" WHERE "credit_limit" > 70000

"employees with salary above 50000"
→ SELECT * FROM "employees" WHERE "salary" > 50000
```

**Operators Supported:**
- Greater than: `>`, `greater than`, `more than`, `above`, `greater`
- Less than: `<`, `less than`, `below`, `under`, `lesser`
- Equal to: `=`, `equals`, `equal to`, `equal`

---

## 2. ORDER BY Queries ✅

**Supported Patterns:**
```sql
"show all customers order by credit limit descending"
→ SELECT * FROM "customers" ORDER BY "credit_limit" DESC

"list products sorted by price highest first"
→ SELECT * FROM "products" ORDER BY "price" DESC

"employees sorted by salary ascending"
→ SELECT * FROM "employees" ORDER BY "salary" ASC
```

**Keywords:**
- Order: `order by`, `sort by`, `sorted by`, `arrange by`
- Direction: `ascending` (ASC), `descending` (DESC), `highest`, `lowest`

**Smart Features:**
- Handles column names with underscores (e.g., `credit_limit` matches "credit limit")
- Auto-detects sort direction from natural language

---

## 3. LIMIT Queries ✅

**Supported Patterns:**
```sql
"show top 3 customers by credit limit"
→ SELECT * FROM "customers" ORDER BY "credit_limit" DESC LIMIT 3

"first 5 products"
→ SELECT * FROM "products" LIMIT 5

"top 10 highest salaries"
→ SELECT * FROM "employees" ORDER BY "salary" DESC LIMIT 10
```

**Keywords:** `top N`, `first N`, `limit N`

---

## 4. Combined Queries ✅

**WHERE + ORDER BY + LIMIT:**
```sql
"top 5 products where price less than 100 sorted by price descending"
→ SELECT * FROM "products" WHERE "price" < 100 ORDER BY "price" DESC LIMIT 5
```

---

## 5. GROUP BY Queries ✅

### Basic Aggregations

**COUNT:**
```sql
"count products by category"
→ SELECT "category", COUNT(*) as count FROM "products" GROUP BY "category"

"how many employees by department"
→ SELECT "department", COUNT(*) as count FROM "employees" GROUP BY "department"
```

**AVERAGE:**
```sql
"average price by category"
→ SELECT "category", AVG("price") as average_price FROM "products" GROUP BY "category"

"average salary by department"
→ SELECT "department", AVG("salary") as average_salary FROM "employees" GROUP BY "department"
```

**SUM:**
```sql
"total revenue by month"
→ SELECT "month", SUM("revenue") as total_revenue FROM "sales" GROUP BY "month"
```

### GROUP BY with ORDER BY ✅

```sql
"count products by category sorted by count descending"
→ SELECT "category", COUNT(*) as count FROM "products" 
  GROUP BY "category" ORDER BY count DESC

"average price by category ordered by average price highest"
→ SELECT "category", AVG("price") as average_price FROM "products" 
  GROUP BY "category" ORDER BY average_price DESC
```

---

## 6. HAVING Clauses ✅

**With COUNT:**
```sql
"count products by category having count greater than 1"
→ SELECT "category", COUNT(*) as count FROM "products" 
  GROUP BY "category" HAVING COUNT(*) > 1

"departments with more than 10 employees"
→ SELECT "department", COUNT(*) FROM "employees" 
  GROUP BY "department" HAVING COUNT(*) > 10
```

**With AVG:**
```sql
"average price by category having average greater than 100"
→ SELECT "category", AVG("price") as average_price FROM "products" 
  GROUP BY "category" HAVING AVG("price") > 100
```

---

## 7. Multi-Table JOIN Queries ✅

**Automatic FK Detection:**
- Detects explicit foreign keys from `PRAGMA foreign_key_list`
- Uses heuristic matching (e.g., `customer_id` → `customers.id`)
- Builds JOIN paths automatically

**Supported Patterns:**
```sql
"show customers with their orders"
→ SELECT t0."name" AS customers_name, t0."customer_id" AS customers_customer_id,
         t1."order_id" AS orders_order_id, t1."customer_id" AS orders_customer_id
  FROM "customers" t0 
  JOIN "orders" t1 ON t0."customer_id" = t1."customer_id"

"show orders with products"
→ SELECT t0."name" AS products_name, t1."order_id" AS orders_order_id
  FROM "products" t0 
  JOIN "orders" t1 ON t0."product_id" = t1."product_id"
```

**Features:**
- Table aliases (t0, t1, t2, etc.)
- Column aliases for clarity
- Automatic JOIN path finding via BFS algorithm
- Supports 3+ table JOINs

---

## 8. Date-Based Queries ✅

**Supported Patterns:**
```sql
"orders from this year"
→ SELECT * FROM "orders" 
  WHERE strftime('%Y', "order_date") = strftime('%Y', 'now')

"sales from last month"
→ SELECT * FROM "sales" 
  WHERE strftime('%Y-%m', "date") = strftime('%Y-%m', date('now','start of month','-1 month'))

"transactions from today"
→ SELECT * FROM "transactions" WHERE date("date") = date('now')
```

**Keywords:**
- `this year`, `current year`, `last year`
- `this month`, `current month`, `last month`
- `today`, `yesterday`

---

## 9. Numeric Column Detection ✅

**Smart Column Identification:**

The system automatically identifies numeric columns for comparisons using keywords:
- `salary`, `price`, `amount`, `score`, `revenue`
- `cost`, `total`, `value`, `age`, `quantity`, `balance`

**Example:**
```
"show name whose salary is greater than 90000"
```
- Detects `salary` as the numeric column (not `name`)
- Generates: `SELECT * FROM "employees" WHERE "salary" > 90000`

---

## 10. Safety Features ✅

**Read-Only Enforcement:**
- ✅ SELECT queries allowed
- ✅ WITH (CTE) queries allowed
- ❌ INSERT blocked
- ❌ UPDATE blocked
- ❌ DELETE blocked
- ❌ DROP blocked
- ❌ ALTER blocked

---

## 11. Schema Relationships ✅

**Foreign Key Relationships:**
```python
{
    'orders': [
        {'from_column': 'customer_id', 'to_table': 'customers', 'to_column': 'id'},
        {'from_column': 'product_id', 'to_table': 'products', 'to_column': 'id'}
    ]
}
```

**Visual Schema Graph:**
- Interactive Plotly visualization
- Shows tables as nodes
- Shows relationships as edges
- Displays FK details on hover

---

## Query Pattern Summary

| Feature | Status | Example |
|---------|--------|---------|
| **WHERE filtering** | ✅ | `price > 100` |
| **ORDER BY** | ✅ | `order by salary desc` |
| **LIMIT** | ✅ | `top 10` |
| **GROUP BY** | ✅ | `count by department` |
| **HAVING** | ✅ | `having count > 5` |
| **JOINs** | ✅ | `customers with orders` |
| **Date filtering** | ✅ | `from this year` |
| **Numeric detection** | ✅ | Auto-detects salary/price |
| **Column aliases** | ✅ | `average_price`, `total_count` |
| **Multi-table** | ✅ | 2+ table JOINs |

---

## Example Queries for Testing

### E-commerce Database

```sql
-- Basic filtering
"products where price less than 100"
"customers with credit limit greater than 50000"

-- Sorting
"products sorted by price descending"
"top 10 customers by credit limit"

-- Aggregations
"count orders by customer"
"average price by category"
"total revenue by month"

-- GROUP BY + HAVING
"categories with more than 5 products"
"customers with average order above 1000"

-- Multi-table
"show customers with their orders"
"orders with product details"
"customers with orders and products"
```

### Employee Database

```sql
-- Basic
"employees where salary greater than 75000"
"show employees in Engineering department"

-- Sorting  
"employees sorted by salary highest first"
"top 5 highest paid employees"

-- Aggregations
"count employees by department"
"average salary by department"
"departments with highest average salary"

-- HAVING
"departments with more than 20 employees"
"departments where average salary above 80000"
```

### Sales Database

```sql
-- Time-based
"sales from this year"
"orders from last month"
"transactions from today"

-- Aggregations
"total revenue by region"
"count sales by product"
"average sale amount by customer"

-- Combined
"top 10 products by revenue this year"
"customers with total purchases above 10000"
```

---

## Technical Implementation

### Template Matching (Fast Path)
- Pattern recognition for common queries
- Instant SQL generation (< 1ms)
- No AI model required

### AI Fallback (Complex Queries)
- T5-based transformer model
- Schema-aware prompting
- Handles complex natural language

### SQL Repair & Validation
- Fixes malformed SQL
- Validates columns against schema
- Ensures only SELECT queries

---

## Limitations & Future Enhancements

### Current Limitations:
1. Complex nested subqueries → Falls back to AI
2. UNION queries → Not yet supported
3. Window functions → Not yet supported
4. Complex CASE statements → Falls back to AI

### Planned Features:
- [ ] DISTINCT support
- [ ] IN/NOT IN clauses
- [ ] BETWEEN operator
- [ ] LIKE pattern matching
- [ ] NULL handling
- [ ] Subqueries
- [ ] Window functions (ROW_NUMBER, RANK, etc.)

---

**End of Documentation**
