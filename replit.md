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
- **Enhanced Schema Extraction**:
  - Extracts column types and sample values
  - Provides rich context to AI model
  - Helps model understand data patterns
- **Few-Shot Prompting**:
  - Structured prompts with examples
  - Table and column details with types
  - Better generation parameters (temperature, top_p, repetition penalty)
- **SQL Repair & Validation**:
  - Intelligent post-processing of AI output
  - Regex-based column name quoting
  - Artifact removal and table reference fixing
  - Ensures all identifiers properly quoted
- **Template Fast-Path** (optional optimization):
  - SHOW ALL, COUNT, AVERAGE, GROUP BY, FILTER patterns
  - Used only when pattern matches exactly
  - Falls through to AI for everything else

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

### Testing & Validation
- Comprehensive end-to-end testing completed with Playwright
- Verified SQL privacy across all user interactions
- Confirmed template and AI-based query generation working correctly
- Tested with diverse databases (orders, customers, products)
- Verified upload history and chat history features
- Architect-approved implementation meeting all requirements

## Future Architectural Considerations
The `attached_assets` folder references a planned multi-tier architecture with:
- Separate backend (FastAPI) and frontend directories
- Model training infrastructure (Colab notebook references)
- Spider dataset integration for fine-tuning
- Virtual environment setup with additional dependencies (FastAPI, uvicorn)

**Note**: The current implementation is a streamlined Streamlit monolith optimized for single-user data exploration, while project notes suggest evolution toward a decoupled FastAPI backend architecture for multi-user deployment.