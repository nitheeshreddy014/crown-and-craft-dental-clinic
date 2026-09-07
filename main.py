import os, hashlib, hmac, re, urllib.parse, secrets, logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from database import (
    init_db, add_appointment, get_appointments, get_appointment_by_id,
    update_appointment_status, add_contact_message, get_contact_messages,
    create_user, get_user_by_email, check_email_exists, get_appointments_by_email,
    cancel_appointment_by_patient, get_appointments_for_tomorrow, get_analytics,
    update_user_profile, set_reset_token, get_user_by_reset_token,
    clear_reset_token, update_password, set_totp_secret,
    get_slots, add_slot, delete_slot, toggle_slot,
    add_dental_record, get_dental_records, delete_dental_record,
    get_blog_posts, get_blog_post,
)
from models import (
    AppointmentForm, ContactForm, LoginForm, RegisterForm,
    ForgotPasswordForm, ResetPasswordForm, ProfileUpdateForm,
    SlotForm, DentalRecordForm, TOTPVerifyForm,
)
from email_utils import (
    send_booking_confirmation, send_status_update, send_reminder,
    send_password_reset, send_cancellation_confirmation,
)

CLINIC_NAME = "Crown & Craft Dental Clinic"
DOCTOR_NAME = "Dr. Maneesh Reddy Pocharam"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

logger = logging.getLogger("crown_craft")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Google OAuth diagnostic logging ──────────────────────────────────────
    _gid     = os.environ.get("GOOGLE_CLIENT_ID", "")
    _gsecret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    _gredir  = os.environ.get("GOOGLE_REDIRECT_URI", "")
    logger.info("[OAuth] GOOGLE_CLIENT_ID loaded     : %s", bool(_gid))
    logger.info("[OAuth] GOOGLE_CLIENT_SECRET loaded : %s", bool(_gsecret))
    logger.info("[OAuth] GOOGLE_CLIENT_SECRET prefix : %s", (_gsecret[:6] + "…") if _gsecret else "(not set)")
    logger.info("[OAuth] GOOGLE_REDIRECT_URI         : %s", _gredir or "(not set)")
    # ─────────────────────────────────────────────────────────────────────────
    try:
        init_db()
        logger.info("DB init successful")
    except Exception as e:
        logger.error("DB init failed: %s", e)
    yield

app = FastAPI(title=CLINIC_NAME, version="1.0.0", lifespan=lifespan)

