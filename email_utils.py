import smtplib, os, logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("crown_craft")

GMAIL_USER        = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD= os.getenv("GMAIL_APP_PASSWORD", "")
CLINIC_NAME       = "Crown & Craft Dental Clinic"
CLINIC_PHONE      = "+91 99493 35358"
CLINIC_ADDRESS    = "123 Dental Avenue, Banjara Hills, Hyderabad"
BASE_URL          = os.getenv("BASE_URL", "https://crown-and-craft-dental-clinic-2153.vercel.app")

# ── shared HTML wrapper ───────────────────────────────────────────────────────
def _wrap(body_html: str) -> str:
    return f"""
<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
  body{{font-family:'Segoe UI',Arial,sans-serif;background:#0f172a;color:#e2e8f0;margin:0;padding:0}}
  .wrap{{max-width:580px;margin:30px auto;background:#1e293b;border-radius:16px;overflow:hidden;border:1px solid rgba(255,255,255,.08)}}
  .hdr{{background:linear-gradient(135deg,#0ea5e9,#8b5cf6);padding:28px 32px;text-align:center}}
  .hdr h1{{margin:0;color:#fff;font-size:1.4rem;font-weight:700}}
  .hdr p{{margin:6px 0 0;color:rgba(255,255,255,.8);font-size:.9rem}}
  .body{{padding:28px 32px}}
  .body p{{color:#cbd5e1;line-height:1.7;margin:0 0 14px}}
  .info-box{{background:rgba(14,165,233,.08);border:1px solid rgba(14,165,233,.2);border-radius:10px;padding:16px 20px;margin:18px 0}}
  .info-row{{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.05);font-size:.88rem}}
  .info-row:last-child{{border-bottom:none}}
  .info-label{{color:#94a3b8}}
  .info-value{{color:#f1f5f9;font-weight:600}}
  .btn{{display:inline-block;padding:12px 28px;background:linear-gradient(135deg,#0ea5e9,#8b5cf6);color:#fff;text-decoration:none;border-radius:8px;font-weight:600;font-size:.9rem;margin:8px 0}}
  .ftr{{background:rgba(255,255,255,.03);border-top:1px solid rgba(255,255,255,.06);padding:18px 32px;text-align:center;font-size:.78rem;color:#64748b}}
  .ftr a{{color:#0ea5e9;text-decoration:none}}
</style></head><body>
<div class="wrap">
  <div class="hdr"><h1>🦷 {CLINIC_NAME}</h1><p>Your Smile, Our Passion</p></div>
  <div class="body">{body_html}</div>
  <div class="ftr">
    📍 {CLINIC_ADDRESS}<br>📞 {CLINIC_PHONE}<br><br>
    <a href="{BASE_URL}">{BASE_URL}</a><br><br>
    © 2024 {CLINIC_NAME}. All rights reserved.
  </div>
</div></body></html>"""


