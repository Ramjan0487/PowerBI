"""
Database models — User, Contract, Reminder, AIAnalysis, AuditLog, DigitalCertificate
"""
from datetime import datetime, date
from app import db


class User(db.Model):
    __tablename__ = "users"
    id              = db.Column(db.Integer, primary_key=True)
    full_name       = db.Column(db.String(120), nullable=False)
    email           = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone           = db.Column(db.String(20))
    password_hash   = db.Column(db.String(256), nullable=False)
    role            = db.Column(db.String(20), default="user")   # admin, manager, user
    department      = db.Column(db.String(80))
    is_active       = db.Column(db.Boolean, default=True)
    email_verified  = db.Column(db.Boolean, default=False)
    verify_token    = db.Column(db.String(128))
    reset_token     = db.Column(db.String(128))
    reset_expires   = db.Column(db.DateTime)
    failed_logins   = db.Column(db.Integer, default=0)
    locked_until    = db.Column(db.DateTime)
    cert_subject    = db.Column(db.String(256))   # mTLS DN
    cert_serial     = db.Column(db.String(64))
    sms_opt_in      = db.Column(db.Boolean, default=True)
    email_opt_in    = db.Column(db.Boolean, default=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    last_login      = db.Column(db.DateTime)

    contracts       = db.relationship("Contract", back_populates="owner", lazy="dynamic",
                                       foreign_keys="Contract.owner_id")
    audits          = db.relationship("AuditLog", back_populates="user", lazy="dynamic")

    def __repr__(self):
        return f"<User {self.email}>"


class Contract(db.Model):
    __tablename__ = "contracts"
    id               = db.Column(db.Integer, primary_key=True)
    ref_number       = db.Column(db.String(32), unique=True, nullable=False, index=True)
    title            = db.Column(db.String(200), nullable=False)
    description      = db.Column(db.Text)
    contract_type    = db.Column(db.String(50))   # SERVICE, VENDOR, EMPLOYMENT, NDA, LEASE, etc.
    status           = db.Column(db.String(30), default="DRAFT")
    # Parties
    counterparty_name  = db.Column(db.String(150))
    counterparty_email = db.Column(db.String(120))
    counterparty_phone = db.Column(db.String(20))
    # Dates
    start_date       = db.Column(db.Date)
    end_date         = db.Column(db.Date, index=True)
    signed_date      = db.Column(db.Date)
    # Value
    contract_value   = db.Column(db.Numeric(15, 2))
    currency         = db.Column(db.String(3), default="USD")
    # File
    file_path        = db.Column(db.String(512))
    file_hash        = db.Column(db.String(64))   # SHA-256 for integrity
    # Relations
    owner_id         = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    manager_id       = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Flags
    auto_renew       = db.Column(db.Boolean, default=False)
    is_archived      = db.Column(db.Boolean, default=False)
    digital_cert_id  = db.Column(db.Integer, db.ForeignKey("digital_certificates.id"))
    # Timestamps
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at       = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner            = db.relationship("User", back_populates="contracts", foreign_keys=[owner_id])
    manager          = db.relationship("User", foreign_keys=[manager_id])
    reminders        = db.relationship("Reminder", back_populates="contract", lazy="dynamic",
                                        cascade="all, delete-orphan")
    ai_analysis      = db.relationship("AIAnalysis", back_populates="contract", uselist=False,
                                        cascade="all, delete-orphan")
    certificate      = db.relationship("DigitalCertificate", foreign_keys=[digital_cert_id])

    # Status constants
    DRAFT     = "DRAFT"
    ACTIVE    = "ACTIVE"
    EXPIRED   = "EXPIRED"
    CANCELLED = "CANCELLED"
    RENEWED   = "RENEWED"
    PENDING   = "PENDING_SIGNATURE"

    @property
    def days_until_expiry(self):
        if self.end_date:
            return (self.end_date - date.today()).days
        return None

    @property
    def is_expiring_soon(self):
        d = self.days_until_expiry
        return d is not None and 0 <= d <= 30

    def __repr__(self):
        return f"<Contract {self.ref_number} — {self.title[:40]}>"


class Reminder(db.Model):
    __tablename__ = "reminders"
    id            = db.Column(db.Integer, primary_key=True)
    contract_id   = db.Column(db.Integer, db.ForeignKey("contracts.id"), nullable=False)
    reminder_type = db.Column(db.String(10))   # EMAIL, SMS, BOTH
    days_before   = db.Column(db.Integer)       # 90, 60, 30, 14, 7, 1
    scheduled_at  = db.Column(db.DateTime)
    sent_at       = db.Column(db.DateTime)
    status        = db.Column(db.String(20), default="PENDING")   # PENDING, SENT, FAILED
    recipient_email = db.Column(db.String(120))
    recipient_phone = db.Column(db.String(20))
    error_message = db.Column(db.Text)
    is_weekly     = db.Column(db.Boolean, default=False)   # Friday weekly digest

    contract      = db.relationship("Contract", back_populates="reminders")

    def __repr__(self):
        return f"<Reminder {self.reminder_type} contract={self.contract_id} days={self.days_before}>"


class AIAnalysis(db.Model):
    __tablename__ = "ai_analyses"
    id               = db.Column(db.Integer, primary_key=True)
    contract_id      = db.Column(db.Integer, db.ForeignKey("contracts.id"), nullable=False, unique=True)
    risk_score       = db.Column(db.Float)        # 0.0 – 1.0
    risk_level       = db.Column(db.String(10))   # LOW, MEDIUM, HIGH, CRITICAL
    contract_type    = db.Column(db.String(50))
    key_clauses      = db.Column(db.Text)         # JSON array of detected clauses
    missing_clauses  = db.Column(db.Text)         # JSON array
    anomalies        = db.Column(db.Text)         # JSON array
    summary          = db.Column(db.Text)
    recommendations  = db.Column(db.Text)         # JSON array
    confidence       = db.Column(db.Float)
    model_version    = db.Column(db.String(20))
    analyzed_at      = db.Column(db.DateTime, default=datetime.utcnow)
    duration_ms      = db.Column(db.Float)

    contract         = db.relationship("Contract", back_populates="ai_analysis")

    def __repr__(self):
        return f"<AIAnalysis contract={self.contract_id} risk={self.risk_level}>"


class DigitalCertificate(db.Model):
    __tablename__ = "digital_certificates"
    id            = db.Column(db.Integer, primary_key=True)
    serial_number = db.Column(db.String(64), unique=True, nullable=False)
    subject_dn    = db.Column(db.String(256))
    issuer_dn     = db.Column(db.String(256))
    valid_from    = db.Column(db.DateTime)
    valid_until   = db.Column(db.DateTime)
    cert_pem      = db.Column(db.Text)     # PEM encoded cert
    fingerprint   = db.Column(db.String(64))
    purpose       = db.Column(db.String(30))   # SIGNING, ENCRYPTION, AUTH
    issued_to     = db.Column(db.Integer, db.ForeignKey("users.id"))
    revoked       = db.Column(db.Boolean, default=False)
    revoked_at    = db.Column(db.DateTime)
    revoke_reason = db.Column(db.String(100))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Cert serial={self.serial_number} subject={self.subject_dn}>"


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"))
    action      = db.Column(db.String(64), nullable=False, index=True)
    resource    = db.Column(db.String(64))
    resource_id = db.Column(db.Integer)
    detail      = db.Column(db.Text)
    ip_address  = db.Column(db.String(45))
    user_agent  = db.Column(db.String(256))
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user        = db.relationship("User", back_populates="audits")

    def __repr__(self):
        return f"<Audit {self.action} at {self.timestamp}>"