# Mount static files only when the directory actually exists (safe for Vercel)
_static_dir = os.path.join(BASE_DIR, "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

SECRET_KEY = os.getenv("SECRET_KEY", "crown-craft-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# ── Admin credentials (loaded from environment variable only) ────────────────────
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise RuntimeError("ADMIN_PASSWORD environment variable is not set!")
def _hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()
def _verify_pw(plain, hashed): return hmac.compare_digest(_hash_pw(plain), hashed)
ADMIN_USERS = {
    "nitheesh": _hash_pw(ADMIN_PASSWORD),
    "maneesh":  _hash_pw(ADMIN_PASSWORD),
}

# ── Google OAuth config (set these in Vercel env vars) ──────────────────────
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI",
    "https://crown-and-craft-dental-clinic-2153.vercel.app/auth/google/callback")

def create_token(sub, role="patient", name=""):
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": sub, "role": role, "name": name, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token):
    try: return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError: return None

def get_current_user_payload(request):
    token = request.cookies.get("admin_token")
    if not token: return None
    return verify_token(token)

def get_admin_user(request):
    payload = get_current_user_payload(request)
    if payload and payload.get("role") == "admin": return payload.get("sub")
    return None

def require_patient(request):
    """Return payload if logged-in patient, else None."""
    payload = get_current_user_payload(request)
    if payload and payload.get("role") == "patient":
        return payload
    return None

def ctx(request, **extra):
    return {"request": request, "doctor_name": DOCTOR_NAME, "clinic_name": CLINIC_NAME, **extra}

# ==================== PAGE ROUTES ====================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    posts = get_blog_posts()[:3]   # latest 3 posts for homepage preview
    return templates.TemplateResponse("index.html", ctx(request, blog_posts=posts))

@app.get("/doctor", response_class=HTMLResponse)
async def doctor_page(request: Request):
    return templates.TemplateResponse("doctor.html", ctx(request))

@app.get("/services", response_class=HTMLResponse)
async def services_page(request: Request):
    return templates.TemplateResponse("services.html", ctx(request))

@app.get("/blog", response_class=HTMLResponse)
async def blog_list(request: Request):
    posts = get_blog_posts()
    return templates.TemplateResponse("blog.html", ctx(request, posts=posts, post=None))

@app.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post(request: Request, slug: str):
    post = get_blog_post(slug)
    if not post:
        return RedirectResponse(url="/blog", status_code=302)
    posts = get_blog_posts()
    return templates.TemplateResponse("blog.html", ctx(request, posts=posts, post=post))

@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: str = ""):
    return templates.TemplateResponse("reset_password.html", ctx(request, token=token))

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if get_admin_user(request): return RedirectResponse(url="/admin", status_code=302)
    return templates.TemplateResponse("login.html", ctx(request, error=None))

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request,
        search: str = Query(default=None), status: str = Query(default=None),
        date: str = Query(default=None), tab: str = Query(default="appointments")):
    admin = get_admin_user(request)
    if not admin: return RedirectResponse(url="/login", status_code=302)
    appointments = get_appointments(search=search, status_filter=status, date_filter=date)
    messages     = get_contact_messages()
    slots        = get_slots()
    analytics    = get_analytics()
    user_obj     = get_user_by_email(admin) if get_user_by_email(admin) else None
    admin_totp   = None
    if user_obj:
        admin_totp = user_obj.get("totp_secret")
    return templates.TemplateResponse("admin.html", ctx(request,
        admin_user=admin, appointments=appointments, messages=messages,
        slots=slots, analytics=analytics,
        admin_totp_configured=bool(admin_totp),
        search=search or "", status_filter=status or "All",
        date_filter=date or "", active_tab=tab))

# ==================== API ROUTES ====================

# ── Forgot / Reset Password ───────────────────────────────────────────────────

@app.post("/api/forgot-password")
async def forgot_password(request: Request):
    try:
        body = await request.json()
        form = ForgotPasswordForm(**body)
    except Exception:
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid email."})
    user = get_user_by_email(form.email)
    # Always return success (don't reveal whether email exists)
    if user:
        token   = secrets.token_urlsafe(32)
        expiry  = (datetime.utcnow() + timedelta(minutes=30)).isoformat()
        set_reset_token(form.email, token, expiry)
        send_password_reset(form.email, user["name"], token)
    return JSONResponse(content={"success": True,
        "message": "If that email is registered, a reset link has been sent."})

@app.post("/api/reset-password")
async def reset_password(request: Request):
    try:
        body = await request.json()
        form = ResetPasswordForm(**body)
    except Exception as e:
        return JSONResponse(status_code=400, content={"success": False, "message": str(e)})
    if form.password != form.confirm_password:
        return JSONResponse(status_code=400, content={"success": False, "message": "Passwords do not match."})
    user = get_user_by_reset_token(form.token)
    if not user:
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid or expired reset link."})
    # Check expiry
    try:
        expiry = datetime.fromisoformat(user["reset_token_expiry"])
        if datetime.utcnow() > expiry:
            clear_reset_token(user["email"])
            return JSONResponse(status_code=400, content={"success": False, "message": "Reset link has expired. Please request a new one."})
    except Exception:
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid reset token."})
    update_password(user["email"], _hash_pw(form.password))
    clear_reset_token(user["email"])
    return JSONResponse(content={"success": True, "message": "Password updated! You can now sign in."})

