"""
database.py
------------
Database Module (CampusCare)
Author: CampusCare Development Team

Central data-access layer for the CampusCare complaint management system. 
Every other module talks to SQLite only through the functions defined here.
"""

import os
import sqlite3
import hashlib
from datetime import datetime
from contextlib import contextmanager

# Ensures the DB is created in the same directory as this script
DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "campuscare.db")


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
        # Removed 'priority' to match the ER Diagram and Table 3
        conn.execute("""
            CREATE TABLE IF NOT EXISTS Complaints (
                complaint_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                location TEXT NOT NULL,
                description TEXT NOT NULL,
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

        # Performance Indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_complaints_user_id ON Complaints(user_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_complaints_status ON Complaints(status);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_complaints_category ON Complaints(category);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_history_complaint_id ON Complaint_History(complaint_id);")


def format_complaint_id(complaint_id):
    """Turns the numeric primary key into the display ID, e.g. CC-0007."""
    return f"CC-{complaint_id:04d}"


def parse_complaint_id(display_id):
    """Converts a display ID (e.g., 'CC-0007') back to its numeric primary key."""
    try:
        if isinstance(display_id, str) and display_id.upper().startswith("CC-"):
            return int(display_id.split("-")[1])
        return int(display_id)
    except (ValueError, IndexError):
        return None


def hash_password(password):
    """Converts a plain-text password into a SHA-256 hash string."""
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


def email_exists(email):
    """True if an account with this email is already registered (case-insensitive)."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM Users WHERE lower(email) = lower(?)", (email,)
        ).fetchone()
        return row is not None


def register_student(name, email, password):
    """Self-service signup. Always creates a 'student' account (never an admin).

    Returns the new user_id, or None if the email is already registered.
    """
    email = email.strip().lower()
    if email_exists(email):
        return None
    try:
        return add_user(name.strip(), email, password, "student")
    except sqlite3.IntegrityError:
        # lost a race with another signup using the same email
        return None


def authenticate_user(email, password):
    hashed_pwd = hash_password(password)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM Users WHERE lower(email) = lower(?) AND password = ?",
            (email, hashed_pwd),
        ).fetchone()
        return dict(row) if row else None


def user_count():
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) AS c FROM Users").fetchone()["c"]


# ----------------------------------------------------------- Complaints ----

def add_history(complaint_id, old_status, new_status, changed_at=None, conn=None):
    """Explicitly separated to match report requirements.

    Pass `conn` when you are already inside a get_connection() block (as
    add_complaint and update_complaint_status are). SQLite lets only one
    connection write at a time, so opening a second connection in that
    situation waits and then fails with 'database is locked'.
    """
    if not changed_at:
        changed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = """INSERT INTO Complaint_History (complaint_id, old_status, new_status, changed_at)
             VALUES (?, ?, ?, ?)"""
    params = (complaint_id, old_status, new_status, changed_at)
    if conn is not None:
        conn.execute(sql, params)
        return
    with get_connection() as own_conn:
        own_conn.execute(sql, params)


def add_complaint(user_id, category, location, description):
    """Removed 'priority' to match report schema."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO Complaints
               (user_id, category, location, description, status, department, created_at)
               VALUES (?, ?, ?, ?, 'Pending', 'Unassigned', ?)""",
            (user_id, category, location, description, now),
        )
        complaint_id = cur.lastrowid
        # Calling the explicit add_history function (same connection, see its docstring)
        add_history(complaint_id, None, 'Pending', now, conn=conn)
        return complaint_id


def get_complaint_by_id(complaint_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM Complaints WHERE complaint_id = ?",
            (complaint_id,)
        ).fetchone()
        return dict(row) if row else None


def get_complaints_by_user(user_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM Complaints WHERE user_id = ? ORDER BY complaint_id DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_complaints(status_filter=None, category_filter=None):
    """Removed 'priority_filter' to match report schema."""
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

    query += " ORDER BY c.complaint_id DESC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def assign_department(complaint_id, department):
    """Explicitly separated to match report requirements."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE Complaints SET department = ? WHERE complaint_id = ?",
            (department, complaint_id),
        )
        return True


def update_complaint_status(complaint_id, new_status):
    """Now handles ONLY status changes, as per the report."""
    VALID_STATUSES = ("Pending", "In Progress", "Resolved")
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{new_status}'. Must be one of {VALID_STATUSES}")

    with get_connection() as conn:
        old = conn.execute(
            "SELECT status FROM Complaints WHERE complaint_id = ?", (complaint_id,)
        ).fetchone()
        
        if old is None:
            return False
            
        old_status = old["status"]

        if old_status != new_status:
            conn.execute(
                "UPDATE Complaints SET status = ? WHERE complaint_id = ?",
                (new_status, complaint_id),
            )
            # Call the explicit history function (same connection, see its docstring)
            add_history(complaint_id, old_status, new_status, conn=conn)
        return True


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

# ------------------------------------------------------------- Initialization ----

def seed_data():
    """Populates the database with an admin, sample students, and initial complaints if empty."""
    create_tables()
    if user_count() == 0:
        print("Seeding initial database records...")
        admin_id = add_user("Admin User", "admin@campus.edu", "admin123", "admin")
        student1 = add_user("Arjun Singh", "arjun@student.edu", "pass123", "student")
        student2 = add_user("Priya Sharma", "priya@student.edu", "pass123", "student")
        
        # Priority argument removed to match schema
        c1 = add_complaint(student1, "Maintenance", "Hostel Block A", "Leaking pipe in washroom")
        c2 = add_complaint(student2, "IT Support", "Main Library", "Wi-Fi access point dead")
        c3 = add_complaint(student1, "Food", "Cafeteria", "Quality of lunch was poor today")
        
        # Separated into individual function calls to match the new architecture
        update_complaint_status(c1, "In Progress")
        assign_department(c1, "Plumbing Dept")
        
        update_complaint_status(c2, "Resolved")
        assign_department(c2, "IT Services")
        
        print("Seed data creation complete.")