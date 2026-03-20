"""
Contract Management System — Application Factory
Features: mTLS login · AI contract analysis · SMS+Email reminders
PowerBI dashboards · Katalon testing · Digital certificates
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_bcrypt import Bcrypt
from prometheus_client import Counter, Histogram, Gauge, make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

db      = SQLAlchemy()
mail    = Mail()
bcrypt  = Bcrypt()
limiter = Limiter(key_func=get_remote_address)

METRICS = {
    "login_total":         Counter("cms_login_total",         "Login attempts",          ["status"]),
    "contract_created":    Counter("cms_contracts_created",   "Contracts created"),
    "reminder_sms_sent":   Counter("cms_sms_sent_total",      "SMS reminders sent",      ["status"]),
    "reminder_email_sent": Counter("cms_email_sent_total",    "Email reminders sent",    ["status"]),
    "ai_analysis_time":    Histogram("cms_ai_analysis_seconds","AI analysis latency"),
    "active_contracts":    Gauge("cms_active_contracts",      "Active contracts"),
    "expiring_soon":       Gauge("cms_expiring_soon",         "Contracts expiring ≤30d"),
}


def create_app(config_name: str = "production") -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    cfgs = {
        "development": "app.config.DevelopmentConfig",
        "production":  "app.config.ProductionConfig",
        "testing":     "app.config.TestingConfig",
    }
    app.config.from_object(cfgs.get(config_name, cfgs["production"]))

    db.init_app(app)
    mail.init_app(app)
    bcrypt.init_app(app)
    limiter.init_app(app)

    from app.routes.auth      import auth_bp
    from app.routes.contracts import contracts_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.api       import api_bp
    from app.routes.certs     import certs_bp

    app.register_blueprint(auth_bp,      url_prefix="/auth")
    app.register_blueprint(contracts_bp, url_prefix="/contracts")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(api_bp,       url_prefix="/api/v1")
    app.register_blueprint(certs_bp,     url_prefix="/certs")

    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {"/metrics": make_wsgi_app()})

    with app.app_context():
        db.create_all()

    return app
