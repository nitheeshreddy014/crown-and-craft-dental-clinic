import sqlite3, os

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
DB_PATH = os.path.join(DB_DIR, 'clinic.db')

def get_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    return conn

def init_db():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now','localtime')))""")
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
        conn.commit()
    finally:
        conn.close()

# ==================== ADMIN CRUD ====================

def get_admin_by_username(username):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT * FROM admins WHERE username = ?', (username.strip(),))
        row = c.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def create_admin(username, password_hash):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('INSERT INTO admins (username, password_hash) VALUES (?, ?)', (username.strip(), password_hash))
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()

def admin_exists(username):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT 1 FROM admins WHERE username = ?', (username.strip(),))
        return c.fetchone() is not None
    finally:
        conn.close()

def get_all_admins():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT id, username, created_at FROM admins ORDER BY created_at ASC')
        return [dict(r) for r in c.fetchall()]
    finally:
        conn.close()

def delete_admin(username):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('DELETE FROM admins WHERE username = ?', (username.strip(),))
        conn.commit()
        return c.rowcount > 0
    finally:
        conn.close()

def update_admin_password(username, new_password_hash):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('UPDATE admins SET password_hash = ? WHERE username = ?', (new_password_hash, username.strip()))
        conn.commit()
        return c.rowcount > 0
    finally:
        conn.close()

def admin_count():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM admins')
        return c.fetchone()[0]
    finally:
        conn.close()

# ==================== APPOINTMENTS ====================

def add_appointment(name, phone, email, preferred_date, preferred_time, service, message=''):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('INSERT INTO appointments (name,phone,email,preferred_date,preferred_time,service,message) VALUES (?,?,?,?,?,?,?)',
                  (name, phone, email, preferred_date, preferred_time, service, message))
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()

def get_appointments(search=None, status_filter=None, date_filter=None):
    conn = get_connection()
    try:
        c = conn.cursor()
        q = 'SELECT * FROM appointments WHERE 1=1'
        p = []
        if search:
            q += ' AND (name LIKE ? OR email LIKE ? OR phone LIKE ?)'
            s = f'%{search}%'
            p.extend([s, s, s])
        if status_filter and status_filter != 'All':
            q += ' AND appointment_status = ?'
            p.append(status_filter)
        if date_filter:
            q += ' AND preferred_date = ?'
            p.append(date_filter)
        q += ' ORDER BY created_at DESC'
        c.execute(q, p)
        return [dict(r) for r in c.fetchall()]
    finally:
        conn.close()

def get_appointment_by_id(aid):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT * FROM appointments WHERE id = ?', (aid,))
        row = c.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def update_appointment_status(aid, status):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('UPDATE appointments SET appointment_status = ? WHERE id = ?', (status, aid))
        conn.commit()
        return c.rowcount > 0
    finally:
        conn.close()

# ==================== CONTACT MESSAGES ====================

def add_contact_message(name, email, phone, message):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('INSERT INTO contact_messages (name,email,phone,message) VALUES (?,?,?,?)',
                  (name, email, phone, message))
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()

def get_contact_messages():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT * FROM contact_messages ORDER BY created_at DESC')
        return [dict(r) for r in c.fetchall()]
    finally:
        conn.close()

# ==================== USERS ====================

def create_user(name, email, phone, password_hash, role='patient'):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('INSERT INTO users (name,email,phone,password_hash,role) VALUES (?,?,?,?,?)',
                  (name, email, phone, password_hash, role))
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()

def get_user_by_email(email):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email = ?', (email.lower(),))
        row = c.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def check_email_exists(email):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT 1 FROM users WHERE email = ?', (email.lower(),))
        return c.fetchone() is not None
    finally:
        conn.close()
