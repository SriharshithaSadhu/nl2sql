"""
Comprehensive Test Suite for AskDB NL2SQL Application
Tests all features programmatically without requiring Streamlit UI interaction
"""

import os
import sys
import sqlite3
import pandas as pd
import tempfile
from typing import Dict, List

# Import core modules
import database
from core import (
    extract_schema,
    detect_foreign_keys,
    extract_enhanced_schema,
    format_schema_for_model,
    get_template_sql,
    get_join_template_sql,
    generate_sql,
    execute_sql,
    repair_sql,
    sanitize_error_message,
    explain_sql_query,
)


class TestRunner:
    """Test runner for AskDB features"""
    
    def __init__(self):
        self.results = []
        self.temp_db_path = None
        self.passed = 0
        self.failed = 0
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages"""
        prefix = {
            "INFO": "ℹ️",
            "PASS": "✅",
            "FAIL": "❌",
            "WARN": "⚠️"
        }
        print(f"{prefix.get(level, 'ℹ️')} {message}")
        
    def test(self, name: str, func, *args, **kwargs):
        """Run a single test"""
        try:
            self.log(f"Testing: {name}", "INFO")
            result = func(*args, **kwargs)
            if result:
                self.log(f"PASSED: {name}", "PASS")
                self.passed += 1
                return True
            else:
                self.log(f"FAILED: {name}", "FAIL")
                self.failed += 1
                return False
        except Exception as e:
            self.log(f"FAILED: {name} - {str(e)}", "FAIL")
            self.failed += 1
            return False
    
    def create_test_database(self) -> str:
        """Create a comprehensive test database with multiple tables and relationships"""
        temp_dir = tempfile.gettempdir()
        db_path = os.path.join(temp_dir, "test_nl2sql.sqlite")
        
        # Remove if exists
        if os.path.exists(db_path):
            os.remove(db_path)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create Students table
        cursor.execute("""
            CREATE TABLE students (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER,
                department TEXT,
                score REAL,
                grade TEXT
            )
        """)
        
        # Insert sample students
        students_data = [
            (1, "Alice Johnson", 20, "Computer Science", 92.5, "A"),
            (2, "Bob Smith", 21, "Mathematics", 88.0, "B"),
            (3, "Charlie Brown", 19, "Physics", 95.5, "A"),
            (4, "Diana Prince", 22, "Computer Science", 78.5, "C"),
            (5, "Eve Williams", 20, "Mathematics", 85.0, "B"),
            (6, "Frank Miller", 21, "Physics", 91.0, "A"),
            (7, "Grace Lee", 19, "Computer Science", 89.5, "B"),
            (8, "Henry Davis", 20, "Mathematics", 72.0, "C"),
        ]
        cursor.executemany("INSERT INTO students VALUES (?, ?, ?, ?, ?, ?)", students_data)
        
        # Create Courses table
        cursor.execute("""
            CREATE TABLE courses (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                credits INTEGER,
                department TEXT,
                instructor TEXT
            )
        """)
        
        courses_data = [
            (1, "Database Systems", 4, "Computer Science", "Dr. Smith"),
            (2, "Calculus II", 3, "Mathematics", "Dr. Johnson"),
            (3, "Quantum Mechanics", 4, "Physics", "Dr. Brown"),
            (4, "Machine Learning", 4, "Computer Science", "Dr. Davis"),
            (5, "Linear Algebra", 3, "Mathematics", "Dr. Wilson"),
        ]
        cursor.executemany("INSERT INTO courses VALUES (?, ?, ?, ?, ?)", courses_data)
        
        # Create Enrollments table (junction table with foreign keys)
        cursor.execute("""
            CREATE TABLE enrollments (
                id INTEGER PRIMARY KEY,
                student_id INTEGER,
                course_id INTEGER,
                semester TEXT,
                grade TEXT,
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (course_id) REFERENCES courses(id)
            )
        """)
        
        enrollments_data = [
            (1, 1, 1, "Fall 2024", "A"),
            (2, 1, 4, "Fall 2024", "A"),
            (3, 2, 2, "Fall 2024", "B"),
            (4, 3, 3, "Fall 2024", "A"),
            (5, 4, 1, "Fall 2024", "C"),
            (6, 5, 2, "Fall 2024", "B"),
            (7, 6, 3, "Fall 2024", "A"),
            (8, 7, 4, "Fall 2024", "B"),
        ]
        cursor.executemany("INSERT INTO enrollments VALUES (?, ?, ?, ?, ?)", enrollments_data)
        
        conn.commit()
        conn.close()
        
        self.temp_db_path = db_path
        return db_path
    
    def test_database_creation(self):
        """Test 1: Database creation and schema extraction"""
        db_path = self.create_test_database()
        if not os.path.exists(db_path):
            return False
        
        # Test schema extraction
        schema = extract_schema(db_path)
        if len(schema) != 3:  # Should have 3 tables
            return False
        
        if "students" not in schema or "courses" not in schema or "enrollments" not in schema:
            return False
        
        self.log(f"  Tables found: {list(schema.keys())}", "INFO")
        return True
    
    def test_foreign_key_detection(self):
        """Test 2: Foreign key relationship detection"""
        fks = detect_foreign_keys(self.temp_db_path)
        
        # Should detect FKs in enrollments table
        if "enrollments" not in fks:
            return False
        
        enrollment_fks = fks["enrollments"]
        if len(enrollment_fks) < 2:
            return False
        
        self.log(f"  Foreign keys detected: {len(enrollment_fks)}", "INFO")
        return True
    
    def test_enhanced_schema(self):
        """Test 3: Enhanced schema with sample values"""
        enhanced = extract_enhanced_schema(self.temp_db_path)
        
        if "students" not in enhanced:
            return False
        
        students_cols = enhanced["students"]["columns"]
        if "name" not in students_cols:
            return False
        
        # Check if samples were extracted
        name_samples = students_cols["name"].get("samples", [])
        if len(name_samples) == 0:
            return False
        
        self.log(f"  Sample values for 'name': {name_samples[:3]}", "INFO")
        return True
    
    def test_template_simple_queries(self):
        """Test 4: Template-based SQL generation for simple queries"""
        schema = extract_schema(self.temp_db_path)
        columns = schema["students"]
        
        test_queries = [
            ("Show all students", "SELECT * FROM"),
            ("Count students", "COUNT(*)"),
            ("Average score", "AVG"),
            ("Students where score greater than 90", "WHERE"),
        ]
        
        for question, expected_keyword in test_queries:
            sql = get_template_sql(question, "students", columns, self.temp_db_path)
            if sql and expected_keyword in sql:
                self.log(f"  ✓ '{question}' → {sql[:60]}...", "INFO")
            else:
                self.log(f"  ✗ Failed to generate SQL for: {question}", "WARN")
                return False
        
        return True
    
    def test_template_aggregation_queries(self):
        """Test 5: Template-based aggregation queries"""
        schema = extract_schema(self.temp_db_path)
        columns = schema["students"]
        
        test_queries = [
            ("Average score by department", "AVG", "GROUP BY"),
            ("Count students by grade", "COUNT", "GROUP BY"),
            ("Total score", "SUM"),
        ]
        
        for query_tuple in test_queries:
            question = query_tuple[0]
            expected_keywords = query_tuple[1:]
            
            sql = get_template_sql(question, "students", columns, self.temp_db_path)
            if sql and all(kw in sql for kw in expected_keywords):
                self.log(f"  ✓ '{question}' → {sql[:60]}...", "INFO")
            else:
                self.log(f"  ✗ Failed: {question}", "WARN")
                return False
        
        return True
    
    def test_value_aware_filtering(self):
        """Test 6: Value-aware filtering using sample data"""
        schema = extract_schema(self.temp_db_path)
        columns = schema["students"]
        
        # Query with specific value from data
        question = "Show all Computer Science students"
        sql = get_template_sql(question, "students", columns, self.temp_db_path)
        
        if sql and ("Computer Science" in sql or "department" in sql):
            self.log(f"  ✓ Value-aware query: {sql[:70]}...", "INFO")
            return True
        else:
            self.log(f"  ✗ Failed value-aware filtering", "WARN")
            return False
    
    def test_join_queries(self):
        """Test 7: Multi-table JOIN query generation"""
        schema = extract_schema(self.temp_db_path)
        all_columns = schema
        fks = detect_foreign_keys(self.temp_db_path)
        
        question = "Show students with their courses"
        related_tables = ["students", "courses"]
        
        sql = get_join_template_sql(question, related_tables, all_columns, fks, self.temp_db_path)
        
        if sql and "JOIN" in sql:
            self.log(f"  ✓ JOIN query: {sql[:80]}...", "INFO")
            return True
        else:
            self.log(f"  ✗ Failed JOIN generation", "WARN")
            return False
    
    def test_sql_execution(self):
        """Test 8: SQL execution and result retrieval"""
        test_queries = [
            "SELECT * FROM students WHERE score > 90",
            "SELECT COUNT(*) as total FROM students",
            "SELECT department, AVG(score) as avg_score FROM students GROUP BY department",
        ]
        
        for sql in test_queries:
            df, error = execute_sql(sql, self.temp_db_path)
            if df is not None and error is None:
                self.log(f"  ✓ Executed: {sql[:60]}... → {len(df)} rows", "INFO")
            else:
                self.log(f"  ✗ Failed: {sql} - {error}", "WARN")
                return False
        
        return True
    
    def test_safety_restrictions(self):
        """Test 9: SQL safety restrictions (prevent dangerous queries)"""
        dangerous_queries = [
            "DROP TABLE students",
            "DELETE FROM students WHERE id = 1",
            "INSERT INTO students VALUES (99, 'Hacker', 20, 'CS', 100, 'A')",
            "UPDATE students SET score = 100 WHERE id = 1",
        ]
        
        for sql in dangerous_queries:
            df, error = execute_sql(sql, self.temp_db_path)
            if df is None and error is not None:
                self.log(f"  ✓ Blocked dangerous query: {sql[:50]}...", "INFO")
            else:
                self.log(f"  ✗ SECURITY ISSUE: Dangerous query was NOT blocked!", "WARN")
                return False
        
        return True
    
    def test_error_handling(self):
        """Test 10: Error handling and sanitization"""
        bad_queries = [
            "SELECT nonexistent_column FROM students",
            "SELECT * FROM nonexistent_table",
            "SELECT * FROM students WHERE",  # Incomplete query
        ]
        
        for sql in bad_queries:
            df, error = execute_sql(sql, self.temp_db_path)
            if error is not None:
                sanitized = sanitize_error_message(error)
                self.log(f"  ✓ Error handled: {sanitized[:60]}", "INFO")
            else:
                self.log(f"  ✗ Error not caught for: {sql}", "WARN")
                return False
        
        return True
    
    def test_sql_repair(self):
        """Test 11: SQL repair and validation"""
        schema = extract_schema(self.temp_db_path)
        columns = schema["students"]
        
        broken_sqls = [
            "A: SELECT * FROM table",  # Has artifact prefix
            "SELECT bad_column FROM students",  # Invalid column
            "CREATE TABLE test (id INT)",  # Wrong query type
        ]
        
        for sql in broken_sqls:
            repaired = repair_sql(sql, "students", columns)
            if repaired.startswith("SELECT"):
                self.log(f"  ✓ Repaired: {sql[:40]} → {repaired[:40]}", "INFO")
            else:
                self.log(f"  ✗ Repair failed for: {sql}", "WARN")
                return False
        
        return True
    
    def test_explain_sql(self):
        """Test 12: SQL explanation and insights extraction"""
        schema = extract_schema(self.temp_db_path)
        
        test_cases = [
            ("SELECT * FROM students WHERE score > 90", {"tables": ["students"]}),
            ("SELECT COUNT(*) FROM students", {"aggregations": ["COUNT"]}),
            ("SELECT * FROM students JOIN courses ON students.id = courses.id", {"has_join": True}),
        ]
        
        for sql, expected in test_cases:
            insights = explain_sql_query(sql, schema)
            
            for key, value in expected.items():
                if key == "has_join":
                    if insights.get(key) != value:
                        return False
                elif isinstance(value, list):
                    if not any(v in insights.get(key, []) for v in value):
                        return False
            
            self.log(f"  ✓ Explained: {sql[:50]}...", "INFO")
        
        return True
    
    def test_database_auth(self):
        """Test 13: User authentication database"""
        # Initialize auth database
        if not database.init_db():
            self.log("  ✗ Failed to initialize auth database", "WARN")
            return False
        
        # Create test user
        test_username = f"test_user_{os.getpid()}"
        user = database.create_user(
            username=test_username,
            email=f"{test_username}@test.com",
            password="test_password_123",
            display_name="Test User"
        )
        
        if not user:
            self.log("  ✗ Failed to create user", "WARN")
            return False
        
        # Test authentication
        auth_user = database.authenticate_user(test_username, "test_password_123")
        if not auth_user:
            self.log("  ✗ Failed to authenticate user", "WARN")
            return False
        
        # Test wrong password
        wrong_auth = database.authenticate_user(test_username, "wrong_password")
        if wrong_auth:
            self.log("  ✗ Wrong password was accepted!", "WARN")
            return False
        
        self.log(f"  ✓ User authentication working correctly", "INFO")
        return True
    
    def test_chat_management(self):
        """Test 14: Chat and message management"""
        # Create a test user first
        test_username = f"chat_user_{os.getpid()}"
        user = database.create_user(
            username=test_username,
            email=f"{test_username}@test.com",
            password="test123",
            display_name="Chat Test User"
        )
        
        if not user:
            return False
        
        # Create a chat
        chat = database.create_chat(user.id, "Test Conversation")
        if not chat:
            return False
        
        # Add messages
        msg1 = database.add_message(chat.id, "user", "Show all students", sql_query="SELECT * FROM students", rows_returned=8, success=True)
        msg2 = database.add_message(chat.id, "assistant", "Found 8 students", rows_returned=8, success=True)
        
        if not msg1 or not msg2:
            return False
        
        # Retrieve messages
        messages = database.get_chat_messages(chat.id)
        if len(messages) != 2:
            return False
        
        self.log(f"  ✓ Chat management working correctly", "INFO")
        return True
    
    def test_end_to_end_query_flow(self):
        """Test 15: End-to-end query flow (question → SQL → execution)"""
        schema = extract_schema(self.temp_db_path)
        schema_str = format_schema_for_model(schema)
        
        test_questions = [
            "Show all students",
            "Count students by department",
            "Average score in Computer Science",
            "Students with score greater than 90",
        ]
        
        for question in test_questions:
            # Generate SQL (using templates only, no AI model)
            sql = generate_sql(question, schema_str, None, None, self.temp_db_path)
            
            # Execute SQL
            df, error = execute_sql(sql, self.temp_db_path)
            
            if df is not None and error is None:
                self.log(f"  ✓ '{question}' → {len(df)} rows", "INFO")
            else:
                self.log(f"  ✗ Failed: {question} - {error}", "WARN")
                return False
        
        return True
    
    def run_all_tests(self):
        """Run all test cases"""
        self.log("=" * 60, "INFO")
        self.log("Starting AskDB Feature Test Suite", "INFO")
        self.log("=" * 60, "INFO")
        
        # Run tests
        self.test("Database Creation & Schema Extraction", self.test_database_creation)
        self.test("Foreign Key Detection", self.test_foreign_key_detection)
        self.test("Enhanced Schema with Sample Values", self.test_enhanced_schema)
        self.test("Template-based Simple Queries", self.test_template_simple_queries)
        self.test("Template-based Aggregation Queries", self.test_template_aggregation_queries)
        self.test("Value-Aware Filtering", self.test_value_aware_filtering)
        self.test("Multi-table JOIN Queries", self.test_join_queries)
        self.test("SQL Execution & Results", self.test_sql_execution)
        self.test("Safety Restrictions", self.test_safety_restrictions)
        self.test("Error Handling & Sanitization", self.test_error_handling)
        self.test("SQL Repair & Validation", self.test_sql_repair)
        self.test("SQL Explanation & Insights", self.test_explain_sql)
        self.test("User Authentication", self.test_database_auth)
        self.test("Chat & Message Management", self.test_chat_management)
        self.test("End-to-End Query Flow", self.test_end_to_end_query_flow)
        
        # Summary
        self.log("=" * 60, "INFO")
        self.log(f"Test Summary: {self.passed} passed, {self.failed} failed", "INFO")
        self.log("=" * 60, "INFO")
        
        # Cleanup
        if self.temp_db_path and os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
                self.log("Cleaned up test database", "INFO")
            except:
                pass
        
        return self.failed == 0


def main():
    """Main entry point"""
    runner = TestRunner()
    success = runner.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! The AskDB application is working correctly.")
        return 0
    else:
        print(f"\n⚠️ Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
