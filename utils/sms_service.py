"""
SMS Service - Twilio integration with mock fallback
"""
import os
from datetime import datetime


class SMSService:
    """SMS via Twilio (graceful mock fallback for demo/testing)"""

    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token  = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_FROM_NUMBER", "+12025551234")
        self._client = None
        if self.account_sid and self.auth_token:
            try:
                from twilio.rest import Client
                self._client = Client(self.account_sid, self.auth_token)
            except ImportError:
                pass

    def send(self, to: str, body: str) -> dict:
        """Send SMS. Returns result dict always — never raises."""
        if not to:
            return {"success": False, "error": "No phone number provided", "channel": "none"}

        if self._client:
            try:
                msg = self._client.messages.create(
                    body=body, from_=self.from_number, to=to)
                return {"success": True, "sid": msg.sid, "channel": "twilio",
                        "sent_at": datetime.now().isoformat()}
            except Exception as e:
                return {"success": False, "error": str(e), "channel": "twilio"}

        # Mock response for demo / CI environments
        print(f"[SMS MOCK] To: {to}\n  {body[:120]}\n")
        return {
            "success": True,
            "mock": True,
            "to": to,
            "preview": body[:100],
            "channel": "mock",
            "sent_at": datetime.now().isoformat(),
        }
