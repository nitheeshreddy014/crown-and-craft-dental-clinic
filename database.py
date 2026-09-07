import os, json, urllib.request, urllib.error

_TURSO_URL   = os.environ.get("TURSO_DATABASE_URL", "")
_TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")
_TURSO_HTTP  = _TURSO_URL.replace("libsql://", "https://") + "/v2/pipeline" if _TURSO_URL else ""


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
    except urllib.error.URLError as e:
        raise RuntimeError(f"Turso connection error: {e.reason}") from e
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

def _safe_alter(sql):
    """Run ALTER TABLE — silently ignore duplicate-column errors."""
    try:
        _run(sql)
    except Exception as e:
        if "duplicate column" not in str(e).lower():
            raise


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
            created_at TEXT DEFAULT (datetime('now','localtime')))""",
        """CREATE TABLE IF NOT EXISTS available_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slot_date TEXT NOT NULL, slot_time TEXT NOT NULL,
            is_available INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(slot_date, slot_time))""",
        """CREATE TABLE IF NOT EXISTS dental_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL, file_url TEXT NOT NULL,
            file_name TEXT NOT NULL, record_type TEXT DEFAULT 'General',
            uploaded_at TEXT DEFAULT (datetime('now','localtime')))""",
        """CREATE TABLE IF NOT EXISTS blog_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, slug TEXT NOT NULL UNIQUE,
            summary TEXT NOT NULL, content TEXT NOT NULL,
            author TEXT DEFAULT 'Dr. Maneesh Reddy Pocharam',
            published INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime')))""",
    ]:
        _run(stmt)

    # Safe migrations — add new columns without breaking existing data
    _safe_alter("ALTER TABLE users ADD COLUMN auth_provider TEXT DEFAULT 'email'")
    _safe_alter("ALTER TABLE users ADD COLUMN reset_token TEXT")
    _safe_alter("ALTER TABLE users ADD COLUMN reset_token_expiry TEXT")
    _safe_alter("ALTER TABLE users ADD COLUMN totp_secret TEXT")

    # Seed blog posts if none exist
    if not _run("SELECT 1 FROM blog_posts LIMIT 1")["rows"]:
        _seed_blog()


def _seed_blog():
    posts = [
        ("How Often Should You Visit the Dentist?",
         "how-often-visit-dentist",
         "Most people wonder if twice a year is really necessary. Here's what the science says.",
         "<p>The classic recommendation is to visit your dentist every <strong>6 months</strong>. Regular check-ups allow your dentist to catch cavities, gum disease, and oral cancer early, when they are easiest to treat.</p><p>Some patients need more frequent visits: gum disease patients every 3&ndash;4 months, pregnant women once per trimester, diabetics every 3&ndash;4 months.</p><p>Children should visit within 6 months of their first tooth appearing. Ask Dr. Maneesh what schedule is right for you.</p>"),
        ("5 Signs You Need a Root Canal",
         "signs-you-need-root-canal",
         "Root canals have an unfair reputation. Learn the warning signs early and save your tooth.",
         "<p>Modern root canal treatment is no more uncomfortable than a filling. The pain comes from <em>ignoring</em> the problem.</p><ol><li><strong>Persistent toothache</strong> when chewing or applying pressure.</li><li><strong>Lingering sensitivity</strong> to hot and cold (over 30 seconds).</li><li><strong>Darkening of the tooth</strong> — nerve damage inside.</li><li><strong>Swollen gums</strong> — pimple-like bump near a tooth signals abscess.</li><li><strong>Cracked tooth</strong> — bacteria enter and infect the pulp.</li></ol><p>At Crown &amp; Craft we use rotary endodontic techniques to make treatment fast and comfortable.</p>"),
        ("The Complete Guide to Teeth Whitening",
         "complete-guide-teeth-whitening",
         "Professional whitening vs home kits — what actually works and is safe for your enamel.",
         "<p>Professional in-office whitening gets teeth <strong>3&ndash;8 shades brighter in 60 minutes</strong> and is the gold standard. Take-home trays give similar results over 2 weeks. OTC strips are slower with lower concentration. Avoid charcoal pastes — they damage enamel. Starting from &#8377;5,000, professional whitening at Crown &amp; Craft is safer than any home remedy.</p>"),
        ("How to Brush Your Teeth Correctly",
         "how-to-brush-teeth-correctly",
         "Most adults are brushing wrong. This simple technique makes a big difference.",
         "<p>Hold your brush at a <strong>45-degree angle</strong> to your gums and use <strong>gentle circular motions</strong> for a full <strong>2 minutes</strong>. Never scrub back-and-forth. Clean all surfaces including your tongue. Use soft bristles, replace every 3 months, and do not rinse immediately after brushing — let fluoride work for 2 minutes.</p>"),
        ("Dental Implants vs Dentures: Which is Right for You?",
         "implants-vs-dentures",
         "Missing teeth? We compare the two most popular tooth replacement options side by side.",
         "<p>Implants last a lifetime, feel like natural teeth, and prevent bone loss. Dentures are lower upfront cost but need replacement every 5&ndash;10 years and can feel loose. If you are healthy enough for a minor procedure, implants are almost always the better long-term investment. Book a consultation with Dr. Maneesh to find out if you qualify.</p>"),
    ]
    for title, slug, summary, content in posts:
        try:
            _run("INSERT OR IGNORE INTO blog_posts (title,slug,summary,content) VALUES (?,?,?,?)",
                 (title, slug, summary, content))
        except Exception:
            pass


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

