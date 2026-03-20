"""
Notification Service — Email (SMTP/Flask-Mail) + SMS (Twilio)
Weekly Friday digest + individual expiry reminders
"""
import os
import json
from datetime import datetime, date, timedelta
from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    "cms",
    broker=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://redis:6379/0"),
)

# ── Celery Beat schedule — every Friday at 08:00 ──────────────────────────
celery_app.conf.beat_schedule = {
    "weekly-friday-reminder": {
        "task": "app.services.notifications.notification_service.send_weekly_friday_digest",
        "schedule": crontab(hour=8, minute=0, day_of_week="friday"),
    },
    "daily-expiry-check": {
        "task": "app.services.notifications.notification_service.check_and_send_reminders",
        "schedule": crontab(hour=7, minute=0),   # daily 07:00
    },
}
celery_app.conf.timezone = "Africa/Kigali"


# ── Individual reminder task ───────────────────────────────────────────────
@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def send_contract_reminder(self, reminder_id: int):
    """Send a single contract expiry reminder (email + SMS)."""
    from app import create_app, db
    from app.models import Reminder, Contract, User
    app = create_app("production")
    with app.app_context():
        reminder = Reminder.query.get(reminder_id)
        if not reminder or reminder.status == "SENT":
            return
        contract = reminder.contract
        owner    = User.query.get(contract.owner_id)
        if not owner:
            return
        errors = []
        # Email
        if reminder.reminder_type in ("EMAIL", "BOTH") and owner.email_opt_in:
            try:
                send_expiry_email(app, contract, owner, reminder.days_before)
                from app import METRICS
                METRICS["reminder_email_sent"].labels(status="sent").inc()
            except Exception as e:
                errors.append(f"email:{e}")
                from app import METRICS
                METRICS["reminder_email_sent"].labels(status="failed").inc()
        # SMS
        if reminder.reminder_type in ("SMS", "BOTH") and owner.sms_opt_in and owner.phone:
            try:
                send_expiry_sms(owner.phone, contract, reminder.days_before)
                from app import METRICS
                METRICS["reminder_sms_sent"].labels(status="sent").inc()
            except Exception as e:
                errors.append(f"sms:{e}")
                from app import METRICS
                METRICS["reminder_sms_sent"].labels(status="failed").inc()
        # Update status
        reminder.status  = "FAILED" if errors else "SENT"
        reminder.sent_at = datetime.utcnow()
        reminder.error_message = "; ".join(errors) if errors else None
        db.session.commit()
        if errors:
            raise self.retry(exc=Exception("; ".join(errors)))


# ── Daily expiry check task ────────────────────────────────────────────────
@celery_app.task
def check_and_send_reminders():
    """Find all pending reminders due today and dispatch them."""
    from app import create_app, db
    from app.models import Reminder
    app = create_app("production")
    with app.app_context():
        now      = datetime.utcnow()
        due      = Reminder.query.filter(
            Reminder.status == "PENDING",
            Reminder.scheduled_at <= now,
        ).all()
        count = 0
        for r in due:
            send_contract_reminder.delay(r.id)
            count += 1
        return f"Dispatched {count} reminders"


# ── Weekly Friday digest task ──────────────────────────────────────────────
@celery_app.task
def send_weekly_friday_digest():
    """
    Every Friday: review ALL active contracts expiring within 90 days.
    Send a digest email + SMS to each owner with their expiring contracts.
    """
    from app import create_app, db
    from app.models import Contract, User
    app = create_app("production")
    with app.app_context():
        cutoff = date.today() + timedelta(days=90)
        expiring = Contract.query.filter(
            Contract.status == Contract.ACTIVE,
            Contract.is_archived == False,
            Contract.end_date != None,
            Contract.end_date <= cutoff,
        ).order_by(Contract.end_date.asc()).all()

        # Group by owner
        by_owner: dict[int, list] = {}
        for c in expiring:
            by_owner.setdefault(c.owner_id, []).append(c)

        sent_count = 0
        for owner_id, contracts in by_owner.items():
            owner = User.query.get(owner_id)
            if not owner:
                continue
            # Email digest
            if owner.email_opt_in:
                try:
                    send_weekly_digest_email(app, owner, contracts)
                    sent_count += 1
                    from app import METRICS
                    METRICS["reminder_email_sent"].labels(status="sent").inc()
                except Exception:
                    pass
            # SMS digest (short summary)
            if owner.sms_opt_in and owner.phone:
                try:
                    count_urgent = sum(1 for c in contracts if c.days_until_expiry is not None and c.days_until_expiry <= 30)
                    msg = (
                        f"[CMS Weekly] Hi {owner.full_name.split()[0]}, "
                        f"you have {len(contracts)} contract(s) expiring within 90 days"
                        + (f", including {count_urgent} URGENT (≤30 days)" if count_urgent else "")
                        + ". Log in at https://cms.company.com to review."
                    )
                    _send_sms(owner.phone, msg)
                    from app import METRICS
                    METRICS["reminder_sms_sent"].labels(status="sent").inc()
                except Exception:
                    pass

        return f"Weekly digest sent to {sent_count} owners for {len(expiring)} contracts"


