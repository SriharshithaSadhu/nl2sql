# Overview

AskDB is an AI-powered natural language to SQL query system that converts user questions into SQL queries using Hugging Face Transformers (specifically T5 models). The application provides an interactive web interface built with Streamlit, allowing users to upload databases (CSV or SQLite), ask questions in plain English, and receive execution results, visualizations, and natural language summaries.

**Key Design Principle**: The generated SQL queries are NEVER shown to users. Only results are displayed, making the system perfect for non-technical users who want insights from their data without needing to know SQL.

The system focuses on safe, read-only database operations and provides an intuitive interface for non-technical users to explore data through natural language.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Application Framework
- **Frontend/UI Layer**: Streamlit-based web application (`app.py`) running on port 5000
- **Rationale**: Streamlit provides rapid development of data-focused applications with minimal boilerplate, ideal for prototyping and interactive data exploration tools
- **Trade-offs**: Limited customization compared to full frontend frameworks, but significantly faster development time for data science applications

## AI/ML Components
- **Model**: Hugging Face Transformers with T5 architecture for natural language to SQL conversion
  - **Primary Model**: `mrm8488/t5-base-finetuned-wikiSQL` - T5-base model fine-tuned on WikiSQL dataset
  - **Previous Model**: Upgraded from `cssupport/t5-small-awesome-text-to-sql` for improved accuracy
- **Rationale**: T5 (Text-to-Text Transfer Learning) models are pre-trained and proven effective for sequence-to-sequence tasks like translation from natural language to structured queries
- **Implementation Details**:
  - Two-tier SQL generation pipeline:
    1. **Template-based generation**: Fast, reliable SQL for common query patterns (SHOW ALL, COUNT, AVERAGE, GROUP BY, FILTER)
    2. **AI model fallback**: Handles complex queries using WikiSQL-trained T5 model
  - Model caching implemented for performance optimization
  - Structured prompts with schema context for better AI generation
  - SQL output cleaning and validation
  - Inference pipeline uses PyTorch backend
  - SentencePiece tokenizer for text preprocessing

## Data Layer
- **Database Engine**: SQLite for in-memory/file-based data storage
- **Data Ingestion**: Supports two input formats:
  1. Direct SQLite database uploads (.db, .sqlite, .sqlite3)
  2. CSV files with automatic conversion to SQLite
- **Rationale**: SQLite provides zero-configuration, serverless operation suitable for single-user applications and prototyping
- **Schema Extraction**: Automatic introspection of database structure to provide context for query generation

## Security Architecture
- **Query Privacy**: Generated SQL queries are NEVER displayed to users
  - Results, visualizations, and summaries shown instead
  - Error messages sanitized to remove SQL content using `sanitize_error_message()`
  - Query history shows questions and status, NOT the generated SQL
- **Query Validation**: Read-only query enforcement (SELECT, WITH/CTE statements only)
- **Rationale**: Prevents data modification, deletion, or schema changes to protect data integrity
- **Implementation**: Query filtering before execution to block INSERT, UPDATE, DELETE, DROP, ALTER operations
- **Safe User Experience**: Non-technical users get insights without SQL knowledge

## Visualization Layer
- **Library**: Plotly for interactive charts
- **Rationale**: Plotly provides rich, interactive visualizations with minimal configuration, suitable for dynamic data exploration
- **Trigger**: Automatic chart generation when query results contain numeric data

## State Management
- **Query History**: Session-based tracking of questions and generated SQL queries
- **Implementation**: Streamlit's session state mechanism for maintaining application state across reruns

## Deployment Architecture
- **Runtime**: Python 3.11+
- **Execution Environment**: Replit-based deployment with automatic startup
- **Port Configuration**: Configured for port 5000 with Streamlit server

# External Dependencies

## AI/ML Services
- **Hugging Face Transformers**: Pre-trained T5 models for NL-to-SQL conversion
  - Current model: `mrm8488/t5-base-finetuned-wikiSQL`
  - Requires Hugging Face token for model access (stored in `HUGGING_FACE_TOKEN` environment variable)
  - Models cached locally after first download for faster inference

## Core Python Libraries
- **streamlit**: Web application framework and UI components
- **transformers**: Hugging Face library for accessing pre-trained models
- **torch**: PyTorch deep learning framework (backend for model inference)
- **pandas**: Data manipulation and analysis
- **plotly**: Interactive visualization library
- **sentencepiece**: Tokenization library for transformer models

## Database
- **SQLite**: Built-in Python library, no external service required
- File-based or in-memory database operations

## Development Infrastructure
- **Replit**: Hosting and execution environment
- **GitHub**: Version control (repository initialization mentioned in project setup notes)

## Recent Changes (November 2025)

### Model Upgrade
- Upgraded from `cssupport/t5-small-awesome-text-to-sql` to `mrm8488/t5-base-finetuned-wikiSQL`
- Added Hugging Face authentication token support
- Improved model prompting with structured schema context

