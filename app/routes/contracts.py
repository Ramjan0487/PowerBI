"""
Contracts Blueprint — CRUD, file upload, AI analysis, status management
"""
import os
import uuid
import hashlib
from datetime import date
from flask import (Blueprint, request, session, jsonify,
                   render_template, redirect, url_for, current_app, send_file)
from werkzeug.utils import secure_filename
from app import db, limiter, METRICS
from app.models import Contract, Reminder, AIAnalysis, AuditLog, User

contracts_bp = Blueprint("contracts", __name__)


def _login_required():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    return None


def _audit(action, detail="", resource_id=None):
    db.session.add(AuditLog(
        user_id=session.get("user_id"), action=action, detail=detail,
        resource="contract", resource_id=resource_id,
        ip_address=request.remote_addr,
    ))
    try: db.session.commit()
    except Exception: db.session.rollback()


def _allowed_file(fname):
    return "." in fname and \
           fname.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]


# ── List contracts ─────────────────────────────────────────────────────────
@contracts_bp.route("/", methods=["GET"])
def index():
    err = _login_required()
    if err: return err
    user = User.query.get(session["user_id"])
    q    = Contract.query.filter_by(is_archived=False)
    if user.role not in ("admin", "manager"):
        q = q.filter_by(owner_id=user.id)
    contracts = q.order_by(Contract.end_date.asc()).all()
    return render_template("contracts/list.html", contracts=contracts, user=user)


# ── Create contract ────────────────────────────────────────────────────────
@contracts_bp.route("/new", methods=["GET", "POST"])
def new_contract():
    err = _login_required()
    if err: return err

    if request.method == "GET":
        return render_template("contracts/form.html",
                                action="create", contract=None,
                                user=User.query.get(session["user_id"]))

    d = request.form
    # Validate required fields
    required = ["title", "contract_type", "end_date", "counterparty_name"]
    for f in required:
        if not d.get(f):
            return _err(400, f"Field '{f}' is required.")

    ref = f"CTR-{date.today().year}-{uuid.uuid4().hex[:6].upper()}"
    contract = Contract(
        ref_number         = ref,
        title              = d["title"].strip(),
        description        = d.get("description", "").strip(),
        contract_type      = d["contract_type"],
        counterparty_name  = d["counterparty_name"].strip(),
        counterparty_email = d.get("counterparty_email", "").strip(),
        counterparty_phone = d.get("counterparty_phone", "").strip(),
        start_date         = _parse_date(d.get("start_date")),
        end_date           = _parse_date(d["end_date"]),
        signed_date        = _parse_date(d.get("signed_date")),
        contract_value     = d.get("contract_value") or None,
        currency           = d.get("currency", "USD"),
        auto_renew         = d.get("auto_renew") == "true",
        status             = Contract.ACTIVE if d.get("signed_date") else Contract.DRAFT,
        owner_id           = session["user_id"],
    )

    # Handle file upload
    if "contract_file" in request.files:
        f = request.files["contract_file"]
        if f and f.filename and _allowed_file(f.filename):
            fname    = secure_filename(f"{ref}_{f.filename}")
            folder   = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(folder, exist_ok=True)
            fpath    = os.path.join(folder, fname)
            f.save(fpath)
            contract.file_path = fpath
            contract.file_hash = _sha256(fpath)

    db.session.add(contract)
    db.session.commit()

    # Schedule reminders
    _schedule_reminders(contract)

    # Trigger AI analysis async
    try:
        from app.services.ai.contract_analyzer import analyze_contract_async
        analyze_contract_async(current_app._get_current_object(), contract.id)
    except Exception:
        pass

    METRICS["contract_created"].inc()
    _audit("CONTRACT_CREATED", f"Ref {ref} — {contract.title}", contract.id)

    return jsonify({"status": "ok", "ref": ref,
                    "redirect": url_for("contracts.view_contract", ref=ref)})


# ── View contract ──────────────────────────────────────────────────────────
@contracts_bp.route("/<ref>", methods=["GET"])
def view_contract(ref):
    err = _login_required()
    if err: return err
    contract = Contract.query.filter_by(ref_number=ref).first_or_404()
    user     = User.query.get(session["user_id"])
    return render_template("contracts/detail.html", contract=contract, user=user)


