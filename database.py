"""
database.py
------------
Database Module (CampusCare)

Central data-access layer. Every other module talks to SQLite only
through the functions defined here.
"""

import sqlite3
import hashlib
from datetime import datetime
from contextlib import contextmanager

DB_NAME = "campuscare.db"


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def create_tables():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('student', 'admin'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS Complaints (
                complaint_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                location TEXT NOT NULL,
                description TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'Medium',
                status TEXT NOT NULL DEFAULT 'Pending',
                department TEXT DEFAULT 'Unassigned',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES Users(user_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS Complaint_History (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_id INTEGER NOT NULL,
                old_status TEXT,
                new_status TEXT NOT NULL,
                changed_at TEXT NOT NULL,
                FOREIGN KEY (complaint_id) REFERENCES Complaints(complaint_id)
            )
        """)

        # --- STEP 3: Performance Indexes ---
        # 1. Student dashboard me fast queries ke liye
        conn.execute("CREATE INDEX IF NOT EXISTS idx_complaints_user_id ON Complaints(user_id);")
        
        # 2. Admin dashboard filters (Status & Category) ko fast karne ke liye
        conn.execute("CREATE INDEX IF NOT EXISTS idx_complaints_status ON Complaints(status);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_complaints_category ON Complaints(category);")
        
        # 3. Complaint audit trail fetch karne ke liye
        conn.execute("CREATE INDEX IF NOT EXISTS idx_history_complaint_id ON Complaint_History(complaint_id);")


def format_complaint_id(complaint_id):
    """Turns the numeric primary key into the display ID, e.g. CC-0007."""
    return f"CC-{complaint_id:04d}"


def hash_password(password):
    """Plain-text password ko SHA-256 hash string me convert karta hai."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- Users ----

def add_user(name, email, password, role):
    hashed_pwd = hash_password(password)
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO Users (name, email, password, role) VALUES (?, ?, ?, ?)",
            (name, email, hashed_pwd, role),
        )
        return cur.lastrowid


def authenticate_user(email, password):
    hashed_pwd = hash_password(password)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM Users WHERE email = ? AND password = ?",
            (email, hashed_pwd),
        ).fetchone()
        return dict(row) if row else None


def user_count():
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) AS c FROM Users").fetchone()["c"]


# ----------------------------------------------------------- Complaints ----

def add_complaint(user_id, category, location, description, priority):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO Complaints
               (user_id, category, location, description, priority, status, department, created_at)
               VALUES (?, ?, ?, ?,?, 'Pending', 'Unassigned', ?)""",
            (user_id, category, location, description, priority, now),
        )
        complaint_id = cur.lastrowid
        conn.execute(
            """INSERT INTO Complaint_History (complaint_id, old_status, new_status, changed_at)
               VALUES (?, NULL, 'Pending', ?)""",
            (complaint_id, now),
        )
        return complaint_id


def get_complaints_by_user(user_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM Complaints WHERE user_id = ? ORDER BY complaint_id DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_complaints(status_filter=None, category_filter=None, priority_filter=None):
    query = """SELECT c.*, u.name AS student_name
               FROM Complaints c JOIN Users u ON c.user_id = u.user_id
               WHERE 1=1"""
    params = []
    if status_filter and status_filter != "All":
        query += " AND c.status = ?"
        params.append(status_filter)
    if category_filter and category_filter != "All":
        query += " AND c.category = ?"
        params.append(category_filter)
    if priority_filter and priority_filter != "All":
        query += " AND c.priority = ?"
        params.append(priority_filter)

    query += " ORDER BY c.complaint_id DESC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def update_complaint_status(complaint_id, new_status, department=None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        old = conn.execute(
            "SELECT status FROM Complaints WHERE complaint_id = ?", (complaint_id,)
        ).fetchone()
        old_status = old["status"] if old else None

        if department is not None:
            conn.execute(
                "UPDATE Complaints SET status = ?, department = ? WHERE complaint_id = ?",
                (new_status, department, complaint_id),
            )
        else:
            conn.execute(
                "UPDATE Complaints SET status = ? WHERE complaint_id = ?",
                (new_status, complaint_id),
            )

        if old_status != new_status:
            conn.execute(
                """INSERT INTO Complaint_History
                   (complaint_id, old_status, new_status, changed_at)
                   VALUES (?, ?, ?, ?)""",
                (complaint_id, old_status, new_status, now),
            )


def get_complaint_history(complaint_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM Complaint_History WHERE complaint_id = ? ORDER BY history_id",
            (complaint_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ------------------------------------------------------------- Reporting ----

def get_statistics():
    with get_connection() as conn:
        status_rows = conn.execute(
            "SELECT status, COUNT(*) AS count FROM Complaints GROUP BY status"
        ).fetchall()
        category_rows = conn.execute(
            "SELECT category, COUNT(*) AS count FROM Complaints GROUP BY category ORDER BY count DESC"
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) AS c FROM Complaints").fetchone()["c"]
        return {
            "total": total,
            "by_status": {r["status"]: r["count"] for r in status_rows},
            "by_category": {r["category"]: r["count"] for r in category_rows},
        }