### AI-First Dynamic SQL Generation (November 11, 2025)
- **Primary Strategy**: Enhanced AI model with few-shot prompting
  - T5 model (WikiSQL fine-tuned) as main query generator
  - Templates retained as fast-path optimization only
  - Handles ANY query type dynamically like an "SQL master"
  - **Guaranteed AI fallback** for unmatched queries
  
- **Value-Aware Template Matching**:
  - Extracts up to 50 distinct values per column from database
  - Builds value→column mapping for intelligent matching
  - **Exact matching**: "Science" → `WHERE "subject" = 'Science'`
  - **Partial matching**: "Maths" → `WHERE "subject" LIKE '%Mathematics%'`
  - Handles user queries with VALUES instead of COLUMN NAMES
  - Falls back to AI when value not in samples
  
- **Enhanced Schema Extraction**:
  - Extracts column types and up to 50 sample values per column
  - Provides rich context to both templates and AI model
  - Helps AI understand data patterns and generate accurate SQL
  
- **Few-Shot Prompting**:
  - Structured prompts with examples
  - Table and column details with types and sample values
  - Better generation parameters (temperature, top_p, repetition penalty)
  
- **SQL Repair & Validation**:
  - Intelligent post-processing of AI output
  - Regex-based column name quoting (skips already-quoted)
  - Artifact removal and table reference fixing
  - Ensures all identifiers properly quoted
  
- **Smart Template Fast-Path**:
  - SHOW ALL (only genuine requests), COUNT, AVERAGE, GROUP BY
  - Value-aware FILTER (exact + partial matching)
  - Returns None when unsure → falls back to AI
  - Never blocks AI fallback incorrectly

### Enhanced for Diverse Databases (November 11, 2025)
- **Expanded aggregation keywords** to support diverse business databases:
  - Added: price, cost, total, quantity, revenue, sales, profit, discount, tax, fee, charge, payment, balance, rate
  - Supports orders, customers, products, and any business domain databases
- **Upload History Tracking**:
  - Tracks all uploaded files with metadata (filename, type, rows, columns, timestamp)
  - Displays last 5 uploads in sidebar
  - Complete metadata for CSV, Excel, and SQLite files
- **Full Chat History**:
  - Three-tab interface: Ask Question, Chat History, Query History
  - Chat history shows complete conversation flow with timestamps
  - Displays questions, answers, row counts, and result previews
  - Preserves all interactions in session

### SQL Identifier Quoting (November 11, 2025)
- **Comprehensive quoting system** for table and column names:
  - Shared `quote_identifier()` function ensures consistent quoting
  - Handles tables/columns with spaces (e.g., "Order Details")
  - Escapes reserved SQL keywords
  - Properly escapes embedded quotes by doubling
- **Applied across all SQL generation**:
  - Template-based queries quote all identifiers
  - AI fallback quotes identifiers in prompts and post-processing
  - Schema extraction uses quoted table names
  - Upload metadata collection uses quoted table names
- **Error handling**: Try/except per table prevents cascading failures

### SQL Privacy Enhancement
- Completely removed "Generated SQL Query" display section
- Added `sanitize_error_message()` to strip SQL from all error messages
- Query history shows questions and status only, never SQL code
- Maintains server-side SQL logging for debugging while hiding from UI

### AI Model SQL Generation Fixes (November 11, 2025)
- **Regex-based table placeholder replacement**: Uses word-boundary regex `\bFROM\s+table\b` to catch AI-generated "table" placeholder regardless of trailing characters
- **Schema-driven prompting**: Dynamically builds few-shot examples using ACTUAL column names from database instead of generic placeholders
- **Explicit anti-hallucination instruction**: Prompt includes "Never use the word 'table' as a placeholder" to prevent AI from generating invalid SQL
- **Column whitelist validation**: Post-generation check removes hallucinated columns, falls back to SELECT * while preserving WHERE clauses
- **Resolved critical bugs**: Fixed "syntax error near 'table'" issues that blocked complex queries

### Multi-Table Upload Support (November 11, 2025)
- **Multiple file upload**: Accept multiple CSV, Excel, and SQLite files simultaneously
- **Unified database**: Merges all uploaded files into single SQLite database with separate tables
- **SQLite file handling**: Attaches source databases and copies tables using proper quoting
- **Smart table naming**: Cleans filenames to create valid table names (replaces spaces, dashes, dots with underscores)
- **Comprehensive feedback**: Shows success message listing all created tables
- **Foreign key detection**: Automatic discovery of relationships using PRAGMA foreign_key_list + heuristic matching
- **Heuristic matching**: Detects implicit relationships (e.g., "customer_id" → "customers" table)
- **Table name detection**: Identifies which table is mentioned in question
- **Multi-table schema in prompts**: AI receives information about all available tables and their relationships
- **Limitation**: Full cross-table JOIN queries currently limited to single-table context in SQL repair pipeline

