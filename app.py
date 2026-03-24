"""
Contract Management System - Flask + Python + Power BI Dashboard
Main Application Entry Point
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
try:
    from flask_mail import Mail, Message
except ImportError:
    class Mail:
        def __init__(self, app=None): pass
    class Message:
        def __init__(self, **kw): pass
import json, os, random
from datetime import datetime, timedelta
from utils.sms_service import SMSService
from utils.data_generator import generate_contracts, generate_transactions, generate_alerts
from utils.reminder_engine import ReminderEngine

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "cms-rwanda-2026-secret")

# ── Mail Configuration ─────────────────────────────────────────
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'cms@example.com')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'password')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'CMS System <cms@example.com>')

mail = Mail(app)
sms = SMSService()
reminder_engine = ReminderEngine(mail, sms)

# ── Seed demo data ─────────────────────────────────────────────
CONTRACTS     = generate_contracts(50)
TRANSACTIONS  = generate_transactions(CONTRACTS, 200)
ALERTS        = generate_alerts(CONTRACTS)

# ══════════════════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    stats = _compute_stats()
    return render_template('dashboard.html', stats=stats,
                           contracts=CONTRACTS[:10], alerts=ALERTS[:5])

@app.route('/contracts')
def contracts():
    status_filter = request.args.get('status', 'all')
    filtered = CONTRACTS if status_filter == 'all' else \
               [c for c in CONTRACTS if c['status'].lower() == status_filter.lower()]
    return render_template('contracts.html', contracts=filtered,
                           status_filter=status_filter)

@app.route('/transactions')
def transactions():
    return render_template('transactions.html', transactions=TRANSACTIONS[:50])

@app.route('/reminders')
def reminders():
    expiring = [c for c in CONTRACTS
                if c['days_remaining'] is not None and 0 < c['days_remaining'] <= 30]
    return render_template('reminders.html', expiring=expiring, alerts=ALERTS)

@app.route('/test-cases')
def test_cases():
    return render_template('test_cases.html')

# ── API Endpoints ──────────────────────────────────────────────

@app.route('/api/stats')
def api_stats():
    return jsonify(_compute_stats())

@app.route('/api/contracts')
def api_contracts():
    return jsonify(CONTRACTS)

@app.route('/api/transactions')
def api_transactions():
    return jsonify(TRANSACTIONS)

@app.route('/api/contracts/status-distribution')
def api_status_dist():
    counts = {}
    for c in CONTRACTS:
        counts[c['status']] = counts.get(c['status'], 0) + 1
    return jsonify(counts)

@app.route('/api/contracts/monthly-value')
def api_monthly_value():
    monthly = {}
    for c in CONTRACTS:
        key = c['start_date'][:7]
        monthly[key] = monthly.get(key, 0) + c['value']
    sorted_keys = sorted(monthly.keys())[-12:]
    return jsonify({k: monthly[k] for k in sorted_keys})

@app.route('/api/transactions/timeline')
def api_tx_timeline():
    daily = {}
    for t in TRANSACTIONS:
        key = t['date'][:10]
        daily[key] = daily.get(key, 0) + t['amount']
    sorted_keys = sorted(daily.keys())[-30:]
    return jsonify([{"date": k, "amount": daily[k]} for k in sorted_keys])

@app.route('/api/send-reminder/<contract_id>', methods=['POST'])
def send_reminder(contract_id):
    contract = next((c for c in CONTRACTS if c['id'] == contract_id), None)
    if not contract:
        return jsonify({"error": "Contract not found"}), 404
    results = reminder_engine.send_expiry_reminder(contract)
    return jsonify({"success": True, "results": results,
                    "message": f"Reminder sent for {contract['title']}"})

@app.route('/api/send-bulk-reminders', methods=['POST'])
def send_bulk_reminders():
    expiring = [c for c in CONTRACTS
                if c['days_remaining'] is not None and 0 < c['days_remaining'] <= 30]
    results = []
    for c in expiring[:5]:
        r = reminder_engine.send_expiry_reminder(c)
        results.append({"contract": c['title'], "results": r})
    return jsonify({"sent": len(results), "results": results})

@app.route('/api/alerts')
def api_alerts():
    return jsonify(ALERTS)

# ── Helpers ────────────────────────────────────────────────────
def _compute_stats():
    total_value     = sum(c['value'] for c in CONTRACTS)
    active          = sum(1 for c in CONTRACTS if c['status'] == 'Active')
    expiring_soon   = sum(1 for c in CONTRACTS
                          if c.get('days_remaining') and 0 < c['days_remaining'] <= 30)
    total_tx        = sum(t['amount'] for t in TRANSACTIONS)
    completed_tx    = sum(1 for t in TRANSACTIONS if t['status'] == 'Completed')
    pending_tx      = sum(1 for t in TRANSACTIONS if t['status'] == 'Pending')
    by_category = {}
    for c in CONTRACTS:
        by_category[c['category']] = by_category.get(c['category'], 0) + c['value']
    return {
        "total_contracts":   len(CONTRACTS),
        "active_contracts":  active,
        "total_value":       total_value,
        "expiring_soon":     expiring_soon,
        "total_transactions": len(TRANSACTIONS),
        "transaction_volume": total_tx,
        "completed_tx":      completed_tx,
        "pending_tx":        pending_tx,
        "by_category":       by_category,
        "generated_at":      datetime.now().isoformat(),
    }

if __name__ == '__main__':
    print("🚀 Contract Management System running on http://localhost:5000")
    app.run(debug=True, port=5000)
