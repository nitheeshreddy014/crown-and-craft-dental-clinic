import sqlite3, os

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "clinic.db")

def get_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_connection(); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT NOT NULL,
        email TEXT NOT NULL, preferred_date TEXT NOT NULL, preferred_time TEXT NOT NULL,
        service TEXT NOT NULL, message TEXT DEFAULT '', appointment_status TEXT DEFAULT 'Pending',
        created_at TEXT DEFAULT (datetime('now','localtime')))""")
    c.execute("""CREATE TABLE IF NOT EXISTS contact_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL,
        phone TEXT DEFAULT '', message TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now','localtime')))""")
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE, phone TEXT DEFAULT '',
        password_hash TEXT NOT NULL, role TEXT DEFAULT 'patient',
        created_at TEXT DEFAULT (datetime('now','localtime')))""")
    conn.commit(); conn.close()

def add_appointment(name, phone, email, preferred_date, preferred_time, service, message=""):
    conn = get_connection(); c = conn.cursor()
    c.execute("INSERT INTO appointments (name,phone,email,preferred_date,preferred_time,service,message) VALUES (?,?,?,?,?,?,?)",
              (name,phone,email,preferred_date,preferred_time,service,message))
    conn.commit(); aid = c.lastrowid; conn.close(); return aid

def get_appointments(search=None, status_filter=None, date_filter=None):
    conn = get_connection(); c = conn.cursor()
    q = "SELECT * FROM appointments WHERE 1=1"; p = []
    if search:
        q += " AND (name LIKE ? OR email LIKE ? OR phone LIKE ?)"; s = f"%{search}%"; p.extend([s,s,s])
    if status_filter and status_filter != "All":
        q += " AND appointment_status = ?"; p.append(status_filter)
    if date_filter:
        q += " AND preferred_date = ?"; p.append(date_filter)
    q += " ORDER BY created_at DESC"; c.execute(q, p)
    rows = c.fetchall(); conn.close(); return [dict(r) for r in rows]

def get_appointment_by_id(aid):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM appointments WHERE id = ?", (aid,))
    row = c.fetchone(); conn.close(); return dict(row) if row else None

def update_appointment_status(aid, status):
    conn = get_connection(); c = conn.cursor()
    c.execute("UPDATE appointments SET appointment_status = ? WHERE id = ?", (status, aid))
    conn.commit(); ok = c.rowcount > 0; conn.close(); return ok

def add_contact_message(name, email, phone, message):
    conn = get_connection(); c = conn.cursor()
    c.execute("INSERT INTO contact_messages (name,email,phone,message) VALUES (?,?,?,?)", (name,email,phone,message))
    conn.commit(); mid = c.lastrowid; conn.close(); return mid

def get_contact_messages():
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM contact_messages ORDER BY created_at DESC")
    rows = c.fetchall(); conn.close(); return [dict(r) for r in rows]

def create_user(name, email, phone, password_hash, role="patient"):
    conn = get_connection(); c = conn.cursor()
    c.execute("INSERT INTO users (name,email,phone,password_hash,role) VALUES (?,?,?,?,?)",
              (name, email, phone, password_hash, role))
    conn.commit(); uid = c.lastrowid; conn.close(); return uid

def get_user_by_email(email):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
    row = c.fetchone(); conn.close(); return dict(row) if row else None

def check_email_exists(email):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE email = ?", (email.lower(),))
    exists = c.fetchone() is not None; conn.close(); return exists
