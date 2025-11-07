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
- **Rationale**: T5 (Text-to-Text Transfer Learning) models are pre-trained and proven effective for sequence-to-sequence tasks like translation from natural language to structured queries
- **Implementation Details**:
  - Model caching implemented for performance optimization
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
- **Query Validation**: Read-only query enforcement (SELECT, WITH/CTE statements only)
- **Rationale**: Prevents data modification, deletion, or schema changes to protect data integrity
- **Implementation**: Query filtering before execution to block INSERT, UPDATE, DELETE, DROP, ALTER operations

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
  - No API key required for publicly available models
  - Models cached locally after first download

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

## Future Architectural Considerations
The `attached_assets` folder references a planned multi-tier architecture with:
- Separate backend (FastAPI) and frontend directories
- Model training infrastructure (Colab notebook references)
- Spider dataset integration for fine-tuning
- Virtual environment setup with additional dependencies (FastAPI, uvicorn)

**Note**: The current implementation is a streamlined Streamlit monolith, while the project notes suggest evolution toward a decoupled FastAPI backend architecture.