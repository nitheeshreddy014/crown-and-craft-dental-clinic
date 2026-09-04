import os, hashlib, hmac, re, urllib.parse, secrets
import httpx
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from database import (init_db, add_appointment, get_appointments, get_appointment_by_id,
    update_appointment_status, add_contact_message, get_contact_messages,
    create_user, get_user_by_email, check_email_exists, get_appointments_by_email)
from models import AppointmentForm, ContactForm, LoginForm

CLINIC_NAME = "Crown & Craft Dental Clinic"
DOCTOR_NAME = "Dr. Maneesh Reddy Pocharam"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        print("DB init successful")
    except Exception as e:
        # Log the real error so it shows in Vercel logs
        print(f"DB init failed: {e}")
        # Do NOT crash — let the app start so routes can return proper errors
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

# ── Admin credentials (Nitheesh & Maneesh share same password) ────────────────────
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "m808234")
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

def ctx(request, **extra):
    return {"request": request, "doctor_name": DOCTOR_NAME, "clinic_name": CLINIC_NAME, **extra}

# ==================== PAGE ROUTES ====================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", ctx(request))

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if get_admin_user(request): return RedirectResponse(url="/admin", status_code=302)
    return templates.TemplateResponse("login.html", ctx(request, error=None))

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, search: str = Query(default=None), status: str = Query(default=None), date: str = Query(default=None), tab: str = Query(default="appointments")):
    admin = get_admin_user(request)
    if not admin: return RedirectResponse(url="/login", status_code=302)
    appointments = get_appointments(search=search, status_filter=status, date_filter=date)
    messages = get_contact_messages()
    return templates.TemplateResponse("admin.html", ctx(request,
        admin_user=admin, appointments=appointments, messages=messages,
        search=search or "", status_filter=status or "All", date_filter=date or "", active_tab=tab))

# ==================== API ROUTES ====================

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
    if not GOOGLE_CLIENT_ID:
        return RedirectResponse(url="/login?error=google_not_configured")
    state = secrets.token_urlsafe(16)
    params = urllib.parse.urlencode({
        "client_id":     GOOGLE_CLIENT_ID,
        "redirect_uri":  GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope":         "openid email profile",
        "state":         state,
        "access_type":   "offline",
    })
    resp = RedirectResponse(url=f"https://accounts.google.com/o/oauth2/v2/auth?{params}")
    resp.set_cookie("oauth_state", state, httponly=True, max_age=600, samesite="lax")
    return resp


@app.get("/auth/google/callback")
async def google_callback(request: Request, code: str = None, state: str = None, error: str = None):
    # Step 1 — cancelled or missing code
    if error or not code:
        return RedirectResponse(url="/login?error=google_cancelled")

    # Step 2 — verify state cookie to prevent CSRF
    stored_state = request.cookies.get("oauth_state")
    if not stored_state or stored_state != state:
        return RedirectResponse(url="/login?error=invalid_state")

    try:
        # Step 3 — exchange code for access token (8s timeout)
        async with httpx.AsyncClient(timeout=8.0) as client:
            token_r = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id":     GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "code":          code,
                    "redirect_uri":  GOOGLE_REDIRECT_URI,
                    "grant_type":    "authorization_code",
                }
            )
            td = token_r.json()

            # Step 4 — check Google returned a valid token
            if "error" in td or "access_token" not in td:
                return RedirectResponse(url="/login?error=google_token_failed")

            # Step 5 — fetch user profile from Google
            info_r = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {td['access_token']}"}
            )
            info = info_r.json()

        # Step 6 — extract email & name
        email = info.get("email", "").lower().strip()
        name  = info.get("name", "").strip() or email.split("@")[0]

        if not email:
            return RedirectResponse(url="/login?error=google_no_email")

        # Step 7 — create user only if new, else use existing account
        if not check_email_exists(email):
            create_user(
                name=name, email=email, phone="",
                password_hash=_hash_pw(secrets.token_urlsafe(32))
            )

        user  = get_user_by_email(email)
        display_name = user["name"] if user else name

        # Step 8 — issue session token and redirect
        token = create_token(email, "patient", display_name)
        resp  = RedirectResponse(url="/my-appointments", status_code=302)
        resp.set_cookie(
            "admin_token", token,
            httponly=True, max_age=ACCESS_TOKEN_EXPIRE_HOURS * 3600, samesite="lax"
        )
        # Clear the oauth state cookie
        resp.delete_cookie("oauth_state")
        return resp

    except httpx.TimeoutException:
        return RedirectResponse(url="/login?error=google_timeout")
    except httpx.RequestError:
        return RedirectResponse(url="/login?error=google_network_error")
    except Exception:
        return RedirectResponse(url="/login?error=google_server_error")


@app.post("/api/appointments")
async def create_appointment(request: Request):
    # Must be logged in to book
    payload = get_current_user_payload(request)
    if not payload:
        return JSONResponse(status_code=401, content={"success": False,
            "message": "Please login to book an appointment.", "redirect": "/login"})
    try:
        body = await request.json()
        form = AppointmentForm(**body)
    except Exception:
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid form data."})
    try:
        aid = add_appointment(name=form.name, phone=form.phone, email=form.email,
            preferred_date=form.preferred_date, preferred_time=form.preferred_time,
            service=form.service, message=form.message or "")
        return JSONResponse(content={"success": True, "appointment_id": aid,
            "message": "Appointment booked! ✓ View it in <a href='/my-appointments'>My Appointments</a>."})
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
    if update_appointment_status(appointment_id, new_status):
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