# ── Patient Profile ───────────────────────────────────────────────────────────

@app.put("/api/profile")
async def update_profile(request: Request):
    payload = require_patient(request)
    if not payload:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    try:
        body = await request.json()
        form = ProfileUpdateForm(**body)
    except Exception as e:
        return JSONResponse(status_code=400, content={"success": False, "message": str(e)})
    update_user_profile(payload["sub"], form.name, form.phone or "")
    # Re-issue token with updated name
    new_token = create_token(payload["sub"], "patient", form.name)
    resp = JSONResponse(content={"success": True, "message": "Profile updated successfully."})
    resp.set_cookie("admin_token", new_token, httponly=True,
                    max_age=ACCESS_TOKEN_EXPIRE_HOURS * 3600, samesite="lax")
    return resp

# ── Patient Appointment Cancellation ─────────────────────────────────────────

@app.post("/api/appointments/{apt_id}/cancel")
async def patient_cancel_appointment(request: Request, apt_id: int):
    payload = require_patient(request)
    if not payload:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    apt = get_appointment_by_id(apt_id)
    if not apt:
        return JSONResponse(status_code=404, content={"success": False, "message": "Appointment not found."})
    ok = cancel_appointment_by_patient(apt_id, payload["sub"])
    if ok:
        send_cancellation_confirmation(
            apt["email"], apt["name"],
            apt["preferred_date"], apt["preferred_time"], apt["service"]
        )
        return JSONResponse(content={"success": True, "message": "Appointment cancelled."})
    return JSONResponse(status_code=400, content={"success": False,
        "message": "Cannot cancel — appointment may already be completed or cancelled."})

# ── Dental Records ────────────────────────────────────────────────────────────

@app.get("/api/records")
async def list_records(request: Request):
    payload = require_patient(request)
    if not payload:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    records = get_dental_records(payload["sub"])
    return JSONResponse(content={"success": True, "records": records})

@app.post("/api/records")
async def save_record(request: Request):
    payload = require_patient(request)
    if not payload:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    try:
        body = await request.json()
        form = DentalRecordForm(**body)
    except Exception as e:
        return JSONResponse(status_code=400, content={"success": False, "message": str(e)})
    rid = add_dental_record(payload["sub"], form.file_url, form.file_name, form.record_type or "General")
    return JSONResponse(content={"success": True, "record_id": rid, "message": "Record saved."})

@app.delete("/api/records/{record_id}")
async def remove_record(request: Request, record_id: int):
    payload = require_patient(request)
    if not payload:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    ok = delete_dental_record(record_id, payload["sub"])
    if ok:
        return JSONResponse(content={"success": True, "message": "Record deleted."})
    return JSONResponse(status_code=404, content={"success": False, "message": "Record not found."})

# ── Admin: Analytics ──────────────────────────────────────────────────────────

@app.get("/api/admin/analytics")
async def admin_analytics(request: Request):
    if not get_admin_user(request):
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    return JSONResponse(content={"success": True, **get_analytics()})

# ── Admin: Slot Management ────────────────────────────────────────────────────

@app.get("/api/admin/slots")
async def list_slots(request: Request, date: str = Query(default=None)):
    if not get_admin_user(request):
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    return JSONResponse(content={"success": True, "slots": get_slots(date)})

@app.post("/api/admin/slots")
async def create_slot(request: Request):
    if not get_admin_user(request):
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    try:
        body = await request.json()
        form = SlotForm(**body)
    except Exception as e:
        return JSONResponse(status_code=400, content={"success": False, "message": str(e)})
    ok = add_slot(form.slot_date, form.slot_time)
    if ok:
        return JSONResponse(content={"success": True, "message": "Slot added."})
    return JSONResponse(status_code=400, content={"success": False, "message": "Slot already exists."})

