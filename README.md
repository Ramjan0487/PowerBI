# 🚀 AI-Powered PKI & Contract Management System (CMS Pro)

![Version](https://img.shields.io/badge/version-2.1-green)
![Backend](https://img.shields.io/badge/backend-Flask-blue)
![Frontend](https://img.shields.io/badge/frontend-Dashboard_UI-purple)
![Security](https://img.shields.io/badge/security-Zero_Trust-red)
![Testing](https://img.shields.io/badge/testing-Katalon_TestOps-orange)

---

## 📌 Overview

The **AI-Powered PKI & Contract Management System (CMS Pro)** is a **full enterprise-grade platform** designed to manage:

* 📄 Digital Contracts
* 🔐 PKI (Public Key Infrastructure)
* 💳 Transactions & Payments (MoMo Ready 🇷🇼)
* 🔔 Automated Notifications (SMS + Email)
* 📊 Real-time Analytics Dashboard
* 🧪 QA Automation via Katalon TestOps

This system combines **security, automation, analytics, and AI intelligence** into one unified platform.

---

## 🏗️ System Architecture

```text
Frontend (Dashboard UI)
        ↓
Flask API (Secure Backend)
        ↓
PostgreSQL Database
        ↓
Services Layer:
   ├── PKI Engine
   ├── Contract Engine
   ├── Notification Engine
   ├── Transaction Engine
        ↓
Integrations:
   ├── Twilio (SMS)
   ├── Email (SMTP / SendGrid)
   ├── MoMo API (MTN Rwanda)
   ├── Katalon TestOps
```

---

## ✨ Key Features

### 🔐 Security & PKI

* Public Key Infrastructure (PKI)
* Digital Signature Validation
* Zero Trust Architecture
* JWT Authentication & RBAC

### 📄 Contract Management

* Full lifecycle management
* Expiry tracking & alerts
* Vendor & category tracking
* Auto-renewal workflows

### 💳 Transactions & Payments

* Transaction ledger system
* MoMo API integration (Rwanda)
* Financial reporting dashboard

### 🔔 Notification System

* SMS alerts via Twilio
* Email reminders (Flask-Mail / SMTP)
* Automated expiry alerts

### 📊 Dashboard & Analytics

* KPI Monitoring
* Charts (Chart.js)
* Real-time updates
* Power BI / GA4 integration ready

### 🧪 QA Automation (Katalon)

* Integrated with Katalon TestOps
* Automated UI/API testing
* Test case management (100+ ready)
* CI/CD testing pipelines

---

## 🧠 AI Capabilities

* Contract Risk Analysis
* Clause Detection (Penalty, Auto-renew)
* Smart Alerts & Predictions
* Future: ML-based contract scoring

---

## 🗄️ Tech Stack

| Layer     | Technology             |
| --------- | ---------------------- |
| Frontend  | HTML, CSS, Chart.js    |
| Backend   | Flask (Python 3.11)    |
| Database  | PostgreSQL / SQLite    |
| Auth      | JWT + Bcrypt           |
| Messaging | Twilio SMS             |
| Email     | Flask-Mail / SMTP      |
| Payments  | MTN MoMo API           |
| Queue     | Celery + Redis         |
| Testing   | Katalon TestOps        |
| DevOps    | Docker, Docker Compose |

---

## 📁 Project Structure

```bash
cms-enterprise/
│
├── app/
│   ├── routes/
│   ├── models/
│   ├── services/
│   ├── tasks/
│
├── frontend/
│   └── CMS_Dashboard.html
│
├── config.py
├── app.py
├── requirements.txt
├── docker-compose.yml
└── README.md
```

---

## ⚙️ Installation & Setup

### 1️⃣ Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd cms-enterprise
```

### 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Run Application

```bash
python app.py
```

### 4️⃣ Run Celery Worker

```bash
celery -A tasks.reminder worker --loglevel=info
```

---

## 🐳 Docker Deployment

```bash
docker-compose up --build
```

---

## 🔐 Authentication API

### Login

```bash
POST /api/auth/login
```

### Signup

```bash
POST /api/auth/signup
```

---

## 📡 API Endpoints

| Endpoint          | Method | Description       |
| ----------------- | ------ | ----------------- |
| /api/contracts    | GET    | Get all contracts |
| /api/contracts    | POST   | Create contract   |
| /api/auth/login   | POST   | Login             |
| /api/auth/signup  | POST   | Register          |
| /api/transactions | GET    | Get transactions  |

---

## 📩 Notification Flow

```text
Contract Expiry → Alert Engine → SMS (Twilio) + Email → User Notification
```

---

## 🧪 Testing (Katalon TestOps)

* Automated test suites
* API testing
* UI testing
* CI/CD integration

---

## 🔐 Security Best Practices

* HTTPS enforcement
* JWT token expiration
* Input validation
* SQL Injection protection
* Role-Based Access Control

---

## 🌍 Deployment Options

* ☁️ AWS (EC2 / RDS)
* 🚀 Render
* ⚡ Railway
* 🟦 Azure

---

## 📈 Future Enhancements

* AI Contract Scoring Engine
* Blockchain-based PKI
* Multi-tenant SaaS model
* Mobile App (Flutter)

---

## 👨‍💻 Author

**Ntambara Rukaka Steven**
Software Engineer | QA Engineer | Systems Architect

---

## 📜 License

MIT License

---

## ⭐ Support

If you like this project:

* ⭐ Star the repository
* 🍴 Fork it
* 🧪 Contribute test cases
* 🚀 Deploy your own version

---

## 🎯 Final Note

This system is designed for:

* Governments (e.g., Rwanda 🇷🇼)
* Enterprises
* Financial institutions
* Legal firms

**A complete digital transformation platform for contracts, security, and analytics.**
