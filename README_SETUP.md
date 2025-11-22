# AskDB - Natural Language to SQL System

A full-stack application that converts natural language questions into SQL queries using AI. Built with **FastAPI** backend (PostgreSQL) and **Streamlit** frontend.

## 🎯 Architecture Overview

### Two-Database System

1. **PostgreSQL (Application Backend)** - Permanent
   - User authentication
   - Chat history
   - Messages
   - Logs
   - Accessed via `DATABASE_URL`

2. **SQLite (User-Uploaded)** - Temporary
   - User's own database files
   - Stored in temp folder per session
   - NOT mixed with other users
   - Automatically cleaned up after 24 hours

## 📋 Features

### Backend (FastAPI)
- ✅ JWT Authentication (login/signup)
- ✅ PostgreSQL for persistent app data
- ✅ SQLite upload handler for user databases
- ✅ NL2SQL generation (T5-based)
- ✅ Safe query execution (read-only)
- ✅ Conversation history
- ✅ Comprehensive logging

### Frontend (Streamlit)
- ✅ Works standalone (without backend)
- ✅ Can integrate with FastAPI backend
- ✅ Upload CSV/Excel/SQLite files
- ✅ Multi-table support with JOIN detection
- ✅ Chat interface with history
- ✅ Auto-visualizations
- ✅ Schema graph visualization

## 🚀 Quick Start

### 1. Install Dependencies

```powershell
# Create virtual environment (if not exists)
python -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install all dependencies
pip install -e .
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
DATABASE_URL=postgresql://user:pass@host:port/dbname
JWT_SECRET_KEY=your-secret-key
```

Your PostgreSQL URL is already configured in the repo.

### 3. Run the Application

#### Option A: Run Streamlit Only (Standalone Mode)

```powershell
streamlit run app.py
```

Access at: http://localhost:8501

#### Option B: Run Full Stack (FastAPI + Streamlit)

**Terminal 1 - Backend:**
```powershell
cd backend
python main.py
```

Backend runs at: http://localhost:8000
API docs at: http://localhost:8000/docs

**Terminal 2 - Frontend:**
```powershell
streamlit run app.py
```

Frontend at: http://localhost:8501

## 📁 Project Structure

```
nl2sql/
├── backend/                  # FastAPI Backend
│   ├── main.py              # API entrypoint
│   ├── auth.py              # JWT authentication
│   ├── models.py            # Pydantic schemas
│   ├── upload.py            # SQLite upload handler
│   ├── nl2sql.py            # SQL generation service
│   └── query_runner.py      # Safe SQL execution
│
├── database.py              # PostgreSQL models (SQLAlchemy)
├── core.py                  # NL2SQL logic
├── app.py                   # Streamlit frontend
│
├── .env                     # Environment variables (DO NOT COMMIT)
├── .env.example             # Template for .env
├── pyproject.toml           # Dependencies
└── README_SETUP.md          # This file
```

## 🔐 Database Schema (PostgreSQL)

### Tables

1. **users** - User accounts
   - id, username, email, password_hash, display_name, created_at

2. **chats** - Conversations
   - id, user_id, title, created_at, updated_at

3. **messages** - Chat messages
   - id, chat_id, role, content, sql_query, rows_returned, success, created_at

4. **logs** - Application logs
   - id, user_id, chat_id, level, event_type, message, metadata, created_at

## 📡 API Endpoints

### Authentication
- `POST /api/auth/signup` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info

### Upload
- `POST /api/upload` - Upload database file (CSV/Excel/SQLite)
- `DELETE /api/upload/{session_id}` - Delete uploaded database

### Schema
- `GET /api/schema/{session_id}` - Get database schema
- `GET /api/table/{session_id}/{table}/preview` - Preview table data

### Query
- `POST /api/query` - Execute natural language query

### Chats
- `POST /api/chats` - Create new chat
- `GET /api/chats` - List user's chats
- `GET /api/chats/{chat_id}/messages` - Get chat messages

## 🔒 Security Features

1. **Separate Databases**
   - App data in PostgreSQL (persistent)
   - User data in SQLite (temporary, isolated)

2. **Read-Only User Queries**
   - Only SELECT and WITH allowed
   - No INSERT/UPDATE/DELETE/DROP

3. **JWT Authentication**
   - Secure token-based auth
   - 7-day expiration

4. **Password Hashing**
   - bcrypt with salt

5. **Session Isolation**
   - Each user's uploaded DB is isolated
   - Automatic cleanup after 24 hours

## 🎓 Usage Examples

### 1. Basic Query
```
Question: "Show all students"
SQL: SELECT * FROM students
```

### 2. Filtering
```
Question: "Show students with score above 80"
SQL: SELECT * FROM students WHERE score > 80
```

### 3. Aggregation
```
Question: "Average score by department"
SQL: SELECT department, AVG(score) FROM students GROUP BY department
```

### 4. Joins (Multi-Table)
```
Question: "Show orders with customer names"
SQL: SELECT * FROM orders JOIN customers ON orders.customer_id = customers.id
```

## 🛠️ Development

### Database Migrations

```powershell
# Initialize database (auto-creates tables)
python -c "from database import init_db; init_db()"
```

### Run Backend Tests

```powershell
cd backend
python -c "import main; print('Backend modules loaded successfully')"
```

### Environment Variables

All configuration is in `.env`:
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET_KEY` - Secret for JWT tokens
- `HUGGING_FACE_TOKEN` - Optional for private models

## 🐛 Troubleshooting

### Database Connection Failed
- Check `DATABASE_URL` in `.env`
- Ensure PostgreSQL is running
- App falls back to local SQLite if PostgreSQL unavailable

### Model Loading Error
- Check internet connection (downloads from HuggingFace)
- Set `HUGGING_FACE_TOKEN` if using private models
- Use "Template-only (safe mode)" in settings

### Import Errors
- Ensure virtual environment is activated
- Run `pip install -e .` to install dependencies

## 📚 Tech Stack

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL
- **Frontend**: Streamlit, Plotly
- **AI/ML**: Transformers (T5), PyTorch
- **Auth**: JWT (python-jose), bcrypt
- **Database**: PostgreSQL (app), SQLite (user data)

## 📝 License

MIT License - see LICENSE file

## 👥 Contributors

Built for secure, multi-user natural language database queries.

---

**Note**: The frontend (Streamlit) works standalone without the backend. The backend provides additional features like centralized authentication, logging, and API access.