@app.delete("/api/admin/slots/{slot_id}")
async def remove_slot(request: Request, slot_id: int):
    if not get_admin_user(request):
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    ok = delete_slot(slot_id)
    if ok:
        return JSONResponse(content={"success": True, "message": "Slot removed."})
    return JSONResponse(status_code=404, content={"success": False, "message": "Slot not found."})

@app.patch("/api/admin/slots/{slot_id}")
async def toggle_slot_availability(request: Request, slot_id: int):
    if not get_admin_user(request):
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    body = await request.json()
    toggle_slot(slot_id, body.get("is_available", True))
    return JSONResponse(content={"success": True, "message": "Slot updated."})

# ── Admin: 2FA Setup ──────────────────────────────────────────────────────────

@app.post("/api/admin/2fa/setup")
async def setup_2fa(request: Request):
    admin = get_admin_user(request)
    if not admin:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    try:
        import pyotp, base64
        secret = pyotp.random_base32()
        totp   = pyotp.TOTP(secret)
        uri    = totp.provisioning_uri(name=admin, issuer_name="Crown & Craft Dental")
        # Store secret against the admin username (stored as email in users if exists,
        # otherwise we store in ADMIN_USERS via in-memory dict for this session)
        # We persist it in the users table if admin has an account, else env-based fallback
        user = get_user_by_email(admin + "@clinic.local")
        if not user:
            try:
                create_user(admin, admin + "@clinic.local", "", _hash_pw(secrets.token_urlsafe()), "admin")
            except Exception:
                pass
        set_totp_secret(admin + "@clinic.local", secret)
        return JSONResponse(content={"success": True, "secret": secret, "uri": uri})
    except ImportError:
        return JSONResponse(status_code=500, content={"success": False,
            "message": "pyotp not installed. Run: pip install pyotp"})

@app.post("/api/admin/2fa/verify")
async def verify_2fa(request: Request):
    admin = get_admin_user(request)
    if not admin:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    try:
        import pyotp
        body = await request.json()
        code = body.get("code", "")
        user = get_user_by_email(admin + "@clinic.local")
        if not user or not user.get("totp_secret"):
            return JSONResponse(status_code=400, content={"success": False, "message": "2FA not set up yet."})
        totp = pyotp.TOTP(user["totp_secret"])
        if totp.verify(code):
            return JSONResponse(content={"success": True, "message": "2FA code is valid! ✓"})
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid code. Try again."})
    except ImportError:
        return JSONResponse(status_code=500, content={"success": False, "message": "pyotp not installed."})

# ── Cron: Daily Appointment Reminders ────────────────────────────────────────

@app.get("/api/cron/reminders")
async def send_daily_reminders(request: Request):
    """Called daily by Vercel Cron at 9 AM. Sends reminder emails for tomorrow's appointments."""
    # Minimal security: check cron secret header
    cron_secret = os.getenv("CRON_SECRET", "")
    auth_header = request.headers.get("authorization", "")
    if cron_secret and auth_header != f"Bearer {cron_secret}":
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    apts  = get_appointments_for_tomorrow()
    sent  = 0
    for apt in apts:
        ok = send_reminder(
            apt["email"], apt["name"],
            apt["preferred_date"], apt["preferred_time"], apt["service"]
        )
        if ok:
            sent += 1
    return JSONResponse(content={"success": True, "reminders_sent": sent, "total": len(apts)})