def cancel_appointment_by_patient(apt_id, patient_email):
    """Cancel only if appointment belongs to this patient and is not already completed."""
    res = _run(
        "UPDATE appointments SET appointment_status = 'Cancelled' "
        "WHERE id = ? AND email = ? AND appointment_status NOT IN ('Completed','Cancelled')",
        (apt_id, patient_email.lower())
    )
    return res["rowcount"] > 0

def get_appointments_for_tomorrow():
    """Return Confirmed appointments for tomorrow — used by daily cron reminder."""
    return _run(
        "SELECT * FROM appointments "
        "WHERE preferred_date = date('now','+1 day','localtime') "
        "AND appointment_status = 'Confirmed'"
    )["rows"]

def get_analytics():
    monthly   = _run("SELECT strftime('%Y-%m', created_at) AS month, COUNT(*) AS count FROM appointments GROUP BY month ORDER BY month DESC LIMIT 12")["rows"]
    by_service= _run("SELECT service, COUNT(*) AS count FROM appointments GROUP BY service ORDER BY count DESC")["rows"]
    by_status = _run("SELECT appointment_status AS status, COUNT(*) AS count FROM appointments GROUP BY appointment_status")["rows"]
    patients  = _run("SELECT COUNT(DISTINCT email) AS cnt FROM appointments")["rows"]
    return {
        "monthly":        list(reversed(monthly)),
        "by_service":     by_service,
        "by_status":      by_status,
        "total_patients": patients[0]["cnt"] if patients else 0,
    }


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

def create_user(name, email, phone, password_hash, role="patient", auth_provider="email"):
    res = _run(
        "INSERT INTO users (name,email,phone,password_hash,role,auth_provider) VALUES (?,?,?,?,?,?)",
        (name, email, phone, password_hash, role, auth_provider)
    )
    return res["lastrowid"]


def get_user_by_email(email):
    rows = _run("SELECT * FROM users WHERE email = ?", (email.lower(),))["rows"]
    return rows[0] if rows else None


def check_email_exists(email):
    return len(_run("SELECT 1 FROM users WHERE email = ?", (email.lower(),))["rows"]) > 0


def get_appointments_by_email(email):
    return _run(
        "SELECT * FROM appointments WHERE email = ? ORDER BY created_at DESC",
        (email.lower(),)
    )["rows"]

# ── User profile & password reset ─────────────────────────────────────────────

def update_user_profile(email, name, phone):
    _run("UPDATE users SET name = ?, phone = ? WHERE email = ?", (name, phone, email.lower()))

def set_reset_token(email, token, expiry_iso):
    _run("UPDATE users SET reset_token = ?, reset_token_expiry = ? WHERE email = ?",
         (token, expiry_iso, email.lower()))

def get_user_by_reset_token(token):
    rows = _run("SELECT * FROM users WHERE reset_token = ?", (token,))["rows"]
    return rows[0] if rows else None

def clear_reset_token(email):
    _run("UPDATE users SET reset_token = NULL, reset_token_expiry = NULL WHERE email = ?",
         (email.lower(),))

def update_password(email, new_hash):
    _run("UPDATE users SET password_hash = ? WHERE email = ?", (new_hash, email.lower()))

def set_totp_secret(email, secret):
    _run("UPDATE users SET totp_secret = ? WHERE email = ?", (secret, email.lower()))

# ── Available Slots ───────────────────────────────────────────────────────────

def get_slots(date=None):
    if date:
        return _run("SELECT * FROM available_slots WHERE slot_date = ? ORDER BY slot_time", (date,))["rows"]
    return _run("SELECT * FROM available_slots WHERE slot_date >= date('now','localtime') ORDER BY slot_date, slot_time")["rows"]

def add_slot(slot_date, slot_time):
    try:
        _run("INSERT OR IGNORE INTO available_slots (slot_date,slot_time) VALUES (?,?)", (slot_date, slot_time))
        return True
    except Exception:
        return False

def delete_slot(slot_id):
    return _run("DELETE FROM available_slots WHERE id = ?", (slot_id,))["rowcount"] > 0

def toggle_slot(slot_id, is_available):
    _run("UPDATE available_slots SET is_available = ? WHERE id = ?", (1 if is_available else 0, slot_id))

# ── Dental Records ────────────────────────────────────────────────────────────

def add_dental_record(user_email, file_url, file_name, record_type="General"):
    res = _run(
        "INSERT INTO dental_records (user_email,file_url,file_name,record_type) VALUES (?,?,?,?)",
        (user_email.lower(), file_url, file_name, record_type)
    )
    return res["lastrowid"]

def get_dental_records(user_email):
    return _run(
        "SELECT * FROM dental_records WHERE user_email = ? ORDER BY uploaded_at DESC",
        (user_email.lower(),)
    )["rows"]

def delete_dental_record(record_id, user_email):
    return _run(
        "DELETE FROM dental_records WHERE id = ? AND user_email = ?",
        (record_id, user_email.lower())
    )["rowcount"] > 0

# ── Blog ──────────────────────────────────────────────────────────────────────

def get_blog_posts(published_only=True):
    q = "SELECT id,title,slug,summary,author,created_at FROM blog_posts"
    if published_only:
        q += " WHERE published = 1"
    return _run(q + " ORDER BY created_at DESC")["rows"]

def get_blog_post(slug):
    rows = _run("SELECT * FROM blog_posts WHERE slug = ? AND published = 1", (slug,))["rows"]
    return rows[0] if rows else None
