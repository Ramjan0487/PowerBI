"""Realistic Contract Management System data generator"""
import uuid, random
from datetime import datetime, timedelta

CATEGORIES   = ["IT Services","Procurement","Legal","HR","Construction","Consulting","Maintenance","SaaS","Vendor","Leasing"]
VENDORS      = ["TechCorp Ltd","BuildRight Co","LexGroup","HRpro Ltd","CloudVault","SafeguardInc","AcmeSystems","RwandaBuild","KigaliTech","ProServe Africa"]
OWNERS       = ["Jean Damascene","Alice Mukamana","Eric Habimana","Grace Uwase","Patrick Nkurunziza","Marie Ingabire","David Mugisha","Claudine Uwimana","Robert Gahima","Solange Iradukunda"]
TYPES        = ["Fixed-Price","Time-and-Material","Cost-Plus","Retainer","Framework","Milestone","SLA","Subscription"]
STATUSES     = ["Active","Pending","Expired","Terminated","Draft","Under Review"]
TX_TYPES     = ["Payment","Invoice","Amendment","Renewal","Penalty","Deposit","Refund","Milestone"]
TX_STATUSES  = ["Completed","Pending","Failed","Processing","Cancelled"]
ALERT_TYPES  = ["Expiration Warning","Renewal Due","Payment Overdue","Milestone Reached","SLA Breach","Budget Exceeded"]

def random_date(start_days_ago=720, end_days_ago=-180):
    base  = datetime.now()
    start = base - timedelta(days=start_days_ago)
    end   = base + timedelta(days=-end_days_ago)
    return start + (end - start) * random.random()

def generate_contracts(n=50):
    contracts = []
    for i in range(n):
        start  = random_date(540, 0)
        dur    = random.randint(90, 730)
        end    = start + timedelta(days=dur)
        now    = datetime.now()
        days_r = (end - now).days
        if days_r < 0:
            status = "Expired"
        elif days_r <= 30:
            status = random.choice(["Active", "Under Review"])
        elif days_r <= 180:
            status = random.choice(["Active", "Active", "Pending", "Under Review"])
        else:
            status = random.choice(["Active", "Active", "Draft", "Pending"])
        value = round(random.uniform(5000, 2000000), 2)
        contracts.append({
            "id":            str(uuid.uuid4())[:8].upper(),
            "title":         f"{random.choice(CATEGORIES)} Contract #{i+1:03d}",
            "vendor":        random.choice(VENDORS),
            "owner":         random.choice(OWNERS),
            "category":      random.choice(CATEGORIES),
            "type":          random.choice(TYPES),
            "status":        status,
            "value":         value,
            "start_date":    start.strftime("%Y-%m-%d"),
            "end_date":      end.strftime("%Y-%m-%d"),
            "days_remaining": days_r,
            "phone":         f"+2507{random.choice(['8','3'])}{random.randint(1000000,9999999)}",
            "email":         f"{random.choice(OWNERS).split()[0].lower()}@example.rw",
            "renewal_type":  random.choice(["Auto","Manual","None"]),
            "signed":        random.choice([True, True, True, False]),
            "budget_used_pct": round(random.uniform(10, 110), 1),
        })
    return contracts

def generate_transactions(contracts, n=200):
    txs = []
    for i in range(n):
        c   = random.choice(contracts)
        amt = round(random.uniform(500, c["value"] * 0.25), 2)
        dt  = random_date(365, 0)
        txs.append({
            "id":            f"TX-{str(uuid.uuid4())[:6].upper()}",
            "contract_id":   c["id"],
            "contract_title":c["title"],
            "type":          random.choice(TX_TYPES),
            "amount":        amt,
            "currency":      "USD",
            "status":        random.choices(TX_STATUSES, weights=[60,20,5,10,5])[0],
            "date":          dt.strftime("%Y-%m-%d %H:%M:%S"),
            "vendor":        c["vendor"],
            "reference":     f"REF-{random.randint(10000,99999)}",
            "description":   f"{random.choice(TX_TYPES)} for {c['category']} services",
        })
    return sorted(txs, key=lambda x: x["date"], reverse=True)

def generate_alerts(contracts):
    alerts = []
    for c in contracts:
        dr = c.get("days_remaining", 999)
        if dr is not None and dr <= 30 and dr >= 0:
            alerts.append({
                "id":       str(uuid.uuid4())[:8],
                "type":     "Expiration Warning",
                "contract_id":    c["id"],
                "contract_title": c["title"],
                "days_remaining": dr,
                "vendor":   c["vendor"],
                "email":    c["email"],
                "phone":    c["phone"],
                "severity": "Critical" if dr <= 7 else "High" if dr <= 14 else "Medium",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
        if c.get("budget_used_pct", 0) > 100:
            alerts.append({
                "id":       str(uuid.uuid4())[:8],
                "type":     "Budget Exceeded",
                "contract_id":    c["id"],
                "contract_title": c["title"],
                "days_remaining": dr,
                "vendor":   c["vendor"],
                "email":    c["email"],
                "phone":    c["phone"],
                "severity": "High",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
    return sorted(alerts, key=lambda x: x.get("days_remaining", 999))