@app.post("/api/register")
async def register_user(request: Request):
    body = await request.json()
    name = body.get("name", "").strip()
    email = body.get("email", "").strip().lower()
    phone = body.get("phone", "").strip()
    password = body.get("password", "")
    confirm_password = body.get("confirm_password", "")
    if not name or len(name) < 2:
        return JSONResponse(status_code=400, content={"success": False, "message": "Name must be at least 2 characters."})
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        return JSONResponse(status_code=400, content={"success": False, "message": "Please enter a valid email address."})
    if phone:
        phone_clean = re.sub(r"[\s\-\(\)\+]", "", phone)
        if not phone_clean.isdigit() or len(phone_clean) < 7 or len(phone_clean) > 15:
            return JSONResponse(status_code=400, content={"success": False, "message": "Please enter a valid phone number."})
    if len(password) < 6:
        return JSONResponse(status_code=400, content={"success": False, "message": "Password must be at least 6 characters."})
    if password != confirm_password:
        return JSONResponse(status_code=400, content={"success": False, "message": "Passwords do not match."})
    if check_email_exists(email):
        return JSONResponse(status_code=409, content={"success": False, "message": "An account with this email already exists."})
    try:
        create_user(name=name, email=email, phone=phone, password_hash=_hash_pw(password))
        return JSONResponse(content={"success": True, "message": "Registration successful! Please sign in."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": f"Registration failed: {str(e)}"})

@app.post("/api/login")
async def login(form: LoginForm):
    uname = form.username.strip().lower()
    # Check admin (Nitheesh or Maneesh)
    if uname in ADMIN_USERS and hmac.compare_digest(_hash_pw(form.password), ADMIN_USERS[uname]):
        display = uname.title()
        token = create_token(uname, "admin", display)
        resp = JSONResponse(content={"success": True, "message": f"Welcome, {display}!", "redirect_url": "/admin"})
        resp.set_cookie("admin_token", token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_HOURS*3600, samesite="lax")
        return resp
    # Check patient
    user = get_user_by_email(uname)
    if user and _verify_pw(form.password, user["password_hash"]):
        token = create_token(user["email"], "patient", user["name"])
        resp = JSONResponse(content={"success": True, "message": f"Welcome back, {user['name']}!", "redirect_url": "/my-appointments"})
        resp.set_cookie("admin_token", token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_HOURS*3600, samesite="lax")
        return resp
    return JSONResponse(status_code=401, content={"success": False, "message": "Invalid email/username or password."})

@app.get("/api/me")
async def get_current_user(request: Request):
    token = request.cookies.get("admin_token")
    if not token: return JSONResponse(content={"logged_in": False})
    payload = verify_token(token)
    if not payload: return JSONResponse(content={"logged_in": False})
    role = payload.get("role", "patient"); sub = payload.get("sub", "")
    name = payload.get("name", sub)
    if role == "patient":
        user = get_user_by_email(sub)
        return JSONResponse(content={"logged_in": True, "name": user["name"] if user else name, "email": sub, "role": role})
    return JSONResponse(content={"logged_in": True, "name": name.title(), "role": role})

@app.get("/my-appointments", response_class=HTMLResponse)
async def my_appointments(request: Request):
    payload = get_current_user_payload(request)
    if not payload or payload.get("role") != "patient":
        return RedirectResponse(url="/login?next=my-appointments", status_code=302)
    email = payload.get("sub", "")
    user  = get_user_by_email(email)
    apts  = get_appointments_by_email(email)
    return templates.TemplateResponse("my_appointments.html", ctx(request, user=user, appointments=apts))


@app.get("/auth/google")
async def google_login(request: Request):
    # Read from env at request time so changes take effect without redeploy
    _client_id    = os.environ.get("GOOGLE_CLIENT_ID", "")
    _redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", "")

    if not _client_id:
        logger.error("[OAuth] /auth/google — GOOGLE_CLIENT_ID is not set")
        return RedirectResponse(url="/login?error=google_not_configured")
    if not _redirect_uri:
        logger.error("[OAuth] /auth/google — GOOGLE_REDIRECT_URI is not set")
        return RedirectResponse(url="/login?error=google_not_configured")

    state = secrets.token_urlsafe(16)
    params = urllib.parse.urlencode({
        "client_id":     _client_id,
        "redirect_uri":  _redirect_uri,   # single source of truth
        "response_type": "code",
        "scope":         "openid email profile",
        "state":         state,
        "access_type":   "offline",
    })
    logger.info("[OAuth] Redirecting to Google consent — redirect_uri=%s", _redirect_uri)
    resp = RedirectResponse(url=f"https://accounts.google.com/o/oauth2/v2/auth?{params}")
    resp.set_cookie("oauth_state", state, httponly=True, max_age=600, samesite="lax")
    return resp


@app.get("/auth/google/callback")
async def google_callback(request: Request, code: str = None, state: str = None, error: str = None):
    # Step 1 — cancelled or denied by user
    if error or not code:
        logger.warning("[OAuth] Callback received error from Google: %s", error)
        return RedirectResponse(url="/login?error=google_cancelled")

    # Read credentials from env at request time (never from module-level cache)
    _client_id     = os.environ.get("GOOGLE_CLIENT_ID", "")
    _client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    _redirect_uri  = os.environ.get("GOOGLE_REDIRECT_URI", "")

    if not _client_id or not _client_secret or not _redirect_uri:
        logger.error(
            "[OAuth] Missing env vars — CLIENT_ID=%s CLIENT_SECRET=%s REDIRECT_URI=%s",
            bool(_client_id), bool(_client_secret), bool(_redirect_uri)
        )
        return RedirectResponse(url="/login?error=google_not_configured")

    try:
        import httpx

        async with httpx.AsyncClient(timeout=8.0) as client:

            # ── Step 2: Exchange authorization code for tokens ────────────────
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id":     _client_id,      # from os.environ
                    "client_secret": _client_secret,  # from os.environ
                    "code":          code,
                    "redirect_uri":  _redirect_uri,   # SAME value used in /auth/google
                    "grant_type":    "authorization_code",
                },
            )

            # ── DIAGNOSTIC: always log Google's raw response ──────────────────
            logger.info("[OAuth] Google token endpoint status : %s", token_resp.status_code)
            logger.info("[OAuth] Google token endpoint body   : %s", token_resp.text)
            # ─────────────────────────────────────────────────────────────────

            # ── Step 3: Fail fast if Google returned a non-200 ───────────────
            if token_resp.status_code != 200:
                logger.error(
                    "[OAuth] Token exchange failed — HTTP %s — %s",
                    token_resp.status_code, token_resp.text
                )
                return RedirectResponse(url="/login?error=google_token_failed")

            td = token_resp.json()

            # ── Step 4: Validate the token payload ───────────────────────────
            if "error" in td or "access_token" not in td:
                logger.error("[OAuth] Token payload invalid: %s", td)
                return RedirectResponse(url="/login?error=google_token_failed")

            # ── Step 5: Fetch user profile ────────────────────────────────────
            info_resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {td['access_token']}"}
            )
            if info_resp.status_code != 200:
                logger.error(
                    "[OAuth] Userinfo fetch failed — HTTP %s — %s",
                    info_resp.status_code, info_resp.text
                )
                return RedirectResponse(url="/login?error=google_userinfo_failed")

            info = info_resp.json()

        # ── Step 6: Extract email & name ──────────────────────────────────────
        email = info.get("email", "").lower().strip()
        name  = info.get("name", "").strip() or email.split("@")[0]
        logger.info("[OAuth] Google sign-in for email=%s", email)

        if not email:
            logger.error("[OAuth] Google returned no email in userinfo: %s", info)
            return RedirectResponse(url="/login?error=google_no_email")

        # ── Step 7: Create user if new, else use existing account ─────────────
        if not check_email_exists(email):
            create_user(
                name=name, email=email, phone="",
                password_hash=_hash_pw(secrets.token_urlsafe(32)),
                auth_provider="google"
            )
            logger.info("[OAuth] New user created via Google: %s", email)

        user         = get_user_by_email(email)
        display_name = user["name"] if user else name

        # ── Step 8: Issue session JWT and redirect ────────────────────────────
        token = create_token(email, "patient", display_name)
        resp  = RedirectResponse(url="/my-appointments", status_code=302)
        resp.set_cookie(
            "admin_token", token,
            httponly=True, max_age=ACCESS_TOKEN_EXPIRE_HOURS * 3600, samesite="lax"
        )
        resp.delete_cookie("oauth_state")
        return resp

    except httpx.TimeoutException:
        logger.error("[OAuth] Token exchange timed out after 8s")
        return RedirectResponse(url="/login?error=google_timeout")
    except httpx.RequestError as exc:
        logger.error("[OAuth] Network error during token exchange: %s", exc)
        return RedirectResponse(url="/login?error=google_network_error")
    except Exception as exc:
        logger.exception("[OAuth] Unexpected error in Google callback: %s", exc)
        return RedirectResponse(url="/login?error=google_server_error")