def send_email(to: str, subject: str, html_body: str) -> bool:
    """Send email via Gmail SMTP. Returns True on success."""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        logger.warning("[Email] GMAIL_USER or GMAIL_APP_PASSWORD not configured — skipping email to %s", to)
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{CLINIC_NAME} <{GMAIL_USER}>"
        msg["To"]      = to
        msg.attach(MIMEText(_wrap(html_body), "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            smtp.sendmail(GMAIL_USER, to, msg.as_string())
        logger.info("[Email] ✓ Sent '%s' to %s", subject, to)
        return True
    except Exception as e:
        logger.error("[Email] ✗ Failed to send to %s: %s", to, e)
        return False


# ── Email templates ────────────────────────────────────────────────────────────

def send_booking_confirmation(to: str, name: str, date: str, time: str, service: str, apt_id: int):
    body = f"""
<p>Hi <strong>{name}</strong>,</p>
<p>Your appointment request has been received! ✅ We will confirm it shortly.</p>
<div class="info-box">
  <div class="info-row"><span class="info-label">Appointment ID</span><span class="info-value">#{apt_id}</span></div>
  <div class="info-row"><span class="info-label">Service</span><span class="info-value">{service}</span></div>
  <div class="info-row"><span class="info-label">Date</span><span class="info-value">{date}</span></div>
  <div class="info-row"><span class="info-label">Time</span><span class="info-value">{time}</span></div>
  <div class="info-row"><span class="info-label">Doctor</span><span class="info-value">Dr. Maneesh Reddy Pocharam</span></div>
  <div class="info-row"><span class="info-label">Status</span><span class="info-value">⏳ Pending Confirmation</span></div>
</div>
<p>You can track your appointment status anytime from your patient portal:</p>
<p style="text-align:center"><a href="{BASE_URL}/my-appointments" class="btn">View My Appointments</a></p>
<p>If you need to reschedule or have any questions, please call us at <strong>{CLINIC_PHONE}</strong>.</p>
<p>See you soon! 😊</p>"""
    return send_email(to, f"✅ Appointment Booked — {service} on {date}", body)


def send_status_update(to: str, name: str, date: str, time: str, service: str, new_status: str):
    icons = {"Confirmed": "✅", "Cancelled": "❌", "Completed": "🏆", "Pending": "⏳"}
    icon  = icons.get(new_status, "📋")
    body  = f"""
<p>Hi <strong>{name}</strong>,</p>
<p>Your appointment status has been updated.</p>
<div class="info-box">
  <div class="info-row"><span class="info-label">Service</span><span class="info-value">{service}</span></div>
  <div class="info-row"><span class="info-label">Date</span><span class="info-value">{date}</span></div>
  <div class="info-row"><span class="info-label">Time</span><span class="info-value">{time}</span></div>
  <div class="info-row"><span class="info-label">New Status</span><span class="info-value">{icon} {new_status}</span></div>
</div>
{'<p>Please arrive 5 minutes early. If you need to cancel, contact us at least 2 hours before your appointment.</p>' if new_status == 'Confirmed' else ''}
<p style="text-align:center"><a href="{BASE_URL}/my-appointments" class="btn">View My Appointments</a></p>"""
    return send_email(to, f"{icon} Appointment {new_status} — {service} on {date}", body)


def send_reminder(to: str, name: str, date: str, time: str, service: str):
    body = f"""
<p>Hi <strong>{name}</strong>,</p>
<p>This is a friendly reminder that you have a dental appointment <strong>tomorrow</strong>! 🗓️</p>
<div class="info-box">
  <div class="info-row"><span class="info-label">Service</span><span class="info-value">{service}</span></div>
  <div class="info-row"><span class="info-label">Date</span><span class="info-value">{date}</span></div>
  <div class="info-row"><span class="info-label">Time</span><span class="info-value">{time}</span></div>
  <div class="info-row"><span class="info-label">Doctor</span><span class="info-value">Dr. Maneesh Reddy Pocharam</span></div>
  <div class="info-row"><span class="info-label">Address</span><span class="info-value">{CLINIC_ADDRESS}</span></div>
</div>
<p><strong>Please remember to:</strong></p>
<p>• Bring any previous dental records or X-rays<br>
   • Arrive 5–10 minutes early<br>
   • Inform us of any medications you are currently taking</p>
<p>Questions? Call us at <strong>{CLINIC_PHONE}</strong>.</p>"""
    return send_email(to, f"🗓️ Reminder: Appointment Tomorrow at {time}", body)


def send_password_reset(to: str, name: str, reset_token: str):
    reset_url = f"{BASE_URL}/reset-password?token={reset_token}"
    body = f"""
<p>Hi <strong>{name}</strong>,</p>
<p>We received a request to reset your password. Click the button below to set a new password:</p>
<p style="text-align:center"><a href="{reset_url}" class="btn">🔑 Reset My Password</a></p>
<div class="info-box">
  <div class="info-row"><span class="info-label">⚠️ Expires in</span><span class="info-value">30 minutes</span></div>
  <div class="info-row"><span class="info-label">Valid for</span><span class="info-value">One use only</span></div>
</div>
<p>If you did not request a password reset, please ignore this email — your account is safe.</p>
<p style="font-size:.8rem;color:#64748b;">If the button does not work, copy this link: {reset_url}</p>"""
    return send_email(to, "🔑 Reset Your Password — Crown & Craft Dental", body)


def send_cancellation_confirmation(to: str, name: str, date: str, time: str, service: str):
    body = f"""
<p>Hi <strong>{name}</strong>,</p>
<p>Your appointment has been successfully cancelled.</p>
<div class="info-box">
  <div class="info-row"><span class="info-label">Service</span><span class="info-value">{service}</span></div>
  <div class="info-row"><span class="info-label">Date</span><span class="info-value">{date}</span></div>
  <div class="info-row"><span class="info-label">Time</span><span class="info-value">{time}</span></div>
  <div class="info-row"><span class="info-label">Status</span><span class="info-value">❌ Cancelled</span></div>
</div>
<p>We hope to see you again soon! Book a new appointment whenever you are ready:</p>
<p style="text-align:center"><a href="{BASE_URL}/#appointments" class="btn">Book New Appointment</a></p>"""
    return send_email(to, f"❌ Appointment Cancelled — {service} on {date}", body)
