"""
REST API v1 — Powers PowerBI dashboards and external integrations
All endpoints require API key auth (X-API-Key header) or valid session.
"""
import os
from datetime import date, timedelta
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import func
from app import db
from app.models import Contract, User, Reminder, AIAnalysis, AuditLog

api_bp = Blueprint("api", __name__)


def _require_api_key():
    key = request.headers.get("X-API-Key") or request.args.get("api_key")
    if key and key == os.getenv("CMS_API_KEY", ""):
        return None
    from flask import session
    if "user_id" in session:
        return None
    return jsonify({"error": "Unauthorized"}), 401


# ── Summary stats (PowerBI main dataset) ──────────────────────────────────
@api_bp.route("/summary", methods=["GET"])
def summary():
    err = _require_api_key()
    if err: return err

    today   = date.today()
    d30     = today + timedelta(days=30)
    d60     = today + timedelta(days=60)
    d90     = today + timedelta(days=90)

    total        = Contract.query.filter_by(is_archived=False).count()
    active       = Contract.query.filter_by(status="ACTIVE", is_archived=False).count()
    expired      = Contract.query.filter_by(status="EXPIRED").count()
    expiring_7   = Contract.query.filter(
        Contract.status == "ACTIVE", Contract.end_date <= today + timedelta(7),
        Contract.end_date >= today).count()
    expiring_30  = Contract.query.filter(
        Contract.status == "ACTIVE", Contract.end_date <= d30,
        Contract.end_date >= today).count()
    expiring_60  = Contract.query.filter(
        Contract.status == "ACTIVE", Contract.end_date <= d60,
        Contract.end_date >= today).count()
    expiring_90  = Contract.query.filter(
        Contract.status == "ACTIVE", Contract.end_date <= d90,
        Contract.end_date >= today).count()

    total_value = db.session.query(
        func.sum(Contract.contract_value)
    ).filter_by(status="ACTIVE", is_archived=False).scalar() or 0

    by_type = db.session.query(
        Contract.contract_type, func.count(Contract.id)
    ).filter_by(is_archived=False).group_by(Contract.contract_type).all()

    by_status = db.session.query(
        Contract.status, func.count(Contract.id)
    ).filter_by(is_archived=False).group_by(Contract.status).all()

    # Risk distribution
    risk_dist = db.session.query(
        AIAnalysis.risk_level, func.count(AIAnalysis.id)
    ).group_by(AIAnalysis.risk_level).all()

    return jsonify({
        "total_contracts":  total,
        "active":           active,
        "expired":          expired,
        "expiring_7d":      expiring_7,
        "expiring_30d":     expiring_30,
        "expiring_60d":     expiring_60,
        "expiring_90d":     expiring_90,
        "total_value_usd":  float(total_value),
        "by_type":    {t: c for t, c in by_type},
        "by_status":  {s: c for s, c in by_status},
        "risk_distribution": {r: c for r, c in risk_dist},
        "as_of": today.isoformat(),
    })


# ── Contracts list (PowerBI table) ─────────────────────────────────────────
@api_bp.route("/contracts", methods=["GET"])
def contracts_list():
    err = _require_api_key()
    if err: return err

    page     = int(request.args.get("page",  1))
    per_page = int(request.args.get("limit", 100))
    status   = request.args.get("status")
    ctype    = request.args.get("type")

    q = Contract.query.filter_by(is_archived=False)
    if status: q = q.filter_by(status=status)
    if ctype:  q = q.filter_by(contract_type=ctype)

    paginated = q.order_by(Contract.end_date.asc()).paginate(
        page=page, per_page=per_page, error_out=False)

    contracts = []
    for c in paginated.items:
        ai = c.ai_analysis
        contracts.append({
            "ref":              c.ref_number,
            "title":            c.title,
            "type":             c.contract_type,
            "status":           c.status,
            "counterparty":     c.counterparty_name,
            "start_date":       c.start_date.isoformat() if c.start_date else None,
            "end_date":         c.end_date.isoformat()   if c.end_date   else None,
            "days_until_expiry":c.days_until_expiry,
            "value":            float(c.contract_value) if c.contract_value else None,
            "currency":         c.currency,
            "auto_renew":       c.auto_renew,
            "risk_level":       ai.risk_level if ai else None,
            "risk_score":       ai.risk_score if ai else None,
            "owner_email":      c.owner.email if c.owner else None,
            "department":       c.owner.department if c.owner else None,
            "created_at":       c.created_at.isoformat(),
        })

    return jsonify({
        "contracts": contracts,
        "total":     paginated.total,
        "page":      page,
        "pages":     paginated.pages,
    })


# ── Expiring contracts (PowerBI alert feed) ────────────────────────────────
@api_bp.route("/contracts/expiring", methods=["GET"])
def expiring():
    err = _require_api_key()
    if err: return err
    days = int(request.args.get("days", 30))
    cutoff = date.today() + timedelta(days=days)
    results = Contract.query.filter(
        Contract.status == "ACTIVE",
        Contract.is_archived == False,
        Contract.end_date != None,
        Contract.end_date <= cutoff,
        Contract.end_date >= date.today(),
    ).order_by(Contract.end_date.asc()).all()

    return jsonify([{
        "ref":          c.ref_number,
        "title":        c.title,
        "end_date":     c.end_date.isoformat(),
        "days_left":    c.days_until_expiry,
        "counterparty": c.counterparty_name,
        "owner_email":  c.owner.email if c.owner else None,
        "risk_level":   c.ai_analysis.risk_level if c.ai_analysis else None,
        "value":        float(c.contract_value) if c.contract_value else None,
    } for c in results])


# ── Reminders log (PowerBI notifications dataset) ─────────────────────────
@api_bp.route("/reminders", methods=["GET"])
def reminders():
    err = _require_api_key()
    if err: return err
    page = int(request.args.get("page", 1))
    q    = Reminder.query.order_by(Reminder.sent_at.desc()).paginate(
        page=page, per_page=200, error_out=False)
    return jsonify([{
        "id":            r.id,
        "contract_ref":  r.contract.ref_number if r.contract else None,
        "type":          r.reminder_type,
        "days_before":   r.days_before,
        "status":        r.status,
        "sent_at":       r.sent_at.isoformat() if r.sent_at else None,
        "is_weekly":     r.is_weekly,
    } for r in q.items])


# ── Audit log (PowerBI compliance dataset) ────────────────────────────────
@api_bp.route("/audit", methods=["GET"])
def audit():
    err = _require_api_key()
    if err: return err
    page = int(request.args.get("page", 1))
    q    = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(
        page=page, per_page=200, error_out=False)
    return jsonify([{
        "action":    l.action,
        "resource":  l.resource,
        "detail":    l.detail,
        "ip":        l.ip_address,
        "timestamp": l.timestamp.isoformat(),
        "user_email":l.user.email if l.user else None,
    } for l in q.items])


# ── Health check ───────────────────────────────────────────────────────────
@api_bp.route("/health", methods=["GET"])
def health():
    checks = {}
    try:
        db.session.execute(db.text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
    try:
        import openai
        checks["openai_sdk"] = "available"
    except ImportError:
        checks["openai_sdk"] = "not installed"
    try:
        from twilio.rest import Client
        checks["twilio_sdk"] = "available"
    except ImportError:
        checks["twilio_sdk"] = "not installed"
    overall = "ok" if checks["database"] == "ok" else "degraded"
    return jsonify({"status": overall, "checks": checks,
                    "timestamp": date.today().isoformat()}), \
           200 if overall == "ok" else 503
