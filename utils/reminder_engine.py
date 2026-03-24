"""Reminder Engine - orchestrates SMS + Email expiry reminders"""
import os
from datetime import datetime
from utils.sms_service import SMSService


class ReminderEngine:
    def __init__(self, mail, sms):
        self.mail = mail
        self.sms  = sms

    def send_expiry_reminder(self, contract: dict) -> dict:
        dr, phone, email = contract.get("days_remaining", 0), contract.get("phone"), contract.get("email")
        results = {}
        if phone:
            body = (f"\u26a0\ufe0f CONTRACT EXPIRY ALERT\n"
                    f"Contract: {contract['title']}\nVendor: {contract['vendor']}\n"
                    f"Expires: {contract['end_date']} ({dr} days)\nLogin: cms.example.rw")
            results["sms"] = self.sms.send(phone, body)
        if email:
            results["email"] = self._send_email(contract, dr)
        return results

    def _send_email(self, c: dict, days_remaining: int) -> dict:
        severity = "CRITICAL" if days_remaining <= 7 else "URGENT" if days_remaining <= 14 else "WARNING"
        subject  = f"[{severity}] Contract Expiring in {days_remaining} Days: {c['title']}"
        html = (f"<h2>Contract Expiry Notice</h2>"
                f"<p><b>{c['title']}</b> expires in <b style='color:red'>{days_remaining} days</b> ({c['end_date']}).</p>"
                f"<table border='1' cellpadding='8' style='border-collapse:collapse'>"
                f"<tr><td>ID</td><td>{c['id']}</td></tr>"
                f"<tr><td>Vendor</td><td>{c['vendor']}</td></tr>"
                f"<tr><td>Owner</td><td>{c['owner']}</td></tr>"
                f"<tr><td>Value</td><td>${c['value']:,.2f}</td></tr>"
                f"<tr><td>End Date</td><td>{c['end_date']}</td></tr>"
                f"</table><br><a href='http://cms.example.rw/contracts/{c['id']}'>Review Contract</a>")
        try:
            from flask_mail import Message as MailMsg
            msg = MailMsg(subject=subject, recipients=[c['email']], html=html)
            self.mail.send(msg)
            return {"success": True, "to": c['email'], "channel": "smtp", "sent_at": datetime.now().isoformat()}
        except Exception:
            print(f"[EMAIL MOCK] To: {c['email']} | {subject}")
            return {"success": True, "mock": True, "to": c['email'], "channel": "mock", "sent_at": datetime.now().isoformat()}
