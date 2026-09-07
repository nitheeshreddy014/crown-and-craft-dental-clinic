# 🦷 Crown & Craft Dental Clinic — Dr. Maneesh Reddy Pocharam

A **complete, production-ready** dental clinic website built with **FastAPI**, **Jinja2**, **Turso (LibSQL)**, and modern **HTML/CSS/JavaScript**. Features a premium animated UI, online appointment booking, patient portal, email notifications, blog, analytics dashboard, 2FA, and more — all deployed on **Vercel** for free.

🌐 **Live:** [crown-and-craft-dental-clinic-2153.vercel.app](https://crown-and-craft-dental-clinic-2153.vercel.app)

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
- [Environment Variables](#environment-variables)
- [Deploy to Vercel](#deploy-to-vercel)
- [External Services (All Free, No Card)](#external-services-all-free-no-card)
- [Free Domain Options](#free-domain-options)
- [Production Checklist](#production-checklist)
- [License](#license)

---

## Overview

**Crown & Craft Dental Clinic** is a full-stack web application for managing a dental clinic's online presence.

- **Doctor:** Dr. Maneesh Reddy Pocharam (BDS, MDS — Prosthodontics)
- **Clinic:** Crown & Craft Dental Clinic, Banjara Hills, Hyderabad
- **Frontend:** Premium animated UI with glassmorphism, floating elements, scroll reveals, testimonial slider, FAQ accordion, blog, and more
- **Backend:** FastAPI with Jinja2 templating, Turso (LibSQL) serverless database, JWT authentication
- **Auth:** Google OAuth 2.0 + Email/Password — Admin dashboard + Patient portal
- **Emails:** Gmail SMTP (free, no card) — booking confirmations, reminders, password reset, status updates
- **Deployment:** Vercel (free, serverless, with daily cron jobs)

---

## Tech Stack

| Component      | Technology                                      |
|----------------|-------------------------------------------------|
| Backend        | Python 3.12, FastAPI                            |
| Templating     | Jinja2                                          |
| Database       | Turso (LibSQL) — serverless, free 9 GB          |
| Frontend       | HTML5, CSS3, Vanilla JavaScript                 |
| Auth           | JWT (python-jose) + SHA-256 + Google OAuth 2.0  |
| Email          | Gmail SMTP (smtplib — no card required)         |
| 2FA            | pyotp (TOTP — Google Authenticator compatible)  |
| File Storage   | Cloudinary (free 25 GB — no card required)      |
| Charts         | Chart.js (free, CDN)                            |
| Fonts          | Google Fonts (Inter, Playfair Display)          |
| Deployment     | Vercel (free Hobby plan)                        |
| Cron Jobs      | Vercel Cron (daily appointment reminders)       |

---

## Features

### 🌐 Public Website
- ✅ Animated loading screen with tooth SVG
- ✅ Smooth scroll navigation with active link highlighting
- ✅ Hero section with animated gradient & floating dental elements
- ✅ About section — clinic + doctor photo with animated stats counter
- ✅ 9 service cards with glassmorphism & hover animations
- ✅ Testimonial slider (auto-rotate + dot navigation)
- ✅ FAQ accordion (8 questions)
- ✅ Contact section with form, map, and clinic hours
- ✅ Blog preview section (latest 3 articles shown on homepage)
- ✅ WhatsApp floating button (click-to-chat, completely free)
- ✅ Local SEO — schema.org Dentist JSON-LD structured data
- ✅ Open Graph meta tags for social sharing
- ✅ Responsive design (mobile, tablet, desktop)

### 🔐 Authentication
- ✅ Email + password registration and login
- ✅ Google OAuth 2.0 — Continue with Google
- ✅ Account merging by email — same account whether via Google or email/password
- ✅ JWT-based sessions via HTTP-only cookies
- ✅ Password strength meter
- ✅ Forgot password — real email reset link (30-minute expiry)
- ✅ Password reset page with token verification

### 👤 Patient Portal (/my-appointments)
- ✅ Appointments tab — full history with status badges
- ✅ Cancel appointment — one click, cancellation email sent automatically
- ✅ Dental Records tab — upload X-rays, prescriptions, invoices via Cloudinary URL
- ✅ Profile tab — edit name and phone number
- ✅ Appointment email auto-filled from logged-in user (no mismatch bug)

### 📧 Email Notifications (Gmail SMTP — free, no card)
- ✅ Booking confirmation email on every new appointment
- ✅ Status update email when admin confirms / cancels / completes
- ✅ Cancellation confirmation email when patient cancels
- ✅ Password reset email with secure link
- ✅ Daily reminder email 24 hours before confirmed appointments (Vercel Cron)

### 📊 Admin Dashboard (/admin)
- ✅ Appointment management — search, filter by status/date, update status
- ✅ Contact message viewer
- ✅ Summary cards (Total, Pending, Confirmed, Completed, Cancelled)
- ✅ Analytics tab — Chart.js: bookings per month, popular services, status breakdown, unique patients
- ✅ Slot Management tab — add, block, delete available appointment slots
- ✅ 2FA tab — TOTP setup with QR code (Google Authenticator compatible, free)
- ✅ Mobile-responsive sidebar

### 📝 Content Pages
- ✅ /doctor — Dr. Maneesh credentials, qualifications, career timeline, affiliations
- ✅ /services — All services with descriptions, duration, and starting prices
- ✅ /blog — Dental tips blog with 5 articles pre-seeded in DB
- ✅ /blog/{slug} — Individual article page with sidebar

### ⚡ Cron Job
- ✅ Daily reminder emails at 9 AM IST via Vercel Cron (/api/cron/reminders)
- ✅ Secured with CRON_SECRET environment variable

---

## Project Structure

```
DentalClinic_DrManeeshReddy/
├── main.py                   # FastAPI app — all routes
├── database.py               # Turso DB operations (all tables)
├── models.py                 # Pydantic validation models
├── email_utils.py            # Gmail SMTP — all email templates
├── requirements.txt          # Python dependencies
├── vercel.json               # Vercel config + daily cron job
├── README.md
├── static/
│   ├── css/style.css         # Premium animated stylesheet
│   ├── js/main.js            # Frontend interactivity
│   └── images/maneesh.png    # Doctor photo
└── templates/
    ├── index.html            # Homepage (all public sections)
    ├── login.html            # Sign In / Sign Up / Forgot Password
    ├── reset_password.html   # Password reset page
    ├── my_appointments.html  # Patient portal (3 tabs)
    ├── admin.html            # Admin dashboard (5 tabs)
    ├── doctor.html           # Doctor credentials page
    ├── services.html         # All services with pricing
    └── blog.html             # Blog list + single post view
```

---

## Getting Started — Local Setup

### Prerequisites
- Python 3.10+
- pip
- Git
- A Turso account (free) — turso.tech

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/nitheeshreddy014/crown-and-craft-dental-clinic.git
cd crown-and-craft-dental-clinic

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create a .env file with required variables (see Environment Variables below)

# 5. Run the development server
uvicorn main:app --reload

# 6. Open your browser at http://127.0.0.1:8000
```

---

## Local URLs

| Page | URL |
|---|---|
| 🏠 Home | http://127.0.0.1:8000 |
| 🔐 Login | http://127.0.0.1:8000/login |
| 👤 Patient Portal | http://127.0.0.1:8000/my-appointments |
| 📊 Admin Dashboard | http://127.0.0.1:8000/admin |
| 👨‍⚕️ Doctor Page | http://127.0.0.1:8000/doctor |
| 🦷 Services | http://127.0.0.1:8000/services |
| 📝 Blog | http://127.0.0.1:8000/blog |
| 🔑 Reset Password | http://127.0.0.1:8000/reset-password |
| 💚 Health Check | http://127.0.0.1:8000/api/health |

---

## Test Credentials

| Role | Username | Password | Redirects To |
|---|---|---|---|
| Admin (Nitheesh) | nitheesh | set via env var | /admin |
| Admin (Maneesh) | maneesh | set via env var | /admin |
| Patient | Register on /login | your choice | / |

> ⚠️ Admin credentials are set via the ADMIN_USERS environment variable — never hardcode them.

---

## API Endpoints

### Public
| Method | Endpoint | Description |
|---|---|---|
| GET | / | Homepage |
| GET | /doctor | Doctor credentials page |
| GET | /services | Services page |
| GET | /blog | Blog list |
| GET | /blog/{slug} | Single blog post |
| GET | /login | Login / Register page |
| GET | /reset-password?token= | Password reset page |
| POST | /api/register | Patient registration |
| POST | /api/login | Login |
| POST | /api/contact | Contact form |
| POST | /api/forgot-password | Send password reset email |
| POST | /api/reset-password | Reset password with token |
| GET | /api/logout | Logout |
| GET | /auth/google | Start Google OAuth |
| GET | /auth/google/callback | Google OAuth callback |

### Patient (login required)
| Method | Endpoint | Description |
|---|---|---|
| GET | /my-appointments | Patient portal |
| POST | /api/appointments | Book appointment |
| POST | /api/appointments/{id}/cancel | Cancel own appointment |
| PUT | /api/profile | Update name and phone |
| GET | /api/records | List dental records |
| POST | /api/records | Save dental record (Cloudinary URL) |
| DELETE | /api/records/{id} | Delete dental record |

### Admin only
| Method | Endpoint | Description |
|---|---|---|
| GET | /admin | Admin dashboard |
| POST | /api/admin/appointments/{id}/status | Update appointment status |
| GET | /api/admin/analytics | Analytics data (JSON) |
| GET | /api/admin/slots | List available slots |
| POST | /api/admin/slots | Add a slot |
| DELETE | /api/admin/slots/{id} | Delete a slot |
| PATCH | /api/admin/slots/{id} | Block / unblock a slot |
| POST | /api/admin/2fa/setup | Generate 2FA secret and QR code |
| POST | /api/admin/2fa/verify | Verify TOTP code |

### Cron (Vercel — runs daily at 9 AM IST)
| Method | Endpoint | Description |
|---|---|---|
| GET | /api/cron/reminders | Send reminder emails (secured by CRON_SECRET) |

---

## Environment Variables

Add these in **Vercel → Settings → Environment Variables** (or a local .env file):

| Variable | Required | Description |
|---|---|---|
| TURSO_DATABASE_URL | ✅ Yes | Turso DB URL — libsql://xxx.turso.io |
| TURSO_AUTH_TOKEN | ✅ Yes | Turso auth token |
| SECRET_KEY | ✅ Yes | JWT signing secret (min 32 chars, random string) |
| ADMIN_USERS | ✅ Yes | JSON: {"nitheesh":"hashed_pw","maneesh":"hashed_pw"} |
| GMAIL_USER | ✅ Yes | Gmail address used for sending emails |
| GMAIL_APP_PASSWORD | ✅ Yes | Gmail App Password (16 chars — see below) |
| BASE_URL | ✅ Yes | Your live URL e.g. https://xxx.vercel.app |
| CRON_SECRET | ✅ Yes | Any random string — secures the cron route |
| GOOGLE_CLIENT_ID | ⚠️ OAuth | Google OAuth Client ID |
| GOOGLE_CLIENT_SECRET | ⚠️ OAuth | Google OAuth Client Secret |
| GOOGLE_REDIRECT_URI | ⚠️ OAuth | https://yoursite.vercel.app/auth/google/callback |

### How to get a Gmail App Password (free, no card needed)
1. Go to myaccount.google.com
2. Security → 2-Step Verification → enable it
3. Search App Passwords → select Mail → Other → name it Crown Craft
4. Copy the 16-character password → paste as GMAIL_APP_PASSWORD

---

## Deploy to Vercel

1. Push your code to GitHub (already done)
2. Go to vercel.com → New Project → import your repo
3. Framework: Other (auto-detected via vercel.json)
4. Add all environment variables listed above
5. Click Deploy 🚀

Vercel auto-deploys on every push to main. The cron job fires daily at 3:00 AM UTC (9:00 AM IST).

---

## External Services (All Free, No Card)

| Service | Used For | Free Limit |
|---|---|---|
| Turso (turso.tech) | Database | 9 GB, 500 DBs |
| Vercel (vercel.com) | Hosting + Cron jobs | Hobby plan |
| Gmail SMTP | All transactional emails | 500 emails/day |
| Cloudinary (cloudinary.com) | Dental records / file upload | 25 GB storage |
| pyotp | Admin 2FA (TOTP) | Open source |
| Chart.js | Analytics charts | Open source CDN |
| QRCode.js | 2FA QR code generation | Open source CDN |

---

## Free Domain Options

| Option | Cost | Notes |
|---|---|---|
| Vercel subdomain | Free | Auto: yourapp.vercel.app |
| is-a.dev | Free | GitHub PR at is-a.dev |
| Namecheap .com | ~₹99/yr | First year deal |

To connect a custom domain: Vercel → Project → Settings → Domains → Add.

---

## Production Checklist

- [ ] Set strong SECRET_KEY (min 32 random chars)
- [ ] Set admin credentials via ADMIN_USERS env var (never hardcode)
- [ ] Configure GMAIL_USER + GMAIL_APP_PASSWORD for emails
- [ ] Set BASE_URL to your live Vercel URL
- [ ] Set CRON_SECRET to a random string
- [ ] Configure Google OAuth credentials (for Continue with Google)
- [ ] Sign up on Cloudinary (free, no card) for dental records upload
- [ ] Set up admin 2FA from Admin → 🔐 2FA tab
- [ ] Replace placeholder clinic address, phone, email in templates
- [ ] Add real doctor photo at static/images/maneesh.png
- [ ] Update Google Maps embed in index.html with real clinic location

---

## License

This project is open source and available under the [MIT License](https://opensource.org/licenses/MIT).

---

> Built with ❤️ for **Crown & Craft Dental Clinic** | **Dr. Maneesh Reddy Pocharam**