@app.post("/api/appointments")
async def create_appointment(request: Request):
    payload = get_current_user_payload(request)
    if not payload:
        return JSONResponse(status_code=401, content={"success": False,
            "message": "Please login to book an appointment.", "redirect": "/login"})
    try:
        body = await request.json()
        form = AppointmentForm(**body)
    except Exception:
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid form data."})
    # Auto-fill email from logged-in user to prevent mismatch
    if payload.get("role") == "patient":
        form.email = payload["sub"]
    try:
        aid = add_appointment(name=form.name, phone=form.phone, email=form.email,
            preferred_date=form.preferred_date, preferred_time=form.preferred_time,
            service=form.service, message=form.message or "")
        # Send booking confirmation email
        send_booking_confirmation(form.email, form.name, form.preferred_date,
                                  form.preferred_time, form.service, aid)
        return JSONResponse(content={"success": True, "appointment_id": aid,
            "message": "Appointment booked! ✓ A confirmation email has been sent. View it in <a href='/my-appointments'>My Appointments</a>."})
    except Exception as e:
        return JSONResponse(status_code=400, content={"success": False, "message": f"Error: {str(e)}"})


@app.get("/api/my-appointments")
async def api_my_appointments(request: Request):
    payload = get_current_user_payload(request)
    if not payload or payload.get("role") != "patient":
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    apts = get_appointments_by_email(payload.get("sub", ""))
    return JSONResponse(content={"success": True, "appointments": apts})

