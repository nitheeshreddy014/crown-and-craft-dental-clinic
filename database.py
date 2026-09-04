import os, json, urllib.request, urllib.error

# ── Turso (persistent, free 9 GB) via pure-Python HTTP API ───────────────────
# No compiled/binary packages needed — works on any serverless platform.
# Set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN in Vercel Environment Variables.
_TURSO_URL   = os.environ.get("TURSO_DATABASE_URL", "")
_TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")
# Convert  libsql://xxx.turso.io  →  https://xxx.turso.io/v2/pipeline
_TURSO_HTTP  = _TURSO_URL.replace("libsql://", "https://") + "/v2/pipeline" if _TURSO_URL else ""

# Turso credentials are validated lazily when first DB call is made


# ── Turso HTTP layer ──────────────────────────────────────────────────────────

def _turso_arg(v):
    """Convert a Python value → Turso typed argument object."""
    if v is None:            return {"type": "null",    "value": None}
    if isinstance(v, bool):  return {"type": "integer", "value": "1" if v else "0"}
    if isinstance(v, int):   return {"type": "integer", "value": str(v)}
    if isinstance(v, float): return {"type": "float",   "value": str(v)}
    return                          {"type": "text",    "value": str(v)}


def _turso_cast(cell):
    """Convert a Turso response cell → Python value."""
    t, v = cell["type"], cell["value"]
    if t == "null":    return None
    if t == "integer": return int(v)
    if t == "float":   return float(v)
    return v


def _turso_run(sql, params=None):
    """Execute one SQL statement via Turso HTTP API. Returns result dict."""
    payload = json.dumps({
        "requests": [
            {"type": "execute", "stmt": {
                "sql":  sql,
                "args": [_turso_arg(p) for p in (params or [])]
            }},
            {"type": "close"}
        ]
    }).encode()
    req = urllib.request.Request(
        _TURSO_HTTP,
        data=payload,
        headers={"Authorization": f"Bearer {_TURSO_TOKEN}",
                 "Content-Type":  "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Turso HTTP {e.code}: {e.read().decode()}") from e
    res  = body["results"][0]["response"]["result"]
    cols = [c["name"] for c in res["cols"]]
    rows = [dict(zip(cols, (_turso_cast(c) for c in row))) for row in res["rows"]]
    raw_id = res.get("last_insert_rowid")
    return {"rows": rows,
            "lastrowid": int(raw_id) if raw_id is not None else None,
            "rowcount":  res.get("affected_row_count", 0)}


# ── Unified runner ────────────────────────────────────────────────────────────

def _run(sql, params=None):
    """Single entry point: always uses Turso."""
    return _turso_run(sql, params)


# ── Schema ────────────────────────────────────────────────────────────────────

def init_db():
    for stmt in [
        """CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT NOT NULL,
            email TEXT NOT NULL, preferred_date TEXT NOT NULL, preferred_time TEXT NOT NULL,
            service TEXT NOT NULL, message TEXT DEFAULT '', appointment_status TEXT DEFAULT 'Pending',
            created_at TEXT DEFAULT (datetime('now','localtime')))""",
        """CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL,
            phone TEXT DEFAULT '', message TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now','localtime')))""",
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE, phone TEXT DEFAULT '',
            password_hash TEXT NOT NULL, role TEXT DEFAULT 'patient',
            created_at TEXT DEFAULT (datetime('now','localtime')))"""
    ]:
        _run(stmt)


# ── Appointments ──────────────────────────────────────────────────────────────

def add_appointment(name, phone, email, preferred_date, preferred_time, service, message=""):
    res = _run(
        "INSERT INTO appointments (name,phone,email,preferred_date,preferred_time,service,message)"
        " VALUES (?,?,?,?,?,?,?)",
        (name, phone, email, preferred_date, preferred_time, service, message)
    )
    return res["lastrowid"]


def get_appointments(search=None, status_filter=None, date_filter=None):
    q = "SELECT * FROM appointments WHERE 1=1"; p = []
    if search:
        q += " AND (name LIKE ? OR email LIKE ? OR phone LIKE ?)"; s = f"%{search}%"; p.extend([s, s, s])
    if status_filter and status_filter != "All":
        q += " AND appointment_status = ?"; p.append(status_filter)
    if date_filter:
        q += " AND preferred_date = ?"; p.append(date_filter)
    q += " ORDER BY created_at DESC"
    return _run(q, p)["rows"]


def get_appointment_by_id(aid):
    rows = _run("SELECT * FROM appointments WHERE id = ?", (aid,))["rows"]
    return rows[0] if rows else None


def update_appointment_status(aid, status):
    res = _run("UPDATE appointments SET appointment_status = ? WHERE id = ?", (status, aid))
    return res["rowcount"] > 0


# ── Contact messages ──────────────────────────────────────────────────────────

def add_contact_message(name, email, phone, message):
    res = _run(
        "INSERT INTO contact_messages (name,email,phone,message) VALUES (?,?,?,?)",
        (name, email, phone, message)
    )
    return res["lastrowid"]


def get_contact_messages():
    return _run("SELECT * FROM contact_messages ORDER BY created_at DESC")["rows"]


# ── Users ─────────────────────────────────────────────────────────────────────

def create_user(name, email, phone, password_hash, role="patient"):
    res = _run(
        "INSERT INTO users (name,email,phone,password_hash,role) VALUES (?,?,?,?,?)",
        (name, email, phone, password_hash, role)
    )
    return res["lastrowid"]


def get_user_by_email(email):
    rows = _run("SELECT * FROM users WHERE email = ?", (email.lower(),))["rows"]
    return rows[0] if rows else None


def check_email_exists(email):
    return len(_run("SELECT 1 FROM users WHERE email = ?", (email.lower(),))["rows"]) > 0


def get_appointments_by_email(email):
    """Get all appointments for a specific patient email."""
    return _run(
        "SELECT * FROM appointments WHERE email = ? ORDER BY created_at DESC",
        (email.lower(),)
    )["rows"]
