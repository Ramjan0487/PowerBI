"""Certificates Blueprint — issue, verify, revoke digital certificates"""
from flask import Blueprint, request, jsonify, session, render_template
from app import db
from app.models import Contract, DigitalCertificate, AuditLog, User
from app.services.certificates.cert_service import issue_contract_certificate, verify_certificate

certs_bp = Blueprint("certs", __name__)


@certs_bp.route("/issue/<ref>", methods=["POST"])
def issue(ref):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    contract = Contract.query.filter_by(ref_number=ref).first_or_404()
    user     = User.query.get(session["user_id"])
    result   = issue_contract_certificate(contract, user)
    cert = DigitalCertificate(
        serial_number = result["serial_number"],
        subject_dn    = result["subject_dn"],
        issuer_dn     = result["issuer_dn"],
        valid_from    = result["valid_from"],
        valid_until   = result["valid_until"],
        cert_pem      = result["cert_pem"],
        fingerprint   = result["fingerprint"],
        purpose       = "SIGNING",
        issued_to     = user.id,
    )
    db.session.add(cert)
    db.session.flush()
    contract.digital_cert_id = cert.id
    db.session.add(AuditLog(
        user_id=user.id, action="CERT_ISSUED",
        detail=f"Cert {result['serial_number']} issued for contract {ref}",
        resource="contract", resource_id=contract.id,
        ip_address=request.remote_addr,
    ))
    db.session.commit()
    return jsonify({"status": "ok", "serial": result["serial_number"],
                    "fingerprint": result["fingerprint"],
                    "valid_until": result["valid_until"].isoformat()})


@certs_bp.route("/verify", methods=["POST"])
def verify():
    data     = request.get_json(silent=True) or {}
    cert_pem = data.get("cert_pem", "")
    if not cert_pem:
        return jsonify({"error": "cert_pem required"}), 400
    result = verify_certificate(cert_pem)
    return jsonify(result)


@certs_bp.route("/revoke/<serial>", methods=["POST"])
def revoke(serial):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    cert = DigitalCertificate.query.filter_by(serial_number=serial).first_or_404()
    from datetime import datetime
    cert.revoked      = True
    cert.revoked_at   = datetime.utcnow()
    cert.revoke_reason= (request.get_json(silent=True) or {}).get("reason", "Unspecified")
    db.session.commit()
    return jsonify({"status": "revoked", "serial": serial})
