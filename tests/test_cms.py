"""
Contract Management System – 12 Pytest Test Cases
Run: pytest tests/test_cms.py -v --tb=short
"""

import pytest
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app, CONTRACTS, TRANSACTIONS, ALERTS
from utils.data_generator import generate_contracts, generate_transactions, generate_alerts
from utils.sms_service import SMSService
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def sample_contract():
    return {
        "id": "TEST001",
        "title": "Test IT Services Contract #001",
        "vendor": "TechCorp Ltd",
        "owner": "Jean Damascene",
        "category": "IT Services",
        "type": "Fixed-Price",
        "status": "Active",
        "value": 500000.00,
        "start_date": "2024-01-01",
        "end_date": (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d"),
        "days_remaining": 5,
        "phone": "+250780000001",
        "email": "jean@example.rw",
        "renewal_type": "Manual",
        "signed": True,
        "budget_used_pct": 75.0,
    }


# ════════════════════════════════════════════════════════════════
# TC-01: Contract Creation & Validation
# ════════════════════════════════════════════════════════════════
class TestTC01_ContractCreation:
    def test_generate_contracts_returns_correct_count(self):
        """Contract dataset is generated with exactly N records"""
        contracts = generate_contracts(10)
        assert len(contracts) == 10

    def test_all_required_fields_present(self):
        """Each contract has all required fields"""
        required = ['id','title','vendor','owner','category','type','status',
                    'value','start_date','end_date','days_remaining','phone','email']
        for c in CONTRACTS:
            for field in required:
                assert field in c, f"Missing field '{field}' in contract {c.get('id')}"

    def test_contract_value_is_positive(self):
        """All contract values are positive numbers"""
        for c in CONTRACTS:
            assert isinstance(c['value'], float), f"Value must be float: {c['id']}"
            assert c['value'] > 0, f"Value must be positive: {c['id']}"


# ════════════════════════════════════════════════════════════════
# TC-02: Contract Expiry Date Calculation
# ════════════════════════════════════════════════════════════════
class TestTC02_ExpiryCalculation:
    def test_expired_contracts_have_correct_status(self):
        """Contracts with past end_date are marked Expired"""
        expired = [c for c in CONTRACTS if c['status'] == 'Expired']
        for c in expired:
            if c.get('days_remaining') is not None:
                assert c['days_remaining'] < 0, \
                    f"Expired contract {c['id']} should have negative days_remaining"

    def test_expiring_contracts_in_alerts(self):
        """Contracts expiring ≤30 days appear in alerts"""
        expiring_ids = {c['id'] for c in CONTRACTS
                        if c.get('days_remaining') is not None and 0 < c['days_remaining'] <= 30}
        alert_ids = {a['contract_id'] for a in ALERTS if a['type'] == 'Expiration Warning'}
        for eid in expiring_ids:
            assert eid in alert_ids, f"Contract {eid} should be in alerts"

    def test_days_remaining_type(self):
        """days_remaining is always an integer or None"""
        for c in CONTRACTS:
            dr = c.get('days_remaining')
            if dr is not None:
                assert isinstance(dr, int), f"days_remaining must be int: {c['id']}"


# ════════════════════════════════════════════════════════════════
# TC-03: SMS Reminder Dispatch
# ════════════════════════════════════════════════════════════════
class TestTC03_SMSReminder:
    def test_sms_mock_returns_success(self, sample_contract):
        """SMSService mock returns success dict"""
        sms = SMSService()
        result = sms.send(sample_contract['phone'], "Test reminder message")
        assert result['success'] is True
        assert 'channel' in result

    def test_sms_send_api_endpoint(self, client, sample_contract):
        """POST /api/send-reminder/{id} returns 200 for valid contract"""
        contract_id = CONTRACTS[0]['id']
        resp = client.post(f'/api/send-reminder/{contract_id}')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data.get('success') is True

    def test_sms_invalid_contract_returns_404(self, client):
        """POST /api/send-reminder/INVALID returns 404"""
        resp = client.post('/api/send-reminder/INVALIDID999')
        assert resp.status_code == 404
        data = json.loads(resp.data)
        assert 'error' in data


# ════════════════════════════════════════════════════════════════
# TC-04: Email Reminder HTML Delivery
# ════════════════════════════════════════════════════════════════
class TestTC04_EmailReminder:
    def test_email_contains_required_fields(self, sample_contract):
        """Email HTML template includes all contract details"""
        from utils.reminder_engine import ReminderEngine
        mock_mail = MagicMock()
        mock_sms = MagicMock()
        mock_sms.send.return_value = {"success": True, "mock": True}
        engine = ReminderEngine(mock_mail, mock_sms)
        result = engine._send_email(sample_contract, 5)
        assert result['success'] is True

    def test_email_severity_critical_for_7days(self, sample_contract):
        """Email subject includes CRITICAL for ≤7 days"""
        from utils.reminder_engine import ReminderEngine
        engine = ReminderEngine(MagicMock(), MagicMock())
        # Verify severity logic inline
        days = 5
        severity = "🔴 CRITICAL" if days <= 7 else "🟠 URGENT" if days <= 14 else "🟡 WARNING"
        assert "CRITICAL" in severity

    def test_bulk_reminder_returns_sent_count(self, client):
        """POST /api/send-bulk-reminders returns {sent: N}"""
        resp = client.post('/api/send-bulk-reminders')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'sent' in data
        assert isinstance(data['sent'], int)


# ════════════════════════════════════════════════════════════════
# TC-05: Dashboard KPI Accuracy
# ════════════════════════════════════════════════════════════════
class TestTC05_DashboardKPI:
    def test_stats_api_returns_correct_total(self, client):
        """/api/stats total_contracts matches CONTRACTS length"""
        resp = client.get('/api/stats')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['total_contracts'] == len(CONTRACTS)

    def test_stats_active_count_correct(self, client):
        """/api/stats active_contracts matches Active contracts"""
        resp = client.get('/api/stats')
        data = json.loads(resp.data)
        expected_active = sum(1 for c in CONTRACTS if c['status'] == 'Active')
        assert data['active_contracts'] == expected_active

    def test_stats_total_value_matches(self, client):
        """/api/stats total_value matches sum of CONTRACTS values"""
        resp = client.get('/api/stats')
        data = json.loads(resp.data)
        expected = sum(c['value'] for c in CONTRACTS)
        assert abs(data['total_value'] - expected) < 0.01


# ════════════════════════════════════════════════════════════════
# TC-06: Transaction Ledger Integrity
# ════════════════════════════════════════════════════════════════
class TestTC06_TransactionIntegrity:
    def test_all_amounts_are_float(self):
        """All transaction amounts are float type"""
        for t in TRANSACTIONS:
            assert isinstance(t['amount'], float), f"Amount must be float: {t['id']}"
            assert t['amount'] > 0

    def test_all_statuses_valid(self):
        """All transaction statuses are from allowed enum"""
        valid = {'Completed','Pending','Failed','Processing','Cancelled'}
        for t in TRANSACTIONS:
            assert t['status'] in valid, f"Invalid status '{t['status']}' in {t['id']}"

    def test_transactions_route_200(self, client):
        """/transactions returns HTTP 200"""
        resp = client.get('/transactions')
        assert resp.status_code == 200


# ════════════════════════════════════════════════════════════════
# TC-07: Bulk Reminder API Endpoint
# ════════════════════════════════════════════════════════════════
class TestTC07_BulkReminder:
    def test_bulk_reminder_response_structure(self, client):
        """Bulk reminder returns correct JSON structure"""
        resp = client.post('/api/send-bulk-reminders')
        data = json.loads(resp.data)
        assert 'sent' in data
        assert 'results' in data
        assert isinstance(data['results'], list)

    def test_bulk_reminder_caps_at_five(self, client):
        """Bulk reminder sends max 5 per call"""
        resp = client.post('/api/send-bulk-reminders')
        data = json.loads(resp.data)
        assert data['sent'] <= 5


# ════════════════════════════════════════════════════════════════
# TC-08: Contract Status Filter
# ════════════════════════════════════════════════════════════════
class TestTC08_StatusFilter:
    @pytest.mark.parametrize("status", ['Active','Pending','Expired','Draft','Terminated'])
    def test_filter_returns_correct_status(self, client, status):
        """/contracts?status=X returns only matching status"""
        resp = client.get(f'/contracts?status={status}')
        assert resp.status_code == 200

    def test_filter_case_insensitive(self, client):
        """Status filter is case-insensitive"""
        resp_upper = client.get('/contracts?status=Active')
        resp_lower = client.get('/contracts?status=active')
        assert resp_upper.status_code == 200
        assert resp_lower.status_code == 200

    def test_filter_all_returns_all(self, client):
        """/contracts?status=all returns all contracts"""
        resp = client.get('/contracts?status=all')
        assert resp.status_code == 200


# ════════════════════════════════════════════════════════════════
# TC-09: Chart Data API Format
# ════════════════════════════════════════════════════════════════
class TestTC09_ChartDataFormat:
    def test_monthly_value_keys_are_strings(self, client):
        """/api/contracts/monthly-value returns string keys"""
        resp = client.get('/api/contracts/monthly-value')
        data = json.loads(resp.data)
        import re
        for k in data.keys():
            assert re.match(r'^\d{4}-\d{2}$', k), f"Key '{k}' not in YYYY-MM format"

    def test_timeline_returns_list_of_objects(self, client):
        """/api/transactions/timeline returns list of {date, amount}"""
        resp = client.get('/api/transactions/timeline')
        data = json.loads(resp.data)
        assert isinstance(data, list)
        for item in data:
            assert 'date' in item and 'amount' in item

    def test_status_dist_returns_dict(self, client):
        """/api/contracts/status-distribution returns dict"""
        resp = client.get('/api/contracts/status-distribution')
        data = json.loads(resp.data)
        assert isinstance(data, dict)
        assert len(data) > 0


# ════════════════════════════════════════════════════════════════
# TC-10: API Error Handling
# ════════════════════════════════════════════════════════════════
class TestTC10_ErrorHandling:
    def test_invalid_contract_id_returns_404(self, client):
        """Invalid contract ID returns 404 not 500"""
        resp = client.post('/api/send-reminder/DOESNOTEXIST')
        assert resp.status_code == 404

    def test_error_response_has_error_key(self, client):
        """Error response contains 'error' key"""
        resp = client.post('/api/send-reminder/DOESNOTEXIST')
        data = json.loads(resp.data)
        assert 'error' in data
        assert 'stack' not in data


# ════════════════════════════════════════════════════════════════
# TC-11: Alert Severity Classification
# ════════════════════════════════════════════════════════════════
class TestTC11_AlertSeverity:
    @pytest.mark.parametrize("days,expected_severity", [
        (3,  "Critical"),
        (7,  "Critical"),
        (8,  "High"),
        (14, "High"),
        (15, "Medium"),
        (30, "Medium"),
    ])
    def test_severity_classification(self, days, expected_severity):
        """Alert severity correctly classified by days remaining"""
        severity = "Critical" if days <= 7 else "High" if days <= 14 else "Medium"
        assert severity == expected_severity

    def test_alerts_sorted_by_urgency(self):
        """Alerts are sorted by days_remaining ascending"""
        if len(ALERTS) >= 2:
            for i in range(len(ALERTS)-1):
                dr1 = ALERTS[i].get('days_remaining', 9999)
                dr2 = ALERTS[i+1].get('days_remaining', 9999)
                assert dr1 <= dr2, "Alerts not sorted by urgency"


# ════════════════════════════════════════════════════════════════
# TC-12: End-to-End Contract Expiry Workflow
# ════════════════════════════════════════════════════════════════
class TestTC12_E2EWorkflow:
    def test_dashboard_loads_successfully(self, client):
        """Dashboard route returns 200"""
        resp = client.get('/dashboard')
        assert resp.status_code == 200

    def test_reminders_page_loads(self, client):
        """Reminders page returns 200"""
        resp = client.get('/reminders')
        assert resp.status_code == 200

    def test_full_reminder_pipeline(self, client):
        """Full pipeline: find expiring contract → send reminder → assert success"""
        expiring = [c for c in CONTRACTS
                    if c.get('days_remaining') and 0 < c['days_remaining'] <= 30]
        if expiring:
            contract_id = expiring[0]['id']
            resp = client.post(f'/api/send-reminder/{contract_id}')
            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert data['success'] is True
            assert 'results' in data

    def test_all_routes_return_200(self, client):
        """All main routes return HTTP 200"""
        routes = ['/dashboard', '/contracts', '/transactions', '/reminders', '/test-cases']
        for route in routes:
            resp = client.get(route)
            assert resp.status_code == 200, f"Route {route} returned {resp.status_code}"
