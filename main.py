import os, bcrypt, re, logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from database import (init_db, add_appointment, get_appointments, get_appointment_by_id,
    update_appointment_status, add_contact_message, get_contact_messages,
    create_user, get_user_by_email, check_email_exists,
    get_admin_by_username, create_admin, admin_exists,
    get_all_admins, delete_admin, update_admin_password, admin_count)
from models import AppointmentForm, ContactForm, LoginForm

# ==================== LOGGING ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLINIC_NAME = "Crown & Craft Dental Clinic"
DOCTOR_NAME = "Dr. Maneesh Reddy Pocharam"

# ==================== CONFIG — must be set via environment variables ====================
# BUG FIX #3: No fallback for SECRET_KEY — must be explicitly set
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is not set. Set it before starting the server.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Initial admin seeded from env vars on first startup
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
if not ADMIN_USERNAME or not ADMIN_PASSWORD:
    raise RuntimeError("ADMIN_USERNAME and ADMIN_PASSWORD environment variables must be set.")

def _hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def _verify_pw(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

# BUG FIX #14: Rate limiter
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Seed first admin from env vars if no admins exist yet
    if not admin_exists(ADMIN_USERNAME):
        create_admin(ADMIN_USERNAME, _hash_pw(ADMIN_PASSWORD))
        logger.info(f"Seeded initial admin: {ADMIN_USERNAME}")
    logger.info(f"Database initialized. Total admins: {admin_count()}")
    yield
    logger.info("Server shutting down.")

app = FastAPI(title=CLINIC_NAME, version="1.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"success": False, "message": "Too many requests. Please wait and try again."})

# BUG FIX #11: datetime.now(timezone.utc) replaces deprecated datetime.utcnow()
def create_token(username: str, role: str = "admin") -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": username, "role": role, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

def get_admin_user(request: Request):
    # BUG FIX #6: cookie renamed from admin_token → auth_token
    token = request.cookies.get("auth_token")
    if not token: return None
    payload = verify_token(token)
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
@limiter.limit("10/minute")
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
        # BUG FIX #8: log internally, never expose raw exception to client
        logger.error(f"Registration error for {email}: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Registration failed. Please try again later."})

@app.post("/api/login")
@limiter.limit("10/minute")
async def login(request: Request, form: LoginForm):
    username = form.username.strip()
    # Check admins table — supports multiple admins with individual passwords
    admin = get_admin_by_username(username)
    if admin and _verify_pw(form.password, admin["password_hash"]):
        token = create_token(username, "admin")
        response = JSONResponse(content={"success": True, "message": f"Welcome back, {username}!", "redirect_url": "/admin"})
        response.set_cookie(key="auth_token", value=token, httponly=True,
            max_age=ACCESS_TOKEN_EXPIRE_HOURS * 3600, samesite="lax", secure=True)
        return response
    # Check patient credentials
    user = get_user_by_email(username.lower())
    if user and _verify_pw(form.password, user["password_hash"]):
        token = create_token(user["email"], "patient")
        response = JSONResponse(content={"success": True, "message": f"Welcome back, {user['name']}!", "redirect_url": "/"})
        response.set_cookie(key="auth_token", value=token, httponly=True,
            max_age=ACCESS_TOKEN_EXPIRE_HOURS * 3600, samesite="lax", secure=True)
        return response
    return JSONResponse(status_code=401, content={"success": False, "message": "Invalid username or password."})

@app.get("/api/me")
async def get_current_user(request: Request):
    token = request.cookies.get("auth_token")
    if not token: return JSONResponse(content={"logged_in": False})
    payload = verify_token(token)
    if not payload: return JSONResponse(content={"logged_in": False})
    role = payload.get("role", "patient"); sub = payload.get("sub", "")
    if role == "patient":
        user = get_user_by_email(sub)
        return JSONResponse(content={"logged_in": True, "name": user["name"] if user else sub, "email": sub, "role": role})
    return JSONResponse(content={"logged_in": True, "name": sub, "role": role})

@app.post("/api/appointments")
async def create_appointment(form: AppointmentForm):
    try:
        aid = add_appointment(name=form.name, phone=form.phone, email=form.email,
            preferred_date=form.preferred_date, preferred_time=form.preferred_time,
            service=form.service, message=form.message or "")
        return JSONResponse(content={"success": True,
            "message": "Appointment booked successfully! We will contact you shortly to confirm.",
            "appointment_id": aid})
    except Exception as e:
        # BUG FIX #8: log internally, never expose raw exception to client
        logger.error(f"Appointment creation error: {e}")
        return JSONResponse(status_code=400, content={"success": False, "message": "Failed to book appointment. Please try again."})

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
        # BUG FIX #8: log internally, never expose raw exception to client
        logger.error(f"Contact message error: {e}")
        return JSONResponse(status_code=400, content={"success": False, "message": "Failed to send message. Please try again."})

# ==================== ADMIN MANAGEMENT ROUTES ====================

@app.get("/api/admin/admins")
async def list_admins(request: Request):
    """List all admins (username + created_at only, no password hashes)."""
    if not get_admin_user(request):
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    admins = get_all_admins()
    return JSONResponse(content={"success": True, "admins": admins})

@app.post("/api/admin/admins")
async def add_admin(request: Request):
    """Add a new admin. Only existing admins can do this."""
    if not get_admin_user(request):
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    body = await request.json()
    username = body.get("username", "").strip()
    password = body.get("password", "")
    if not username or len(username) < 3:
        return JSONResponse(status_code=400, content={"success": False, "message": "Username must be at least 3 characters."})
    if not password or len(password) < 6:
        return JSONResponse(status_code=400, content={"success": False, "message": "Password must be at least 6 characters."})
    if admin_exists(username):
        return JSONResponse(status_code=409, content={"success": False, "message": f"Admin '{username}' already exists."})
    try:
        create_admin(username, _hash_pw(password))
        logger.info(f"New admin added: {username} by {get_admin_user(request)}")
        return JSONResponse(content={"success": True, "message": f"Admin '{username}' created successfully."})
    except Exception as e:
        logger.error(f"Error creating admin: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Failed to create admin."})