# ── Email functions ────────────────────────────────────────────────────────
def send_expiry_email(app, contract, user, days_before: int):
    with app.app_context():
        from flask_mail import Message
        from app import mail
        from flask import render_template
        urgency = "URGENT" if days_before <= 7 else ("ACTION REQUIRED" if days_before <= 30 else "REMINDER")
        html = _render_email_template(app, "emails/expiry_reminder.html", {
            "contract":    contract,
            "user":        user,
            "days_before": days_before,
            "urgency":     urgency,
            "login_url":   "https://cms.company.com/auth/login",
            "contract_url": f"https://cms.company.com/contracts/{contract.ref_number}",
        })
        msg = Message(
            subject    = f"[{urgency}] Contract '{contract.title}' expires in {days_before} days",
            recipients = [user.email],
            html       = html,
        )
        mail.send(msg)


def send_weekly_digest_email(app, user, contracts: list):
    with app.app_context():
        from flask_mail import Message
        from app import mail
        html = _render_email_template(app, "emails/weekly_digest.html", {
            "user":      user,
            "contracts": contracts,
            "today":     date.today(),
            "login_url": "https://cms.company.com/auth/login",
        })
        msg = Message(
            subject    = f"[CMS Weekly] {len(contracts)} contract(s) expiring soon — {date.today().strftime('%d %b %Y')}",
            recipients = [user.email],
            html       = html,
        )
        mail.send(msg)


def send_verify_email(app, user, token: str):
    with app.app_context():
        from flask_mail import Message
        from app import mail
        url  = f"https://cms.company.com/auth/verify/{token}"
        html = _render_email_template(app, "emails/verify_email.html",
                                       {"user": user, "verify_url": url})
        msg  = Message(
            subject    = "Verify your CMS account",
            recipients = [user.email], html=html,
        )
        mail.send(msg)


def send_password_reset_email(app, user, token: str):
    with app.app_context():
        from flask_mail import Message
        from app import mail
        url  = f"https://cms.company.com/auth/reset-password/{token}"
        html = _render_email_template(app, "emails/password_reset.html",
                                       {"user": user, "reset_url": url})
        msg  = Message(
            subject    = "Reset your CMS password",
            recipients = [user.email], html=html,
        )
        mail.send(msg)


# ── SMS function ───────────────────────────────────────────────────────────
def send_expiry_sms(phone: str, contract, days_before: int):
    urgency = "URGENT: " if days_before <= 7 else ""
    msg = (
        f"[CMS] {urgency}Contract '{contract.title[:40]}' "
        f"(Ref: {contract.ref_number}) expires in {days_before} day(s). "
        f"Login: https://cms.company.com"
    )
    _send_sms(phone, msg)


def _send_sms(phone: str, message: str):
    from twilio.rest import Client
    client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN"),
    )
    client.messages.create(
        to   = phone,
        from_= os.getenv("TWILIO_FROM_NUMBER", "+1234567890"),
        body = message[:1600],
    )


def _render_email_template(app, template: str, ctx: dict) -> str:
    with app.app_context():
        from flask import render_template
        try:
            return render_template(template, **ctx)
        except Exception:
            return f"<p>Contract Management System notification</p><p>{ctx}</p>"
