# 🦷 Crown & Craft Dental Clinic — Dr. Maneesh Reddy Pocharam

A **complete, end-to-end, production-ready** dental clinic website built with **FastAPI**, **Jinja2**, **SQLite**, and modern **HTML/CSS/JavaScript**. Features a premium, highly animated UI, online appointment booking, patient registration & login, and a fully functional admin dashboard.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [Project Structure](#project-structure)
- [Getting Started — Local Setup](#getting-started--local-setup)
- [Local URLs](#local-urls)
- [Test Credentials](#test-credentials)
- [API Endpoints](#api-endpoints)
- [Push to GitHub](#push-to-github)
- [Deploy to Render (Free)](#deploy-to-render-free)
- [Free Domain Options](#free-domain-options)
- [Environment Variables](#environment-variables)
- [Production Checklist](#production-checklist)
- [License](#license)

---

## Overview

**Crown & Craft Dental Clinic** is a full-stack web application for managing a dental clinic's online presence.

- **Doctor:** Dr. Maneesh Reddy Pocharam
- **Clinic:** Crown & Craft Dental Clinic
- **Frontend:** Premium animated UI with glassmorphism, floating elements, scroll reveals, testimonial sliders, FAQ accordion, and more.
- **Backend:** FastAPI with Jinja2 templating, SQLite database, JWT authentication.
- **Auth:** Dual login — Admin dashboard access + Patient registration & login.

---

## Tech Stack

| Component     | Technology                          |
|---------------|-------------------------------------|
| Backend       | Python 3.10+, FastAPI               |
| Templating    | Jinja2                              |
| Database      | SQLite (dev) / PostgreSQL (prod)    |
| Frontend      | HTML5, CSS3, JavaScript (Vanilla)   |
| Auth          | JWT (python-jose) + SHA-256 hashing |
| Fonts         | Google Fonts (Inter, Playfair Display) |
| Deployment    | Render.com (Free Tier)              |

---

## Features

### 🌐 Public Website
- ✅ Animated loading screen
- ✅ Smooth scroll navigation with active link highlighting
- ✅ Hero section with animated gradient background & floating dental elements
- ✅ About section (clinic + doctor info with photo) with animated stats counter
- ✅ 9 service cards with glassmorphism & hover animations
- ✅ Appointment booking form with client & server-side validation
- ✅ Testimonial slider (auto-rotate + dot navigation)
- ✅ FAQ accordion (8 questions)
- ✅ Contact section with form, info cards, map, clinic hours
- ✅ Responsive design (mobile, tablet, desktop)
- ✅ Toast notifications
- ✅ Premium CSS animations (glassmorphism, glow, parallax, reveals)

### 🔐 Authentication & Login
- ✅ Premium login page with Sign In / Sign Up tabs
- ✅ Patient registration with email & password
- ✅ Password strength meter (Weak / Fair / Good / Strong)
- ✅ Show/hide password toggle
- ✅ Forgot password modal with contact info
- ✅ Admin login → redirects to dashboard
- ✅ Patient login → redirects to home page
- ✅ JWT-based authentication with HTTP-only cookies

### 📊 Admin Dashboard
- ✅ Secure dashboard with JWT authentication
- ✅ Appointment management (view, search, filter by status/date, update status)
- ✅ Contact message viewer
- ✅ Summary cards (Total, Pending, Confirmed, Completed, Cancelled)
- ✅ Mobile-responsive sidebar layout
- ✅ Toast notifications for actions

---

## Project Structure

```
CrownAndCraft_DrManeeshReddy/
├── main.py                 # FastAPI application
├── database.py             # SQLite database operations
├── models.py               # Pydantic validation models
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── .gitignore              # Git ignore rules
├── data/                   # Database directory (auto-created)
│   └── clinic.db           # SQLite database (auto-created)
├── static/
│   ├── css/
│   │   └── style.css       # Premium animated stylesheet
│   ├── js/
│   │   └── main.js         # Frontend interactivity
│   └── images/
│       └── maneesh.png     # Doctor photo
└── templates/
    ├── index.html           # Main website (all sections)
    ├── login.html           # Login page (Sign In / Sign Up)
    └── admin.html           # Admin dashboard
```

---

## Getting Started — Local Setup

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)
- Git

### Installation Steps

```bash
# 1. Navigate to the project folder
cd CrownAndCraft_DrManeeshReddy

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate the virtual environment
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the development server
uvicorn main:app --reload

# 6. Open your browser
# Visit: http://127.0.0.1:8000
```

> 💡 The database (`data/clinic.db`) is created automatically on first run.

---

## Local URLs

| Page               | URL                              |
|--------------------|----------------------------------|
| 🏠 Home            | http://127.0.0.1:8000            |
| 🔐 Login           | http://127.0.0.1:8000/login      |
| 📊 Admin Dashboard | http://127.0.0.1:8000/admin      |
| 💚 Health Check    | http://127.0.0.1:8000/api/health |

---

## Test Credentials

| Role    | Username/Email     | Password   | Redirects To |
|---------|--------------------|------------|--------------|
| Admin   | `admin`            | `admin123` | /admin       |
| Patient | Sign up first      | Your password | /         |

> ⚠️ **Change admin credentials before deploying to production!**

---

## API Endpoints

| Method | Endpoint                                  | Description              | Auth  |
|--------|-------------------------------------------|--------------------------|-------|
| GET    | `/`                                        | Home page                | No    |
| GET    | `/login`                                   | Login page               | No    |
| GET    | `/admin`                                   | Admin dashboard          | Admin |
| POST   | `/api/register`                            | Patient registration     | No    |
| POST   | `/api/login`                               | Login (admin + patient)  | No    |
| GET    | `/api/me`                                  | Current user info        | Yes   |
| POST   | `/api/appointments`                        | Book appointment         | No    |
| POST   | `/api/admin/appointments/{id}/status`      | Update appointment status| Admin |
| POST   | `/api/contact`                             | Submit contact form      | No    |
| GET    | `/api/logout`                              | Logout                   | Yes   |
| GET    | `/api/health`                              | Health check             | No    |

---

## Push to GitHub

### Step 1: Create `.gitignore`

```
__pycache__/
*.pyc
.venv/
data/
.env
*.db
```

### Step 2: Push

```bash
git init
git add .
git commit -m "Crown & Craft Dental Clinic - initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/crown-and-craft-dental.git
git push -u origin main
```

---

## Deploy to Render (Free)

### Step-by-Step

1. Go to [render.com](https://render.com) → **Sign up with GitHub**
2. Click **New → Web Service**
3. **Connect** your `crown-and-craft-dental` repository
4. Configure:
   - **Name:** `crown-and-craft-dental`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add **Environment Variables:**
   - `SECRET_KEY` = (generate a strong random string)
   - `ADMIN_USERNAME` = your_admin_username
   - `ADMIN_PASSWORD` = your_strong_password
6. Click **Deploy** 🚀
7. Your site will be live at: `https://crown-and-craft-dental.onrender.com`

> ⏱️ First deploy takes 2-5 minutes. Free tier may sleep after 15 min of inactivity.

---

## Free Domain Options

| Option | Cost | How to Get |
|--------|------|------------|
| **Render subdomain** | 🆓 Free | Auto: `yourapp.onrender.com` |
| **is-a.dev** | 🆓 Free | GitHub PR at [is-a.dev](https://is-a.dev) |
| **Namecheap .com** | ~₹99/yr | [namecheap.com](https://namecheap.com) first year deal |
| **Cloudflare** | ~₹700/yr | [cloudflare.com](https://cloudflare.com) with free DNS |

### Connect Custom Domain on Render
1. Go to Render Dashboard → Your Service → **Settings**
2. Scroll to **Custom Domains** → Click **Add Custom Domain**
3. Enter your domain (e.g., `crownandcraft.com`)
4. Add the DNS records shown in your domain registrar
5. Wait for SSL certificate (automatic, takes a few minutes)

---

## Environment Variables

| Variable         | Default     | Description            |
|------------------|-------------|------------------------|
| `SECRET_KEY`     | *(change!)* | JWT signing secret key |
| `ADMIN_USERNAME` | `admin`     | Admin login username   |
| `ADMIN_PASSWORD` | `admin123`  | Admin login password   |

---

## Production Checklist

- [ ] Change admin credentials via environment variables
- [ ] Change SECRET_KEY to a strong random string (min 32 chars)
- [ ] Replace SQLite with PostgreSQL for production
- [ ] Enable HTTPS (Render handles this automatically)
- [ ] Update clinic information (address, phone, email, map)
- [ ] Add real testimonials and clinic photos
- [ ] Set up email notifications for new appointments
- [ ] Add rate limiting to API endpoints
- [ ] Add Google Analytics tracking

---

## License

This project is open source and available under the [MIT License](https://opensource.org/licenses/MIT).

---

> Built with ❤️ for **Crown & Craft Dental Clinic** | **Dr. Maneesh Reddy Pocharam**

