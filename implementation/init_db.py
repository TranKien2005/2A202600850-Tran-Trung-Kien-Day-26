import os
import sqlite3

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    cohort TEXT NOT NULL,
    score REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    instructor TEXT NOT NULL,
    credits INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    grade TEXT,
    score REAL,
    FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
);
"""

SEED_SQL = """
-- Insert Students
INSERT OR IGNORE INTO students (id, name, email, cohort, score) VALUES 
(1, 'Alice Nguyen', 'alice@example.com', 'A1', 85.5),
(2, 'Bob Tran', 'bob@example.com', 'A1', 72.0),
(3, 'Charlie Le', 'charlie@example.com', 'B2', 91.2),
(4, 'David Pham', 'david@example.com', 'B2', 65.4),
(5, 'Eva Vu', 'eva@example.com', 'A1', 88.0);

-- Insert Courses
INSERT OR IGNORE INTO courses (id, name, instructor, credits) VALUES
(1, 'Python Programming', 'Dr. Smith', 3),
(2, 'Database Systems', 'Prof. Davis', 4),
(3, 'Machine Learning', 'Dr. Adams', 3);

-- Insert Enrollments
INSERT OR IGNORE INTO enrollments (student_id, course_id, grade, score) VALUES
(1, 1, 'A', 90.0),
(1, 2, 'B+', 82.0),
(2, 1, 'B', 72.0),
(3, 1, 'A+', 95.0),
(3, 3, 'A', 89.0),
(4, 2, 'C', 65.4),
(5, 3, 'A-', 88.0);
"""

def create_database(db_path="school.db"):
    """
    Creates and seeds the SQLite database.
    """
    # Resolve absolute path relative to the directory containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    abs_db_path = os.path.join(script_dir, db_path)
    
    print(f"Creating database at: {abs_db_path}")
    conn = sqlite3.connect(abs_db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    
    try:
        cursor = conn.cursor()
        # Enable multiple statements execution using executescript
        cursor.executescript(SCHEMA_SQL)
        cursor.executescript(SEED_SQL)
        conn.commit()
        print("Database initialized and seeded successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Error initializing database: {e}")
        raise e
    finally:
        conn.close()
        
    return abs_db_path

if __name__ == "__main__":
    create_database()
