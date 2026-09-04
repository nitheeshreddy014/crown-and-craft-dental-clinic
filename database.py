import os, sqlite3

# ── Turso (persistent, free 9 GB) ────────────────────────────────────────────
# Set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN in Vercel Environment Variables.
_TURSO_URL   = os.environ.get("TURSO_DATABASE_URL", "")
_TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")
_USE_TURSO   = bool(_TURSO_URL and _TURSO_TOKEN)

if _USE_TURSO:
    import libsql_experimental as libsql  # type: ignore

# ── Local / ephemeral SQLite fallback (used when Turso vars are absent) ───────
_IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))
DB_DIR  = "/tmp/clinic_data" if _IS_VERCEL else os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "clinic.db")


# ── Connection ────────────────────────────────────────────────────────────────

def get_connection():
    if _USE_TURSO:
        return libsql.connect(_TURSO_URL, auth_token=_TURSO_TOKEN)
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _to_dict(row, cursor):
    """Single row → dict; handles both sqlite3.Row and libsql plain tuples."""
    if row is None:
        return None
    if hasattr(row, "keys"):                        # sqlite3.Row
        return dict(row)
    cols = [d[0] for d in cursor.description]       # libsql tuple
    return dict(zip(cols, row))


def _to_dicts(rows, cursor):
    """Many rows → list[dict]; handles both sqlite3.Row and libsql plain tuples."""
    if not rows:
        return []
    cols = [d[0] for d in cursor.description]
    if hasattr(rows[0], "keys"):                    # sqlite3.Row
        return [dict(r) for r in rows]
    return [dict(zip(cols, r)) for r in rows]       # libsql tuple


# ── Schema ────────────────────────────────────────────────────────────────────

def init_db():
    conn = get_connection()
    conn.execute("""CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT NOT NULL,
        email TEXT NOT NULL, preferred_date TEXT NOT NULL, preferred_time TEXT NOT NULL,
        service TEXT NOT NULL, message TEXT DEFAULT '', appointment_status TEXT DEFAULT 'Pending',
        created_at TEXT DEFAULT (datetime('now','localtime')))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS contact_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL,
        phone TEXT DEFAULT '', message TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now','localtime')))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE, phone TEXT DEFAULT '',
        password_hash TEXT NOT NULL, role TEXT DEFAULT 'patient',
        created_at TEXT DEFAULT (datetime('now','localtime')))""")
    conn.commit()
    conn.close()


# ── Appointments ──────────────────────────────────────────────────────────────

def add_appointment(name, phone, email, preferred_date, preferred_time, service, message=""):
    conn = get_connection()
    c = conn.execute(
        "INSERT INTO appointments (name,phone,email,preferred_date,preferred_time,service,message)"
        " VALUES (?,?,?,?,?,?,?)",
        (name, phone, email, preferred_date, preferred_time, service, message)
    )
    conn.commit(); aid = c.lastrowid; conn.close()
    return aid


def get_appointments(search=None, status_filter=None, date_filter=None):
    conn = get_connection()
    q = "SELECT * FROM appointments WHERE 1=1"; p = []
    if search:
        q += " AND (name LIKE ? OR email LIKE ? OR phone LIKE ?)"; s = f"%{search}%"; p.extend([s, s, s])
    if status_filter and status_filter != "All":
        q += " AND appointment_status = ?"; p.append(status_filter)
    if date_filter:
        q += " AND preferred_date = ?"; p.append(date_filter)
    q += " ORDER BY created_at DESC"
    c = conn.execute(q, p); rows = c.fetchall()
    result = _to_dicts(rows, c); conn.close()
    return result


def get_appointment_by_id(aid):
    conn = get_connection()
    c = conn.execute("SELECT * FROM appointments WHERE id = ?", (aid,))
    row = c.fetchone(); result = _to_dict(row, c); conn.close()
    return result


def update_appointment_status(aid, status):
    conn = get_connection()
    c = conn.execute("UPDATE appointments SET appointment_status = ? WHERE id = ?", (status, aid))
    conn.commit(); ok = c.rowcount > 0; conn.close()
    return ok


# ── Contact messages ──────────────────────────────────────────────────────────

def add_contact_message(name, email, phone, message):
    conn = get_connection()
    c = conn.execute(
        "INSERT INTO contact_messages (name,email,phone,message) VALUES (?,?,?,?)",
        (name, email, phone, message)
    )
    conn.commit(); mid = c.lastrowid; conn.close()
    return mid


def get_contact_messages():
    conn = get_connection()
    c = conn.execute("SELECT * FROM contact_messages ORDER BY created_at DESC")
    rows = c.fetchall(); result = _to_dicts(rows, c); conn.close()
    return result


# ── Users ─────────────────────────────────────────────────────────────────────

def create_user(name, email, phone, password_hash, role="patient"):
    conn = get_connection()
    c = conn.execute(
        "INSERT INTO users (name,email,phone,password_hash,role) VALUES (?,?,?,?,?)",
        (name, email, phone, password_hash, role)
    )
    conn.commit(); uid = c.lastrowid; conn.close()
    return uid


def get_user_by_email(email):
    conn = get_connection()
    c = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
    row = c.fetchone(); result = _to_dict(row, c); conn.close()
    return result


def check_email_exists(email):
    conn = get_connection()
    c = conn.execute("SELECT 1 FROM users WHERE email = ?", (email.lower(),))
    exists = c.fetchone() is not None; conn.close()
    return exists