# ── Edit contract ──────────────────────────────────────────────────────────
@contracts_bp.route("/<ref>/edit", methods=["GET", "POST"])
def edit_contract(ref):
    err = _login_required()
    if err: return err
    contract = Contract.query.filter_by(ref_number=ref).first_or_404()

    if request.method == "GET":
        return render_template("contracts/form.html", action="edit",
                                contract=contract,
                                user=User.query.get(session["user_id"]))

    d = request.form
    contract.title             = d.get("title", contract.title).strip()
    contract.description       = d.get("description", contract.description or "").strip()
    contract.contract_type     = d.get("contract_type", contract.contract_type)
    contract.counterparty_name = d.get("counterparty_name", contract.counterparty_name)
    contract.counterparty_email= d.get("counterparty_email", contract.counterparty_email)
    contract.counterparty_phone= d.get("counterparty_phone", contract.counterparty_phone)
    contract.end_date          = _parse_date(d.get("end_date")) or contract.end_date
    contract.contract_value    = d.get("contract_value") or contract.contract_value
    contract.auto_renew        = d.get("auto_renew") == "true"
    db.session.commit()
    _audit("CONTRACT_UPDATED", f"Ref {ref}", contract.id)
    return jsonify({"status": "ok", "redirect": url_for("contracts.view_contract", ref=ref)})


# ── Delete / archive ───────────────────────────────────────────────────────
@contracts_bp.route("/<ref>/archive", methods=["POST"])
def archive_contract(ref):
    err = _login_required()
    if err: return jsonify({"status": "error", "message": "Auth required"}), 401
    contract = Contract.query.filter_by(ref_number=ref).first_or_404()
    contract.is_archived = True
    contract.status      = Contract.CANCELLED
    db.session.commit()
    _audit("CONTRACT_ARCHIVED", f"Ref {ref}", contract.id)
    return jsonify({"status": "ok"})


# ── Download contract file ─────────────────────────────────────────────────
@contracts_bp.route("/<ref>/download")
def download(ref):
    err = _login_required()
    if err: return err
    contract = Contract.query.filter_by(ref_number=ref).first_or_404()
    if not contract.file_path or not os.path.exists(contract.file_path):
        return _err(404, "File not found.")
    _audit("CONTRACT_DOWNLOADED", f"Ref {ref}", contract.id)
    return send_file(contract.file_path, as_attachment=True)


# ── Trigger AI analysis ────────────────────────────────────────────────────
@contracts_bp.route("/<ref>/analyze", methods=["POST"])
def trigger_analysis(ref):
    err = _login_required()
    if err: return jsonify({"status":"error"}), 401
    contract = Contract.query.filter_by(ref_number=ref).first_or_404()
    try:
        from app.services.ai.contract_analyzer import run_analysis
        result = run_analysis(contract)
        return jsonify({"status": "ok", "risk_level": result.risk_level,
                        "risk_score": result.risk_score, "summary": result.summary})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ── Helpers ────────────────────────────────────────────────────────────────
def _schedule_reminders(contract):
    """Create reminder records for all configured intervals."""
    from datetime import datetime, timedelta
    if not contract.end_date:
        return
    days_list = current_app.config.get("REMINDER_DAYS_BEFORE", [90,60,30,14,7,1])
    for days in days_list:
        remind_on = datetime.combine(contract.end_date, datetime.min.time()) - timedelta(days=days)
        if remind_on > datetime.utcnow():
            reminder = Reminder(
                contract_id     = contract.id,
                reminder_type   = "BOTH",
                days_before     = days,
                scheduled_at    = remind_on,
                recipient_email = contract.counterparty_email or contract.owner.email,
                recipient_phone = contract.counterparty_phone or contract.owner.phone,
                status          = "PENDING",
            )
            db.session.add(reminder)
    db.session.commit()


def _parse_date(val):
    if not val:
        return None
    try:
        from datetime import date as d
        return d.fromisoformat(val)
    except Exception:
        return None


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _err(code, msg):
    if request.is_json:
        return jsonify({"status": "error", "message": msg}), code
    return render_template("contracts/list.html", error=msg), code
