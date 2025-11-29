import sqlite3
from flask import g
import os

DB_NAME = os.path.join(os.path.dirname(__file__), "smartpath.db")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_NAME)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    c = db.cursor()

    # USERS
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student','mentor'))
    )
    """)

    # QUESTIONS (smart/bank questions)
    c.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        question TEXT NOT NULL,
        option_a TEXT,
        option_b TEXT,
        option_c TEXT,
        option_d TEXT,
        correct_option TEXT NOT NULL
    )
    """)

    # QUIZ ATTEMPTS (track source: bank/manual)
    c.execute("""
    CREATE TABLE IF NOT EXISTS quiz_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        is_correct INTEGER NOT NULL,
        source TEXT NOT NULL DEFAULT 'bank',
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # ASSIGNMENTS
    c.execute("""
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        due_date TEXT
    )
    """)

    # ASSIGNMENT SUBMISSIONS
    c.execute("""
    CREATE TABLE IF NOT EXISTS assignment_submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        content TEXT,
        submitted_at TEXT,
        feedback TEXT,
        rating INTEGER,
        FOREIGN KEY(assignment_id) REFERENCES assignments(id),
        FOREIGN KEY(student_id) REFERENCES users(id)
    )
    """)

    # MENTOR MESSAGES
    c.execute("""
    CREATE TABLE IF NOT EXISTS mentor_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        mentor_id INTEGER NOT NULL,
        question_text TEXT NOT NULL,
        answer_text TEXT,
        created_at TEXT NOT NULL,
        answered_at TEXT,
        FOREIGN KEY(student_id) REFERENCES users(id),
        FOREIGN KEY(mentor_id) REFERENCES users(id)
    )
    """)

    # LESSONS / CLASSES (video-based)
    c.execute("""
    CREATE TABLE IF NOT EXISTS lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        video_url TEXT,
        topic TEXT,
        created_by INTEGER,
        created_at TEXT,
        FOREIGN KEY(created_by) REFERENCES users(id)
    )
    """)

    # MANUAL QUIZZES (mentor-created)
    c.execute("""
    CREATE TABLE IF NOT EXISTS mentor_quizzes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        created_by INTEGER,
        created_at TEXT,
        FOREIGN KEY(created_by) REFERENCES users(id)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS mentor_quiz_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id INTEGER NOT NULL,
        question TEXT NOT NULL,
        option_a TEXT,
        option_b TEXT,
        option_c TEXT,
        option_d TEXT,
        correct_option TEXT NOT NULL,
        topic TEXT,
        difficulty TEXT,
        FOREIGN KEY(quiz_id) REFERENCES mentor_quizzes(id)
    )
    """)

    # Seed questions if empty
    c.execute("SELECT COUNT(*) AS cnt FROM questions")
    if c.fetchone()["cnt"] == 0:
        c.executemany("""
            INSERT INTO questions (
                topic, difficulty, question,
                option_a, option_b, option_c, option_d, correct_option
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (
                "Variables", "easy",
                "What is the correct way to declare a variable in Python?",
                "int x = 5", "x := 5", "x = 5", "declare x = 5", "c"
            ),
            (
                "Variables", "easy",
                "Which of these is a valid variable name in Python?",
                "2value", "value_2", "value-2", "value 2", "b"
            ),
            (
                "Loops", "easy",
                "Which loop is commonly used to iterate over a sequence in Python?",
                "for", "while", "repeat", "loop", "a"
            ),
            (
                "Loops", "medium",
                "What does range(5) generate?",
                "0 to 4", "1 to 5", "0 to 5", "1 to 4", "a"
            ),
            (
                "Functions", "medium",
                "Which keyword is used to define a function in Python?",
                "func", "function", "def", "lambda", "c"
            ),
            (
                "Functions", "medium",
                "What is the correct way to call a function named foo with no arguments?",
                "call foo()", "foo", "foo()", "foo[]", "c"
            ),
            (
                "Conditions", "easy",
                "Which keyword is used for conditional branching in Python?",
                "if", "when", "case", "switch", "a"
            ),
            (
                "Lists", "medium",
                "How do you append an element to a list in Python?",
                "list.add(x)", "list.append(x)", "add(list, x)", "push(list, x)", "b"
            ),
            (
                "OOP", "medium",
                "What does OOP stand for?",
                "Object-Oriented Programming",
                "Open Operational Process",
                "Object Original Protocol",
                "Optional Object Processing",
                "a"
            )
        ])

    # Seed assignments if empty
    c.execute("SELECT COUNT(*) AS cnt FROM assignments")
    if c.fetchone()["cnt"] == 0:
        c.executemany("""
            INSERT INTO assignments (title, description, due_date)
            VALUES (?, ?, ?)
        """, [
            (
                "M1: Variables Practice",
                "Write 5 Python programs using variables and print their values.",
                "2025-12-31"
            ),
            (
                "M2: Loops Practice",
                "Solve 3 problems using for and while loops.",
                "2025-12-31"
            ),
            (
                "M3: Functions Mini-Project",
                "Create a small menu-driven program using functions.",
                "2025-12-31"
            )
        ])

    db.commit()
