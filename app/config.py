"""Configuration — Development / Production / Testing"""
import os
from datetime import timedelta


class BaseConfig:
    SECRET_KEY                     = os.getenv("SECRET_KEY", "change-me-in-production-cms")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_SECURE          = True
    SESSION_COOKIE_HTTPONLY        = True
    SESSION_COOKIE_SAMESITE        = "Lax"
    PERMANENT_SESSION_LIFETIME     = timedelta(hours=8)

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///contracts.db")

    # Mail
    MAIL_SERVER        = os.getenv("MAIL_SERVER",   "smtp.office365.com")
    MAIL_PORT          = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS       = True
    MAIL_USERNAME      = os.getenv("MAIL_USERNAME", "contracts@company.com")
    MAIL_PASSWORD      = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = ("Contract Management System", "contracts@company.com")

    # SMS — Twilio
    TWILIO_ACCOUNT_SID  = os.getenv("TWILIO_ACCOUNT_SID",  "")
    TWILIO_AUTH_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN",   "")
    TWILIO_FROM_NUMBER  = os.getenv("TWILIO_FROM_NUMBER",  "+1234567890")

    # Redis / Celery
    REDIS_URL      = os.getenv("REDIS_URL", "redis://redis:6379/0")
    CELERY_BROKER  = os.getenv("REDIS_URL", "redis://redis:6379/0")
    CELERY_BACKEND = os.getenv("REDIS_URL", "redis://redis:6379/0")

    # PKI / mTLS
    MTLS_CA_CERT         = os.getenv("MTLS_CA_CERT",    "certs/ca/ca.crt")
    MTLS_SERVER_CERT     = os.getenv("MTLS_SERVER_CERT","certs/server/server.crt")
    MTLS_SERVER_KEY      = os.getenv("MTLS_SERVER_KEY", "certs/server/server.key")
    VERIFY_CLIENT_CERT   = os.getenv("VERIFY_CLIENT_CERT","true").lower() == "true"

    # AI contract analysis
    AI_MODEL_PATH        = os.getenv("AI_MODEL_PATH", "app/services/ai/models/contract_classifier.pkl")
    OPENAI_API_KEY       = os.getenv("OPENAI_API_KEY", "")

    # PowerBI
    POWERBI_CLIENT_ID    = os.getenv("POWERBI_CLIENT_ID",    "")
    POWERBI_CLIENT_SECRET= os.getenv("POWERBI_CLIENT_SECRET","")
    POWERBI_TENANT_ID    = os.getenv("POWERBI_TENANT_ID",    "")
    POWERBI_WORKSPACE_ID = os.getenv("POWERBI_WORKSPACE_ID", "")

    # File uploads
    MAX_CONTENT_LENGTH   = 50 * 1024 * 1024   # 50 MB
    UPLOAD_FOLDER        = os.getenv("UPLOAD_FOLDER", "uploads")
    ALLOWED_EXTENSIONS   = {"pdf", "docx", "doc", "txt", "png", "jpg"}

    # Reminder schedule
    REMINDER_DAYS_BEFORE = [90, 60, 30, 14, 7, 1]   # days before expiry
    WEEKLY_REMINDER_DAY  = 4   # Friday (0=Monday)
    WEEKLY_REMINDER_HOUR = 8   # 08:00 AM


class DevelopmentConfig(BaseConfig):
    DEBUG                = True
    SESSION_COOKIE_SECURE= False
    VERIFY_CLIENT_CERT   = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///contracts_dev.db"


class ProductionConfig(BaseConfig):
    DEBUG = False


class TestingConfig(BaseConfig):
    TESTING              = True
    DEBUG                = True
    SESSION_COOKIE_SECURE= False
    VERIFY_CLIENT_CERT   = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    MAIL_SUPPRESS_SEND   = True
    WTF_CSRF_ENABLED     = False
