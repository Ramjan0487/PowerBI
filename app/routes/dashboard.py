"""Dashboard Blueprint — main metrics page with PowerBI embed token"""
from datetime import date, timedelta
from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from sqlalchemy import func
from app import db
from app.models import Contract, Reminder, AIAnalysis, AuditLog, User

dashboard_bp = Blueprint("dashboard", __name__)


def _require_login():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    return None


@dashboard_bp.route("/")
def index():
    err = _require_login()
    if err: return err
    user = User.query.get(session["user_id"])
    return render_template("dashboard/index.html", user=user)


@dashboard_bp.route("/api/kpis")
def kpis():
    err = _require_login()
    if err: return jsonify({}), 401
    today  = date.today()
    d30    = today + timedelta(days=30)
    d90    = today + timedelta(days=90)
    total  = Contract.query.filter_by(is_archived=False).count()
    active = Contract.query.filter_by(status="ACTIVE", is_archived=False).count()
    exp_30 = Contract.query.filter(
        Contract.status=="ACTIVE", Contract.end_date <= d30, Contract.end_date >= today).count()
    exp_90 = Contract.query.filter(
        Contract.status=="ACTIVE", Contract.end_date <= d90, Contract.end_date >= today).count()
    total_val = db.session.query(func.sum(Contract.contract_value))\
                          .filter_by(status="ACTIVE", is_archived=False).scalar() or 0
    by_type = db.session.query(Contract.contract_type, func.count(Contract.id))\
                        .filter_by(is_archived=False).group_by(Contract.contract_type).all()
    risk_dist = db.session.query(AIAnalysis.risk_level, func.count())\
                          .group_by(AIAnalysis.risk_level).all()
    monthly = []
    for i in range(11, -1, -1):
        m = today.replace(day=1) - timedelta(days=i*30)
        cnt = Contract.query.filter(
            func.strftime("%Y-%m", Contract.created_at) == m.strftime("%Y-%m")).count()
        monthly.append({"month": m.strftime("%b %Y"), "count": cnt})
    return jsonify({
        "total": total, "active": active,
        "expiring_30d": exp_30, "expiring_90d": exp_90,
        "total_value": float(total_val),
        "by_type": {t: c for t, c in by_type},
        "risk_dist": {r: c for r, c in risk_dist},
        "monthly_trend": monthly,
        "sms_sent_today": Reminder.query.filter(
            Reminder.reminder_type.in_(["SMS","BOTH"]),
            Reminder.status=="SENT",
            func.date(Reminder.sent_at)==today).count(),
        "email_sent_today": Reminder.query.filter(
            Reminder.reminder_type.in_(["EMAIL","BOTH"]),
            Reminder.status=="SENT",
            func.date(Reminder.sent_at)==today).count(),
    })


@dashboard_bp.route("/api/powerbi-token")
def powerbi_token():
    """Generate PowerBI embed token for the frontend."""
    err = _require_login()
    if err: return jsonify({}), 401
    import os, requests
    client_id     = os.getenv("POWERBI_CLIENT_ID")
    client_secret = os.getenv("POWERBI_CLIENT_SECRET")
    tenant_id     = os.getenv("POWERBI_TENANT_ID")
    workspace_id  = os.getenv("POWERBI_WORKSPACE_ID")
    report_id     = request.args.get("report_id", os.getenv("POWERBI_REPORT_ID", ""))

    if not all([client_id, client_secret, tenant_id]):
        return jsonify({"error": "PowerBI not configured", "demo": True,
                        "embed_url": "#", "token": "demo"})
    try:
        # Get AAD token
        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        r = requests.post(token_url, data={
            "grant_type": "client_credentials",
            "client_id": client_id, "client_secret": client_secret,
            "scope": "https://analysis.windows.net/powerbi/api/.default",
        }, timeout=10)
        aad_token = r.json().get("access_token", "")
        # Get embed token
        embed_url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports/{report_id}/GenerateToken"
        er = requests.post(embed_url,
            headers={"Authorization": f"Bearer {aad_token}"},
            json={"accessLevel": "View"}, timeout=10)
        embed_data = er.json()
        return jsonify({
            "token":     embed_data.get("token"),
            "embed_url": embed_data.get("embedUrl"),
            "report_id": report_id,
        })
    except Exception as e:
        return jsonify({"error": str(e), "demo": True}), 500


@dashboard_bp.route("/api/activity")
def activity():
    err = _require_login()
    if err: return jsonify([]), 401
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(50).all()
    return jsonify([{
        "action": l.action, "detail": l.detail,
        "user":   l.user.email if l.user else "—",
        "ip":     l.ip_address,
        "time":   l.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
    } for l in logs])
