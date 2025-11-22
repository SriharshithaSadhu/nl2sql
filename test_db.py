"""Test database connection"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from database import init_db, create_user, create_chat, add_message

print("\n=== Testing Database Connection ===\n")

# Test 1: Initialize database
print("1. Initializing database...")
result = init_db()
if result:
    print("   ✓ Database tables created successfully!")
    db_url = os.getenv("DATABASE_URL", "")
    if "postgresql" in db_url:
        print(f"   ✓ Using PostgreSQL: {db_url[:60]}...")
    else:
        print("   ℹ Using local SQLite fallback")
else:
    print("   ✗ Database initialization failed")
    exit(1)

# Test 2: Create a test user
print("\n2. Creating test user...")
try:
    user = create_user(
        username="testuser",
        email="test@example.com",
        password="testpassword123",
        display_name="Test User"
    )
    if user:
        print(f"   ✓ User created: {user.username} (ID: {user.id})")
    else:
        print("   ℹ User already exists (this is OK)")
        # Try to authenticate instead
        from database import authenticate_user
        user = authenticate_user("testuser", "testpassword123")
        if user:
            print(f"   ✓ Authenticated existing user: {user.username} (ID: {user.id})")
        else:
            print("   ✗ Could not create or authenticate user")
            exit(1)
except Exception as e:
    print(f"   ✗ Error: {e}")
    exit(1)

# Test 3: Create a chat
print("\n3. Creating test chat...")
try:
    chat = create_chat(user.id, "Test Conversation")
    if chat:
        print(f"   ✓ Chat created: {chat.title} (ID: {chat.id})")
    else:
        print("   ✗ Could not create chat")
        exit(1)
except Exception as e:
    print(f"   ✗ Error: {e}")
    exit(1)

# Test 4: Add a message
print("\n4. Adding test message...")
try:
    msg = add_message(
        chat_id=chat.id,
        role="user",
        content="Show all records",
        sql_query="SELECT * FROM test",
        rows_returned=10,
        success=True
    )
    if msg:
        print(f"   ✓ Message added (ID: {msg.id})")
    else:
        print("   ✗ Could not add message")
        exit(1)
except Exception as e:
    print(f"   ✗ Error: {e}")
    exit(1)

print("\n=== All Tests Passed! ===\n")
print("Your database is working correctly!")
print("✓ PostgreSQL connection" if "postgresql" in os.getenv("DATABASE_URL", "") else "ℹ SQLite fallback")
print("✓ User management")
print("✓ Chat management")
print("✓ Message storage")
print("\nReady to use!")
