import os, hashlib, hmac, re
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from database import (init_db, add_appointment, get_appointments, get_appointment_by_id,
    update_appointment_status, add_contact_message, get_contact_messages,
    create_user, get_user_by_email, check_email_exists)
from models import AppointmentForm, ContactForm, LoginForm

CLINIC_NAME = "Crown & Craft Dental Clinic"
DOCTOR_NAME = "Dr. Maneesh Reddy Pocharam"

app = FastAPI(title=CLINIC_NAME, version="1.0.0")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

SECRET_KEY = os.getenv("SECRET_KEY", "crown-craft-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

def _hash_pw(pw):
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def _verify_pw(plain, hashed):
    return hmac.compare_digest(_hash_pw(plain), hashed)

ADMIN_PASSWORD_HASH = _hash_pw(ADMIN_PASSWORD)

@app.on_event("startup")
async def startup_event():
    init_db()

def create_token(username, role="admin"):
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": username, "role": role, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

def get_admin_user(request):
    token = request.cookies.get("admin_token")
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
    username = form.username.strip()
    # Check admin credentials first
    if username == ADMIN_USERNAME and _verify_pw(form.password, ADMIN_PASSWORD_HASH):
        token = create_token(username, "admin")
        response = JSONResponse(content={"success": True, "message": "Welcome back, Admin!", "redirect_url": "/admin"})
        response.set_cookie(key="admin_token", value=token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_HOURS * 3600, samesite="lax")
        return response
    # Check patient credentials
    user = get_user_by_email(username.lower())
    if user and _verify_pw(form.password, user["password_hash"]):
        token = create_token(user["email"], "patient")
        response = JSONResponse(content={"success": True, "message": f"Welcome back, {user['name']}!", "redirect_url": "/"})
        response.set_cookie(key="admin_token", value=token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_HOURS * 3600, samesite="lax")
        return response
    return JSONResponse(status_code=401, content={"success": False, "message": "Invalid email/username or password."})

@app.get("/api/me")
async def get_current_user(request: Request):
    token = request.cookies.get("admin_token")
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
        return JSONResponse(status_code=400, content={"success": False, "message": f"Error: {str(e)}"})

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