@app.post("/api/admin/appointments/{appointment_id}/status")
async def update_status(request: Request, appointment_id: int):
    if not get_admin_user(request):
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    body = await request.json()
    new_status = body.get("status")
    valid = ["Pending", "Confirmed", "Cancelled", "Completed"]
    if new_status not in valid:
        return JSONResponse(status_code=400, content={"success": False, "message": f"Invalid status. Must be one of: {valid}"})
    apt = get_appointment_by_id(appointment_id)
    if update_appointment_status(appointment_id, new_status):
        # Notify patient via email
        if apt:
            send_status_update(apt["email"], apt["name"], apt["preferred_date"],
                               apt["preferred_time"], apt["service"], new_status)
        return JSONResponse(content={"success": True, "message": f"Status updated to {new_status}"})
    return JSONResponse(status_code=404, content={"success": False, "message": "Appointment not found"})

@app.post("/api/contact")
async def submit_contact(form: ContactForm):
    try:
        add_contact_message(name=form.name, email=form.email, phone=form.phone or "", message=form.message)
        return JSONResponse(content={"success": True, "message": "Thank you! We will get back to you soon."})
    except Exception as e:
        return JSONResponse(status_code=400, content={"success": False, "message": f"Error: {str(e)}"})

@app.get("/api/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key="admin_token")
    return response

@app.get("/api/health")
async def health_check():
    return JSONResponse(content={"status": "ok", "clinic": CLINIC_NAME, "version": "1.0.0", "timestamp": datetime.utcnow().isoformat()})

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse("index.html", ctx(request), status_code=404)

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})
