import sqlite3

# Connect to SQLite (creates file if not exists)
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Create table
cursor.execute("""
CREATE TABLE IF NOT EXISTS urls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    long_url TEXT NOT NULL,
    short_code TEXT UNIQUE NOT NULL,
    clicks INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Create index for fast lookup (important for scalability)
cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_short_code
ON urls(short_code)
""")

conn.commit()
conn.close()

print("Database and table created successfully.")
