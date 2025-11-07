# 🗄️ AskDB - Natural Language to SQL Query System

An AI-powered application that converts natural language questions into SQL queries using Hugging Face Transformers (T5 models). Built with Streamlit for an intuitive user interface.

## ✨ Features

- **🤖 AI-Powered SQL Generation**: Convert natural language questions to SQL using pre-trained T5 models
- **🎯 User-Friendly Interface**: See only results, not complex SQL code - perfect for non-technical users
- **📁 Flexible Database Support**: Upload CSV files or SQLite databases
- **🔍 Automatic Schema Extraction**: Intelligently extracts and displays database structure
- **🔒 Safe Query Execution**: Only read-only queries (SELECT, WITH/CTE) allowed for data protection
- **📊 Interactive Visualizations**: Automatic chart generation for numeric data using Plotly
- **💡 Natural Language Summaries**: AI-generated plain English explanations of query results
- **📜 Query History**: Track all your questions and results
- **⚡ Optimized Performance**: Model caching for faster inference

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- The following packages are already installed:
  - streamlit
  - transformers
  - torch
  - pandas
  - plotly
  - sentencepiece

### Running the Application

The application is configured to run automatically. Simply access it through the Replit webview on port 5000.

Alternatively, run manually:
```bash
streamlit run app.py --server.port 5000
```

## 📖 How to Use

1. **Upload Database**
   - Click "Browse files" in the sidebar
   - Upload a CSV file or SQLite database (.db, .sqlite, .sqlite3)
   - CSV files are automatically converted to SQLite

2. **View Schema**
   - Examine your database structure in the sidebar
   - See all tables and their columns

3. **Ask Questions**
   - Type your question in natural language
   - Examples:
     - "Show all records"
     - "What is the average score?"
     - "List students who scored above 90"
     - "Count records grouped by grade"

4. **Review Results**
   - Query results displayed in an easy-to-read table
   - Interactive visualizations (for numeric data)
   - Natural language summary explaining what the data shows
   - User-friendly error messages if something goes wrong

5. **Check History**
   - View all previous questions and their results in the "Query History" tab

## 🔧 Technical Details

### AI Models

**NL-to-SQL Generation:**
- Model: `cssupport/t5-small-awesome-text-to-sql`
- A fine-tuned T5 model specifically trained for text-to-SQL tasks
- Optimized for CPU inference
- Note: For complex schemas, consider upgrading to larger models like `t5-base` or domain-specific fine-tuned variants

**Result Summarization:**
- Model: `t5-small`
- Generates natural language summaries of query results
- Converts tabular data into readable English sentences

### Safety Features

- **SQL Privacy**: Generated SQL queries are never shown to users - only results are displayed
- **Query Validation**: Blocks all mutation operations (INSERT, UPDATE, DELETE, DROP, etc.)
- **Read-Only Access**: Only SELECT and WITH (CTE) queries permitted
- **User-Friendly Errors**: Error messages are sanitized to remove technical SQL content
- **SQL Injection Protection**: Queries are validated before execution

### Performance Optimizations

- **Model Caching**: Models loaded once and cached using `@st.cache_resource`
- **Efficient Schema Extraction**: Schema loaded only when database is uploaded
- **Lazy Loading**: Models loaded only when needed

## 📊 Sample Data

A sample CSV file (`sample_students.csv`) is included with student data for testing:
- 20 student records
- Columns: id, name, score, grade, subject

### Example Questions to Try

```
1. Show me all students who scored above 90
2. What is the average score by subject?
3. List all students with grade A
4. Count how many students are in each grade
5. Show the top 5 students by score
```

## 🏗️ Architecture

```
app.py
├── Database Handling
│   ├── CSV upload & conversion
│   ├── SQLite database loading
│   └── Schema extraction
│
├── AI Models
│   ├── T5 NL-to-SQL generation
│   └── T5 result summarization
│
├── Query Processing
│   ├── Prompt construction
│   ├── SQL generation
│   ├── Safety validation
│   └── Query execution
│
└── UI Components
    ├── Database upload sidebar
    ├── Question input
    ├── Results display
    ├── Visualizations
    └── Query history
```

## 🔮 Future Enhancements

Based on the original AskDB project roadmap:

1. **Model Fine-Tuning**
   - Fine-tune T5 on Spider dataset for improved accuracy
   - Train on DART/ToTTo for better summarization

2. **Advanced Features**
   - Support for JOIN operations and complex queries
   - Multi-step conversational query refinement
   - Query optimization suggestions

3. **Database Support**
   - PostgreSQL connection support
   - MySQL integration
   - Real-time database connections

4. **Deployment**
   - Hugging Face Spaces deployment
   - Custom domain support
   - API endpoint creation

## 📚 Project Background

This project implements Steps 0-8 of the AskDB roadmap using pre-trained Hugging Face models instead of custom fine-tuning. This approach provides:

- **Immediate Functionality**: Working prototype without GPU training time
- **Cost Efficiency**: No training infrastructure required
- **Flexibility**: Easy model swapping for experimentation
- **Foundation for Fine-Tuning**: Can be upgraded with custom models later

## 🤝 Contributing

To improve the application:

1. Experiment with different T5 models:
   - `t5-base` for better accuracy (larger model)
   - `google/flan-t5-large` for improved instruction following
   - Fine-tuned SQL-specific models from Hugging Face

2. Enhance SQL validation:
   - Add SQL parser for more robust validation
   - Support for additional safe operations

3. Improve UI/UX:
   - Add example questions gallery
   - Implement query suggestions
   - Save/export functionality for results

## 📄 License

This project uses open-source models and libraries. Please check individual model licenses on Hugging Face.

## 🙏 Acknowledgments

- **Hugging Face** for Transformers library and model hosting
- **T5 Model** by Google Research
- **Spider Dataset** by Yale LILY Lab (for future fine-tuning)
- **Streamlit** for the amazing web framework