### Testing & Validation (November 12, 2025)
- **Comprehensive 50+ question test suite** completed with multi-table upload
- Verified SQL privacy across all user interactions
- Confirmed template and AI-based query generation working correctly  
- Fixed all "syntax error near table/Order" issues - AI now generates valid SQL
- Tested multi-table upload functionality with 4 related tables
- Verified all aggregation types (SUM, AVG, COUNT, MAX, MIN) working correctly
- Architect-approved implementation meeting all requirements

### Bug Fixes from Comprehensive Testing (November 12, 2025)
1. **Table Name Syntax Errors**: Fixed "syntax error near 'Order'" by adding table name variation handling (singular/plural, case variations) with proper quoting
2. **Table Detection**: Enhanced to remove prefixes ("sample_") and match singular/plural forms ("order" → "sample_orders")
3. **SUM/Revenue Queries**: Added dedicated SUM template for "total", "revenue", "sum" keywords with automatic numeric column detection
4. **"How Many" Queries**: Extended COUNT template to handle "how many", "number of", "total number" phrasings
5. **AI Prompt Quality**: Added SUM few-shot example and explicit syntax instructions to prevent malformed SQL
6. **SQL Repair Robustness**: Improved column quoting to be more conservative and avoid false matches

## User Authentication & Multi-User Support (November 12, 2025)
- **PostgreSQL Database**: Created for persistent user data and chat storage
- **User Management**: Username/password authentication with bcrypt password hashing
- **Database Schema**:
  - `users` table: id, username, email, password_hash, display_name, created_at
  - `chats` table: id, user_id (FK), title, created_at, updated_at
  - `messages` table: id, chat_id (FK), role, content, sql_query, rows_returned, success, created_at
- **Signup/Signin UI**: Tab-based interface for new user registration and existing user login
- **Session Management**: Streamlit session state tracks authenticated user
- **Per-User Chat History**: Each user sees only their own conversations
- **Chat Management**:
  - Create new chats (➕ New Chat button)
  - Continue previous chats (click chat from sidebar list)
  - Auto-saves all questions and answers to database
  - Displays last 10 chats in sidebar
- **Logout Functionality**: Secure logout that clears session
- **SQL Privacy Maintained**: Generated SQL stored server-side but never shown to users

## Recent Feature Additions (November 12, 2025)

### Multi-Table JOIN Support (COMPLETED ✅)
- **FK-Driven Detection**: Three-tier detection using explicit mentions, FK + column references, and intent keywords
- **JOIN Template Generation**: `get_join_template_sql()` creates bidirectional FK-based JOINs for 2-3 table queries
- **AI Prompt Enhancement**: Multi-table schema with FK relationships and dynamic JOIN examples
- **Multi-Table Aware SQL Repair**: `repair_sql()` updated with `all_columns` dict and `is_multi_table` flag
  - Preserves JOIN structure by skipping aggressive validation for JOIN queries
  - Maintains single-table safety with column whitelist validation
- **Architecture Decision**: Template-based for simple JOINs, AI handles complex cases with proper validation

### SQL→English Query Explanation (COMPLETED ✅)
- **Function**: `explain_sql_query()` converts SQL operations to plain English descriptions
- **What It Detects**:
  - Aggregations (COUNT, AVG, SUM, MAX, MIN)
  - Multi-table JOINs with involved tables
  - Filtering conditions (WHERE clauses)
  - Grouping and sorting operations
  - LIMIT constraints
- **Privacy Maintained**: Never exposes SQL code, only operation descriptions
- **UI Integration**: Displayed before query results in "🔍 What This Query Does" section
- **Example**: "This query combines data from 2 related tables: orders, customers. It counts the number of matching records. Results are filtered based on your specified conditions."

### Visual Schema Graph (COMPLETED ✅)
- **Interactive Network Graph**: Plotly-based visualization showing database structure
- **Nodes**: Tables positioned in circular layout with hover details (columns, counts)
- **Edges**: Foreign key relationships with directional arrows
- **Features**:
  - Automatic FK detection using `detect_foreign_keys()`
  - Interactive hover showing table columns (first 10)
  - Relationship details in expandable section
  - Responsive sizing based on table count
- **UI Integration**: Sidebar "Database Schema" section, shown only for multi-table databases
- **Visual Design**: Blue nodes with white borders, gray relationship edges, transparent background

## Future Architectural Considerations
- **Advanced Chat Features**: Chat deletion, renaming, search across chat history
- **Model Training**: Spider dataset integration for fine-tuning SQL generation
- **Enhanced JOIN Support**: Hub-and-spoke join patterns, complex multi-table aggregations
- **Query Optimization**: Caching frequently used queries, query plan analysis