@app.delete("/api/admin/admins/{username}")
async def remove_admin(request: Request, username: str):
    """Delete an admin. Cannot delete yourself or the last remaining admin."""
    current = get_admin_user(request)
    if not current:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    if username == current:
        return JSONResponse(status_code=400, content={"success": False, "message": "You cannot delete your own admin account."})
    if admin_count() <= 1:
        return JSONResponse(status_code=400, content={"success": False, "message": "Cannot delete the last admin account."})
    if not admin_exists(username):
        return JSONResponse(status_code=404, content={"success": False, "message": f"Admin '{username}' not found."})
    try:
        delete_admin(username)
        logger.info(f"Admin deleted: {username} by {current}")
        return JSONResponse(content={"success": True, "message": f"Admin '{username}' deleted successfully."})
    except Exception as e:
        logger.error(f"Error deleting admin: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Failed to delete admin."})

@app.put("/api/admin/admins/{username}/password")
async def change_admin_password(request: Request, username: str):
    """Change an admin's password. Only admins can do this."""
    current = get_admin_user(request)
    if not current:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    body = await request.json()
    new_password = body.get("new_password", "")
    if not new_password or len(new_password) < 6:
        return JSONResponse(status_code=400, content={"success": False, "message": "New password must be at least 6 characters."})
    if not admin_exists(username):
        return JSONResponse(status_code=404, content={"success": False, "message": f"Admin '{username}' not found."})
    try:
        update_admin_password(username, _hash_pw(new_password))
        logger.info(f"Password changed for admin: {username} by {current}")
        return JSONResponse(content={"success": True, "message": f"Password for '{username}' updated successfully."})
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Failed to update password."})

# BUG FIX #5: Changed GET → POST to prevent CSRF logout attacks
@app.post("/api/logout")
async def logout():
    response = JSONResponse(content={"success": True, "message": "Logged out successfully."})
    response.delete_cookie(key="auth_token")
    return response

@app.get("/api/health")
async def health_check():
    # BUG FIX #11: datetime.now(timezone.utc) replaces deprecated datetime.utcnow()
    return JSONResponse(content={"status": "ok", "clinic": CLINIC_NAME, "version": "1.0.0", "timestamp": datetime.now(timezone.utc).isoformat()})

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse("index.html", ctx(request), status_code=404)

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})
