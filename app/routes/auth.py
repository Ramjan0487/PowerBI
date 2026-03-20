"""
Auth Blueprint — signup, login (password + mTLS), forgot/reset password, verify email
"""
import re
import secrets
from datetime import datetime, timedelta
from flask import (Blueprint, request, session, jsonify,
                   render_template, redirect, url_for, current_app)
from app import db, bcrypt, limiter, METRICS
from app.models import User, AuditLog

auth_bp = Blueprint("auth", __name__)
EMAIL_RE = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
PHONE_RE = re.compile(r"^\+?[\d\s\-\(\)]{7,20}$")


def _audit(action, detail="", user_id=None, resource=None):
    db.session.add(AuditLog(
        user_id=user_id, action=action, detail=detail, resource=resource,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent", "")[:256],
    ))
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def _verify_mtls():
    if not current_app.config.get("VERIFY_CLIENT_CERT"):
        return True, None
    verify = request.headers.get("X-SSL-Client-Verify", "NONE")
    if verify != "SUCCESS":
        return False, "Client certificate not verified"
    return True, request.headers.get("X-SSL-Client-DN", "")


# ── Signup ─────────────────────────────────────────────────────────────────
@auth_bp.route("/signup", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def signup():
    if request.method == "GET":
        return render_template("auth/signup.html")

    d = request.get_json(silent=True) or request.form
    full_name = (d.get("full_name") or "").strip()
    email     = (d.get("email")     or "").strip().lower()
    phone     = (d.get("phone")     or "").strip()
    password  = (d.get("password")  or "")
    dept      = (d.get("department")or "").strip()

    errors = []
    if len(full_name) < 2:   errors.append("Full name is required.")
    if not EMAIL_RE.match(email): errors.append("Valid email is required.")
    if phone and not PHONE_RE.match(phone): errors.append("Invalid phone number.")
    if len(password) < 8:    errors.append("Password must be at least 8 characters.")
    if User.query.filter_by(email=email).first(): errors.append("Email already registered.")

    if errors:
        return _err(400, errors[0])

    token = secrets.token_urlsafe(32)
    user  = User(
        full_name=full_name, email=email, phone=phone, department=dept,
        password_hash=bcrypt.generate_password_hash(password).decode(),
        verify_token=token, sms_opt_in=bool(phone),
    )
    db.session.add(user)
    db.session.commit()
    _audit("SIGNUP", f"New user {email}", user.id)
    METRICS["login_total"].labels(status="signup").inc()

    # Send verification email (non-blocking)
    try:
        from app.services.notifications.email_service import send_verify_email
        send_verify_email(current_app._get_current_object(), user, token)
    except Exception:
        pass

    return jsonify({"status": "ok",
                    "message": "Account created. Check your email to verify.",
                    "redirect": url_for("auth.login")})


# ── Login ─────────────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("15 per minute")
def login():
    if request.method == "GET":
        return render_template("auth/login.html")

    d        = request.get_json(silent=True) or request.form
    email    = (d.get("email")    or "").strip().lower()
    password = (d.get("password") or "")

    if not EMAIL_RE.match(email):
        return _err(400, "Valid email address is required.")
    if len(password) < 1:
        return _err(400, "Password is required.")

    user = User.query.filter_by(email=email).first()
    if not user:
        METRICS["login_total"].labels(status="not_found").inc()
        _audit("LOGIN_FAIL", f"Email {email} not found")
        return _err(401, "Incorrect email or password.")

    if user.locked_until and user.locked_until > datetime.utcnow():
        mins = int((user.locked_until - datetime.utcnow()).total_seconds() // 60)
        return _err(423, f"Account locked for {mins} more minutes.")

    if not bcrypt.check_password_hash(user.password_hash, password):
        user.failed_logins += 1
        if user.failed_logins >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=30)
            _audit("ACCOUNT_LOCKED", f"Locked after 5 failures", user.id)
        db.session.commit()
        METRICS["login_total"].labels(status="wrong_password").inc()
        return _err(401, "Incorrect email or password.")

    # mTLS check
    cert_ok, cert_dn = _verify_mtls()
    if not cert_ok:
        METRICS["login_total"].labels(status="cert_fail").inc()
        return _err(401, f"Certificate error: {cert_dn}")

    # Success
    user.failed_logins = 0
    user.locked_until  = None
    user.last_login    = datetime.utcnow()
    if cert_dn and not user.cert_subject:
        user.cert_subject = cert_dn
    db.session.commit()

    session.permanent = True
    session["user_id"]   = user.id
    session["user_email"]= user.email
    session["user_role"] = user.role
    session["csrf"]      = secrets.token_hex(32)

    METRICS["login_total"].labels(status="success").inc()
    _audit("LOGIN_SUCCESS", f"User {email}", user.id)

    return jsonify({"status": "ok", "redirect": url_for("dashboard.index"),
                    "csrf": session["csrf"]})


# ── Forgot password ────────────────────────────────────────────────────────
@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def forgot_password():
    if request.method == "GET":
        return render_template("auth/forgot_password.html")

    d     = request.get_json(silent=True) or request.form
    email = (d.get("email") or "").strip().lower()

    user = User.query.filter_by(email=email).first()
    if user:
        token = secrets.token_urlsafe(48)
        user.reset_token   = token
        user.reset_expires = datetime.utcnow() + timedelta(hours=2)
        db.session.commit()
        try:
            from app.services.notifications.email_service import send_password_reset_email
            send_password_reset_email(current_app._get_current_object(), user, token)
        except Exception:
            pass
        _audit("PASSWORD_RESET_REQUEST", f"Reset requested for {email}", user.id)

    # Always return OK to prevent email enumeration
    return jsonify({"status": "ok",
                    "message": "If that email exists, a reset link has been sent."})


# ── Reset password ─────────────────────────────────────────────────────────
@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user or (user.reset_expires and user.reset_expires < datetime.utcnow()):
        return render_template("auth/reset_password.html", error="Link expired or invalid.")

    if request.method == "GET":
        return render_template("auth/reset_password.html", token=token)

    d = request.get_json(silent=True) or request.form
    new_pw = d.get("password", "")
    if len(new_pw) < 8:
        return _err(400, "Password must be at least 8 characters.")

    user.password_hash = bcrypt.generate_password_hash(new_pw).decode()
    user.reset_token   = None
    user.reset_expires = None
    user.failed_logins = 0
    user.locked_until  = None
    db.session.commit()
    _audit("PASSWORD_RESET", "Password successfully reset", user.id)

    return jsonify({"status": "ok", "message": "Password reset. Please log in.",
                    "redirect": url_for("auth.login")})


# ── Verify email ───────────────────────────────────────────────────────────
@auth_bp.route("/verify/<token>")
def verify_email(token):
    user = User.query.filter_by(verify_token=token).first_or_404()
    user.email_verified = True
    user.verify_token   = None
    db.session.commit()
    _audit("EMAIL_VERIFIED", "", user.id)
    return redirect(url_for("auth.login") + "?verified=1")


# ── Logout ─────────────────────────────────────────────────────────────────
@auth_bp.route("/logout", methods=["POST"])
def logout():
    uid = session.get("user_id")
    session.clear()
    _audit("LOGOUT", "", uid)
    return redirect(url_for("auth.login"))


# ── mTLS cert status ───────────────────────────────────────────────────────
@auth_bp.route("/cert-status")
def cert_status():
    verify = request.headers.get("X-SSL-Client-Verify", "NONE")
    dn     = request.headers.get("X-SSL-Client-DN", "")
    return jsonify({"verified": verify == "SUCCESS", "subject": dn})


def _err(code, msg):
    if request.is_json or request.headers.get("Accept","").startswith("application/json"):
        return jsonify({"status": "error", "message": msg}), code
    return render_template("auth/login.html", error=msg), code
