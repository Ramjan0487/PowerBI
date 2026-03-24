# CMS Pro — Contract Management System

**Flask · Python · Power BI-style Dashboard · Twilio SMS · Flask-Mail · 12 Test Cases**

---

## 🚀 Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your credentials
python app.py
# → http://localhost:5000
```

## 📁 Structure
```
contract_mgmt/
├── app.py                        # Flask application & API routes
├── utils/
│   ├── data_generator.py         # Generates 50 contracts, 200 transactions
│   ├── sms_service.py            # Twilio SMS (mock fallback for CI)
│   └── reminder_engine.py        # SMS + Email expiry reminder engine
├── templates/
│   ├── base.html                 # Sidebar nav, topbar, toast
│   ├── dashboard.html            # Executive KPIs + 5 charts
│   ├── contracts.html            # Filterable contract table
│   ├── transactions.html         # Full transaction ledger
│   ├── reminders.html            # Expiry alerts + send buttons
│   └── test_cases.html           # 12 TCs with flow diagrams
├── static/
│   └── dashboard_standalone.html # Standalone Power BI dashboard (no server needed)
├── tests/
│   ├── test_cms.py               # pytest test suite
│   └── run_tests.py              # Standalone runner (no pytest needed)
└── requirements.txt
```

## 🔧 Environment Variables

```bash
# Twilio SMS
TWILIO_ACCOUNT_SID=ACxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+12025551234

# Email (Gmail / SendGrid / Mailtrap)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=you@gmail.com
MAIL_PASSWORD=your_app_password
MAIL_DEFAULT_SENDER=CMS <you@gmail.com>

SECRET_KEY=your-secret-key
```

## 🧪 Run Tests

```bash
# Standalone (no pytest needed)
python3 tests/run_tests.py

# With pytest
pytest tests/test_cms.py -v
```

## 📊 Dashboard Views

| Route | Description |
|-------|-------------|
| `/dashboard` | KPIs + 5 charts + alerts |
| `/contracts` | All 50 contracts, filterable by status |
| `/transactions` | 200 transactions ledger |
| `/reminders` | Expiry alerts + SMS/Email send |
| `/test-cases` | 12 TCs + flow diagrams |

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats` | Dashboard KPI data |
| GET | `/api/contracts` | All contracts JSON |
| GET | `/api/transactions` | All transactions JSON |
| GET | `/api/contracts/status-distribution` | Donut chart data |
| GET | `/api/contracts/monthly-value` | Bar chart data |
| GET | `/api/transactions/timeline` | Line chart data |
| POST | `/api/send-reminder/<id>` | Send SMS+Email for one contract |
| POST | `/api/send-bulk-reminders` | Send reminders for all expiring (max 5) |
| GET | `/api/alerts` | Active alert list |

## 🏗️ Architecture

```
Browser ←→ Flask App (Python 3.11)
              ├── Jinja2 Templates → HTML Dashboard
              ├── Chart.js 4.4    → Visual charts
              ├── Twilio SMS      → Phone reminders (+250...)
              └── Flask-Mail SMTP → HTML email reminders
```

## 📋 12 Test Cases

| # | Test Case | Status |
|---|-----------|--------|
| TC-01 | Contract Creation & Validation | ✅ PASS |
| TC-02 | Contract Expiry Date Calculation | ✅ PASS |
| TC-03 | SMS Reminder Dispatch | ✅ PASS |
| TC-04 | Email Reminder HTML Delivery | ✅ PASS |
| TC-05 | Dashboard KPI Accuracy | ✅ PASS |
| TC-06 | Transaction Ledger Integrity | ✅ PASS |
| TC-07 | Bulk Reminder API Endpoint | ✅ PASS |
| TC-08 | Contract Status Filter | ✅ PASS |
| TC-09 | Chart Data API Format | ✅ PASS |
| TC-10 | API Error Handling & Security | ✅ PASS |
| TC-11 | Alert Severity Classification | ✅ PASS |
| TC-12 | End-to-End Expiry Workflow | ✅ PASS |
