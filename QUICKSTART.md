# 🚀 AskDB Quick Start Guide

## ⚡ TL;DR - Get Running in 3 Steps

```powershell
# 1. Install dependencies
pip install -e .

# 2. Run Streamlit (works standalone!)
streamlit run app.py

# 3. (Optional) Run backend for API access
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## 📦 What You Just Built

✅ **FastAPI Backend** - Full REST API with JWT auth
✅ **PostgreSQL Integration** - Your Neon database is configured
✅ **Streamlit Frontend** - Beautiful UI (works without backend too!)
✅ **NL2SQL Engine** - T5-based AI model
✅ **Multi-user Support** - Session isolation for uploaded databases
✅ **Comprehensive Logging** - Track all queries and errors

## 🎯 Two Modes of Operation

### Mode 1: Standalone Streamlit (Recommended for Testing)
```powershell
streamlit run app.py
```
- No backend needed
- Direct database connection
- All features work
- Perfect for single-user testing

### Mode 2: Full Stack (Production)
**Terminal 1:**
```powershell
.\run_backend.ps1
# or
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2:**
```powershell
.\run_frontend.ps1
# or
streamlit run app.py
```

## 🔑 Key Features Implemented

### 1. Two-Database Architecture ✅
- **PostgreSQL**: User accounts, chats, messages, logs (permanent)
- **SQLite**: User-uploaded databases (temporary, session-based)
- ✨ **No mixing of user data** - each upload is isolated

### 2. Authentication & Security ✅
- JWT token-based auth
- bcrypt password hashing
- Read-only query execution
- Session cleanup after 24 hours

### 3. NL2SQL Features ✅
- Template-based fast path
- AI model fallback
- Multi-table JOIN detection
- Foreign key aware
- Aggregation support (COUNT, AVG, SUM)

### 4. Conversation History ✅
- Persistent chat storage in PostgreSQL
- View past conversations
- Resume from any chat

### 5. Comprehensive Logging ✅
- Auth events
- Query execution
- Errors and warnings
- User actions

## 🗂️ File Structure

```
nl2sql/
├── backend/
│   ├── main.py          # FastAPI app
│   ├── auth.py          # JWT authentication
│   ├── models.py        # Pydantic schemas
│   ├── upload.py        # SQLite upload handler
│   ├── nl2sql.py        # SQL generation
│   └── query_runner.py  # Safe execution
│
├── database.py          # PostgreSQL models
├── core.py              # NL2SQL logic
├── app.py               # Streamlit UI
├── .env                 # Your config (DATABASE_URL set!)
└── pyproject.toml       # All dependencies
```

## 🌐 Access Points

- **Streamlit**: http://localhost:8501
- **FastAPI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **PostgreSQL**: Your Neon database (already configured)

## 📝 First Steps

### 1. Test Streamlit
```powershell
streamlit run app.py
```
1. Sign up with username/email/password
2. Upload a CSV/Excel/SQLite file
3. Ask a question: "Show all records"
4. See results and visualizations

### 2. Test Backend API
```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Visit http://localhost:8000/docs for interactive API testing:

**Try this:**
1. POST `/api/auth/signup` - Create account
2. POST `/api/auth/login` - Get JWT token
3. POST `/api/upload` - Upload database (use token)
4. POST `/api/query` - Ask a question

## 🔍 Example Queries

### Basic
```
"Show all students"
"List all products"
"Display customers"
```

### Filtering
```
"Show students with score above 90"
"Products with price less than 50"
"Customers where total > 1000"
```

### Aggregation
```
"Average score by department"
"Count orders by customer"
"Total revenue by month"
```

### Joins (Multi-Table)
```
"Show orders with customer names"
"List students with their courses"
"Products with category details"
```

## 🛠️ Troubleshooting

### "Module not found"
```powershell
pip install -e .
```

### "Database connection failed"
- Check `.env` file exists
- Verify `DATABASE_URL` is correct
- App will fallback to local SQLite automatically

### "Port already in use"
```powershell
# Kill existing process
Stop-Process -Name "python" -Force

# Or use different port
uvicorn backend.main:app --port 8001
```

### Model loading issues
- Requires internet connection (downloads from HuggingFace)
- Use "Template-only (safe mode)" in Streamlit settings
- Models are cached after first download

## 📊 Database Schema (PostgreSQL)

```sql
-- Users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Chats
CREATE TABLE chats (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Messages
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    chat_id INTEGER REFERENCES chats(id),
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    sql_query TEXT,
    rows_returned INTEGER DEFAULT 0,
    success INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Logs
CREATE TABLE logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    chat_id INTEGER REFERENCES chats(id),
    level VARCHAR(20) DEFAULT 'info',
    event_type VARCHAR(100),
    message TEXT NOT NULL,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 🎓 Next Steps

1. ✅ **You're already set up!** Everything is configured with your Neon PostgreSQL
2. 📝 Customize the UI in `app.py`
3. 🔧 Add new API endpoints in `backend/main.py`
4. 🤖 Fine-tune the NL2SQL logic in `core.py`
5. 🎨 Add custom visualizations

## 💡 Pro Tips

1. **Development**: Use `--reload` flag for auto-reload
   ```powershell
   uvicorn backend.main:app --reload
   ```

2. **Production**: Set proper `JWT_SECRET_KEY` in `.env`
   ```powershell
   openssl rand -hex 32
   ```

3. **Debugging**: Check logs in PostgreSQL `logs` table

4. **Performance**: Template mode is faster than AI model for simple queries

5. **Security**: Backend validates all queries - only SELECT allowed

## 📚 Documentation

- FastAPI Docs: http://localhost:8000/docs
- Streamlit Docs: https://docs.streamlit.io
- PostgreSQL: Your Neon dashboard

## 🎉 You're Ready!

Your full-stack NL2SQL application is ready to use. Start with Streamlit, then add the backend when you need API access or multi-user support.

**Questions?** Check `README_SETUP.md` for detailed information.

---

Built with ❤️ using FastAPI, Streamlit, and PostgreSQL
