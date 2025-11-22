# AskDB - Quick Start Guide

## Running the Application

### Start the Streamlit App

```powershell
python -m streamlit run app.py
```

The app will open in your default browser at `http://localhost:8501`

---

## First-Time Setup

### 1. Create an Account

- Click on the **"Sign Up"** tab
- Enter your details:
  - Username
  - Email
  - Display Name (optional)
  - Password (min 6 characters)
- Click **"Sign Up"**

### 2. Sign In

- Switch to **"Sign In"** tab
- Enter your username and password
- Click **"Sign In"**

---

## Using the Application

### Step 1: Upload Your Database

**Supported Formats:**
- CSV files (`.csv`)
- Excel files (`.xls`, `.xlsx`)
- SQLite databases (`.db`, `.sqlite`, `.sqlite3`)

**How to Upload:**
1. Look for **"Database Upload"** in the sidebar
2. Click **"Browse files"**
3. Select one or multiple files
4. Files are automatically converted to SQLite

**Multiple Files:**
- You can upload multiple CSV/Excel files to create a multi-table database
- Foreign key relationships are automatically detected

---

### Step 2: Ask Questions in Natural Language

Navigate to the **"💬 Ask a Question"** tab and type your questions.

#### Example Questions

**Basic Queries:**
```
Show all records
List all students
Display everything
```

**Filtering:**
```
Students where score greater than 90
Show customers where total > 1000
Products with price less than 50
```

**Aggregations:**
```
Count students
Average score
Total revenue
Sum of sales
```

**Grouping:**
```
Count students by department
Average price by category
Total sales by region
Revenue by month
```

**Multi-table Queries:**
```
Show students with their courses
List orders with customer details
Display products with categories
```

---

### Step 3: View Results

After asking a question, you'll see:

1. **✅ Success Message** - Shows number of rows returned
2. **🔍 Query Insights** - Tables involved, aggregations, joins, filters
3. **📋 Query Results** - Data table with your results
4. **Download CSV** - Button to download results
5. **📊 Visualizations** - Auto-generated charts (for numeric data)
6. **💡 Summary** - Natural language summary of results

---

## Chat Management

### Create New Chat
- Click **"➕ New Chat"** in the sidebar
- Start a fresh conversation

### View Chat History
- Go to **"💭 Chat History"** tab
- See all previous questions and answers
- Review result previews

### Switch Between Chats
- Click on any chat in the sidebar
- Chat history loads automatically

---

## Advanced Features

### Schema Visualization

If you upload multiple related tables, you'll see:
- **🗺️ Visual Schema Graph** - Interactive diagram showing table relationships
- **Relationship Details** - Foreign key connections between tables

### Query History

Navigate to **"📜 Query History"** tab to see:
- All past queries
- Success/failure status
- Number of rows returned
- Error messages (if any)

---

## Supported Query Patterns

### Simple Patterns (Fast Template-based)

| Pattern | Example |
|---------|---------|
| Show all | "Show all students" |
| Count | "Count students" |
| Average | "Average score" |
| Sum | "Total revenue" |
| Filter | "Score greater than 90" |
| Group By | "Count by department" |

### Complex Patterns (AI-powered)

| Pattern | Example |
|---------|---------|
| Multi-column | "Show name, score, and department" |
| Multiple filters | "Students in CS with score > 85" |
| Complex aggregations | "Average score by department where grade is A" |
| Multi-table JOINs | "Students with their course enrollments" |

---

## Tips for Best Results

### ✅ Do's

1. **Use exact column names when possible**
   - "Show score" (if column is named 'score')
   - "Average price" (if column is named 'price')

2. **Be specific with values**
   - "Show Computer Science students"
   - "Orders where amount greater than 1000"

3. **Mention tables for multi-table queries**
   - "Show students with courses"
   - "List customers with their orders"

4. **Use natural language for aggregations**
   - "Average score by department"
   - "Count orders by customer"

### ❌ Don'ts

1. **Avoid ambiguous references**
   - ❌ "Show high scorers" (What's high?)
   - ✅ "Show students where score > 90"

2. **Don't use database jargon**
   - ❌ "SELECT * FROM students"
   - ✅ "Show all students"

3. **Don't ask unrelated questions**
   - ❌ "What's the weather?" (Not a database query)
   - ✅ "What's the average temperature?" (If you have weather data)

---

## Troubleshooting

### "No results found"
- Check if your table has data
- Try a simpler query first ("Show all records")
- Verify column names in the schema (sidebar)

### "Column not found"
- Check the **"Database Schema"** section in sidebar
- Use exact column names as shown
- Try asking about the table first

### "Table not found"
- Make sure you've uploaded a database
- Check the schema section for available tables
- Re-upload if needed

### Query returns wrong results
- Be more specific with your question
- Add filtering conditions
- Check if the column name matches your data

---

## Settings

### Model Configuration

In the sidebar under **"⚙️ Settings"**:

- **NL→SQL Model:** Default is `mrm8488/t5-base-finetuned-wikiSQL`
- **Summary Model:** Default is `t5-small`
- **Template-only (safe mode):** Bypass AI and use only templates

### Database Backend

For production use, you can configure PostgreSQL:

1. Click **"Auth DB Backend"**
2. Select "PostgreSQL"
3. Enter your `DATABASE_URL`
4. Click **"Connect"**

Default uses local SQLite (no setup required)

---

## Running Tests

To verify all features are working:

```powershell
python test_features.py
```

This will:
- Create a test database
- Run 15 comprehensive tests
- Display pass/fail results
- Clean up automatically

Expected output: **"15 passed, 0 failed"**

---

## Keyboard Shortcuts

- **Enter** in question box: Submit query
- **Ctrl+Enter**: Force submit
- **Sidebar buttons**: Click to switch views

---

## Data Privacy & Security

### ✅ Safe by Design

- **Read-only queries:** Only SELECT queries allowed
- **No modifications:** INSERT, UPDATE, DELETE blocked
- **No drops:** DROP TABLE commands blocked
- **Password hashing:** bcrypt encryption
- **Session isolation:** Each user has separate data

### Your Data

- Database files stored temporarily during session
- Chat history saved per user
- SQL queries stored server-side only (never shown to user)
- No data sent to external services (local processing)

---

## Example Workflows

### Workflow 1: Student Grade Analysis

1. Upload `students.csv`
2. Ask: "Show all students"
3. Ask: "Average score by department"
4. Ask: "Students where score greater than 90"
5. Download results as CSV

### Workflow 2: Sales Analysis

1. Upload `sales.csv` and `customers.csv`
2. Ask: "Total revenue"
3. Ask: "Average sale amount by region"
4. Ask: "Show customers with their orders"
5. View visualizations

### Workflow 3: Product Inventory

1. Upload `products.xlsx`
2. Ask: "Count products by category"
3. Ask: "Products with price less than 50"
4. Ask: "Average price by category"
5. Export results

---

## Getting Help

### In-App Help

- Hover over **ℹ️** icons for tooltips
- Check **"Database Schema"** for table/column info
- Review **"Example Questions"** on the home page

### Documentation

- `TEST_REPORT.md` - Detailed feature testing results
- `test_features.py` - Test script with examples
- `README.md` - Project documentation

---

## Logging Out

Click **"🚪 Logout"** in the sidebar to end your session.

---

**Happy Querying! 🚀**
