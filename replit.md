# Overview

AskDB is an AI-powered natural language to SQL query system that converts user questions into SQL queries using Hugging Face Transformers. It provides an interactive web interface built with Streamlit, enabling users to upload databases (CSV or SQLite), ask questions in plain English, and receive execution results, visualizations, and natural language summaries. The system prioritizes safe, read-only database operations and offers an intuitive experience for non-technical users to gain insights from their data without needing SQL knowledge. The generated SQL queries are never shown to users, only the results are displayed. The project aims to provide an accessible and powerful data exploration tool.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Application Framework
- **Frontend/UI Layer**: Streamlit-based web application (`app.py`) running on port 5000.
- **UI/UX Decisions**: Focus on an intuitive interface, interactive visualizations using Plotly, and clear presentation of results. Visual schema graph for multi-table databases. Chat history and per-user chat management.
- **Technical Implementations**: SQLite for in-memory/file-based data, automatic schema introspection, and interactive Plotly charts.
- **Feature Specifications**:
    - **Natural Language to SQL**: Converts English questions to SQL.
    - **Database Uploads**: Supports .db, .sqlite, .sqlite3, CSV, and Excel files.
    - **Result Display**: Shows query results, visualizations, and natural language explanations.
    - **Query Privacy**: Generated SQL is never shown to the user; only results and sanitized error messages.
    - **Read-only Enforcement**: Prevents data modification (INSERT, UPDATE, DELETE, DROP, ALTER).
    - **Multi-table Support**: Handles multiple uploaded files by merging into a single SQLite database, detects foreign key relationships, and supports multi-table JOINs.
    - **User Authentication**: Username/password authentication with persistent per-user chat history.
    - **SQL Explanation**: Converts SQL operations into plain English descriptions before displaying results.

## AI/ML Components
- **Model**: Hugging Face Transformers with T5 architecture for natural language to SQL conversion.
  - **Primary Model**: `mrm8488/t5-base-finetuned-wikiSQL`.
- **Implementation Details**:
  - Two-tier SQL generation: Template-based for common patterns (SHOW ALL, COUNT, AVERAGE, GROUP BY, FILTER), with AI model fallback for complex queries.
  - Model caching for performance.
  - Structured prompts with schema context (including column types and sample values) and few-shot examples for improved AI generation.
  - SQL output cleaning, validation, and comprehensive identifier quoting.
  - Value-aware template matching using distinct column values.
  - Intelligent post-processing and repair of AI-generated SQL to ensure validity.

## Data Layer
- **Database Engine**: SQLite for user-uploaded data.
- **Data Ingestion**: Supports SQLite files, CSV, and Excel files, automatically converting CSV/Excel to SQLite tables.
- **Schema Extraction**: Automatic introspection of database structure, including column types, sample values, and foreign key detection.

## Security Architecture
- **Query Privacy**: Generated SQL queries are never displayed to users; results, visualizations, and summaries are shown instead. Error messages are sanitized.
- **Query Validation**: Enforces read-only operations (SELECT, WITH/CTE only) to prevent data manipulation.
- **SQL Identifier Quoting**: Comprehensive quoting system for table and column names across all SQL generation to handle special characters and reserved keywords.

## Visualization Layer
- **Library**: Plotly for interactive charts, automatically generated for numeric query results.
- **Visual Schema Graph**: Interactive network graph of database tables and foreign key relationships using Plotly.

## State Management
- **Query History**: Session-based tracking of questions and generated SQL queries (without showing SQL).
- **User Session**: Streamlit session state tracks authenticated user and their chat history.

## Deployment Architecture
- **Runtime**: Python 3.11+.
- **Execution Environment**: Replit-based deployment.
- **Port Configuration**: Streamlit server configured for port 5000.

## System Design Choices
- **User Authentication & Multi-User Support**: Implemented using a PostgreSQL database for persistent user data and chat storage. Includes `users`, `chats`, and `messages` tables.
- **Chat Management**: Supports creating new chats, continuing previous conversations, and displaying per-user chat history.

# External Dependencies

## AI/ML Services
- **Hugging Face Transformers**: For NL-to-SQL models (e.g., `mrm8488/t5-base-finetuned-wikiSQL`). Requires `HUGGING_FACE_TOKEN` environment variable.

## Core Python Libraries
- **streamlit**: Web application framework.
- **transformers**: Hugging Face library for models.
- **torch**: PyTorch for model inference.
- **pandas**: Data manipulation.
- **plotly**: Interactive visualizations.
- **sentencepiece**: Tokenization.
- **bcrypt**: Password hashing.

## Databases
- **SQLite**: Built-in Python library for user-uploaded data.
- **PostgreSQL**: For persistent user authentication and chat history.

## Development Infrastructure
- **Replit**: Hosting and execution environment.
- **GitHub**: Version control.