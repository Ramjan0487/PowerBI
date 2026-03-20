"""
AI Contract Analyzer
Uses keyword + rule-based analysis + optional OpenAI GPT for deep analysis.
Returns risk score, detected clauses, missing clauses, anomalies, recommendations.
"""
import json
import time
import re
import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AnalysisResult:
    risk_score:       float       = 0.0
    risk_level:       str         = "LOW"
    contract_type:    str         = "UNKNOWN"
    key_clauses:      List[str]   = field(default_factory=list)
    missing_clauses:  List[str]   = field(default_factory=list)
    anomalies:        List[str]   = field(default_factory=list)
    recommendations:  List[str]   = field(default_factory=list)
    summary:          str         = ""
    confidence:       float       = 0.0
    model_version:    str         = "rule-v1.0"
    duration_ms:      float       = 0.0


# ── Clause detection patterns ──────────────────────────────────────────────
CLAUSE_PATTERNS = {
    "termination":        [r"terminat\w*", r"cancel\w*", r"end of agreement"],
    "confidentiality":    [r"confidential\w*", r"non-disclosure", r"nda"],
    "payment_terms":      [r"payment\w*", r"invoice\w*", r"due date", r"net \d+"],
    "liability":          [r"liabilit\w*", r"indemnif\w*", r"damage\w*"],
    "dispute_resolution": [r"arbitrat\w*", r"mediat\w*", r"dispute resolution"],
    "intellectual_prop":  [r"intellectual property", r"copyright", r"patent"],
    "governing_law":      [r"governing law", r"jurisdiction", r"laws of"],
    "force_majeure":      [r"force majeure", r"act of god", r"unforeseen"],
    "auto_renewal":       [r"auto.?renew\w*", r"automatically renew", r"evergreen"],
    "warranty":           [r"warrant\w*", r"represent\w*", r"guaranty"],
    "non_compete":        [r"non.?compet\w*", r"competitive activit\w*"],
    "sla":                [r"service level", r"uptime", r"sla", r"availability"],
    "data_protection":    [r"data protection", r"gdpr", r"privacy policy", r"personal data"],
    "penalty":            [r"penalt\w*", r"liquidated damages", r"late fee"],
}

REQUIRED_CLAUSES   = ["termination", "payment_terms", "governing_law", "liability"]
RISK_CLAUSES       = ["penalty", "auto_renewal", "non_compete"]

CONTRACT_TYPE_KEYWORDS = {
    "SERVICE":    ["services", "service agreement", "consulting", "professional services"],
    "VENDOR":     ["vendor", "supplier", "procurement", "purchase order"],
    "EMPLOYMENT": ["employment", "employee", "salary", "compensation", "hire"],
    "NDA":        ["non-disclosure", "nda", "confidentiality agreement"],
    "LEASE":      ["lease", "rental", "tenancy", "landlord", "tenant"],
    "LICENSE":    ["license", "licensing", "software license", "subscription"],
    "PARTNERSHIP":["partnership", "joint venture", "collaboration"],
}


def run_analysis(contract) -> AnalysisResult:
    """Run full AI analysis on a contract. Returns AnalysisResult."""
    t0 = time.perf_counter()
    r  = AnalysisResult()

    # Get text content
    text = _extract_text(contract)
    text_lower = text.lower()

    # Detect contract type
    r.contract_type = _detect_type(text_lower) or (contract.contract_type or "UNKNOWN")

    # Detect clauses
    detected = []
    for clause, patterns in CLAUSE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                detected.append(clause)
                break
    r.key_clauses = detected

    # Missing required clauses
    r.missing_clauses = [c for c in REQUIRED_CLAUSES if c not in detected]

    # Anomalies
    anomalies = []
    if contract.end_date:
        from datetime import date
        days_left = (contract.end_date - date.today()).days
        if days_left < 0:
            anomalies.append(f"Contract expired {abs(days_left)} days ago.")
        elif days_left < 30:
            anomalies.append(f"Contract expires in {days_left} days — urgent renewal needed.")
        elif days_left < 90:
            anomalies.append(f"Contract expires in {days_left} days.")

    if "auto_renewal" in detected:
        anomalies.append("Auto-renewal clause detected — review cancellation window.")
    if "penalty" in detected:
        anomalies.append("Penalty clause present — verify thresholds.")
    if not contract.contract_value:
        anomalies.append("No contract value specified.")
    if not contract.file_path:
        anomalies.append("No signed document attached.")

    r.anomalies = anomalies

    # Risk score calculation
    score = 0.0
    score += len(r.missing_clauses) * 0.15        # missing required clauses
    score += sum(0.10 for c in RISK_CLAUSES if c in detected)  # risky clauses
    score += len(anomalies) * 0.05
    score = min(score, 1.0)
    r.risk_score = round(score, 3)

    if score < 0.2:      r.risk_level = "LOW"
    elif score < 0.45:   r.risk_level = "MEDIUM"
    elif score < 0.70:   r.risk_level = "HIGH"
    else:                r.risk_level = "CRITICAL"

    # Recommendations
    recs = []
    if r.missing_clauses:
        recs.append(f"Add missing clauses: {', '.join(r.missing_clauses)}.")
    if "data_protection" not in detected:
        recs.append("Consider adding a data protection / GDPR clause.")
    if "force_majeure" not in detected:
        recs.append("Consider adding a force majeure clause.")
    if r.risk_level in ("HIGH", "CRITICAL"):
        recs.append("High-risk contract — request legal review before signing.")
    r.recommendations = recs

    # Summary
    r.summary = (
        f"{r.contract_type} contract with {contract.counterparty_name or 'counterparty'}. "
        f"Risk level: {r.risk_level}. "
        f"Detected {len(detected)}/{len(CLAUSE_PATTERNS)} standard clauses. "
        f"{len(r.missing_clauses)} required clause(s) missing."
    )

    # Optional: enrich with OpenAI
    if os.getenv("OPENAI_API_KEY"):
        try:
            r = _enrich_with_openai(r, text[:3000])
            r.model_version = "gpt-4o-mini+rule-v1.0"
        except Exception:
            pass

    r.confidence = 0.75 if not os.getenv("OPENAI_API_KEY") else 0.92
    r.duration_ms = round((time.perf_counter() - t0) * 1000, 1)
    return r


def analyze_contract_async(app, contract_id: int):
    """Save analysis result to database (call in background thread)."""
    import threading
    def _run():
        with app.app_context():
            from app.models import Contract, AIAnalysis
            from app import db
            contract = Contract.query.get(contract_id)
            if not contract:
                return
            result = run_analysis(contract)
            existing = AIAnalysis.query.filter_by(contract_id=contract_id).first()
            if existing:
                db.session.delete(existing)
                db.session.commit()
            analysis = AIAnalysis(
                contract_id     = contract_id,
                risk_score      = result.risk_score,
                risk_level      = result.risk_level,
                contract_type   = result.contract_type,
                key_clauses     = json.dumps(result.key_clauses),
                missing_clauses = json.dumps(result.missing_clauses),
                anomalies       = json.dumps(result.anomalies),
                summary         = result.summary,
                recommendations = json.dumps(result.recommendations),
                confidence      = result.confidence,
                model_version   = result.model_version,
                duration_ms     = result.duration_ms,
            )
            db.session.add(analysis)
            db.session.commit()
    threading.Thread(target=_run, daemon=True).start()


# ── Helpers ────────────────────────────────────────────────────────────────
def _extract_text(contract) -> str:
    """Extract text from contract file or fallback to DB fields."""
    text_parts = [
        contract.title or "",
        contract.description or "",
        contract.contract_type or "",
    ]
    if contract.file_path and os.path.exists(contract.file_path):
        try:
            ext = contract.file_path.rsplit(".", 1)[-1].lower()
            if ext == "pdf":
                import pdfplumber
                with pdfplumber.open(contract.file_path) as pdf:
                    text_parts.extend(p.extract_text() or "" for p in pdf.pages[:10])
            elif ext in ("docx", "doc"):
                import docx2txt
                text_parts.append(docx2txt.process(contract.file_path))
            else:
                with open(contract.file_path, "r", errors="ignore") as fh:
                    text_parts.append(fh.read(50000))
        except Exception:
            pass
    return " ".join(text_parts)


def _detect_type(text: str) -> Optional[str]:
    for ctype, kws in CONTRACT_TYPE_KEYWORDS.items():
        if any(kw in text for kw in kws):
            return ctype
    return None


def _enrich_with_openai(result: AnalysisResult, text: str) -> AnalysisResult:
    import openai
    prompt = f"""Analyze this contract excerpt and return JSON with keys:
summary (str), additional_risks (list of str), key_recommendations (list of str).

Contract text:
{text}

JSON only, no markdown."""
    resp = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500, temperature=0,
    )
    data = json.loads(resp.choices[0].message.content)
    result.summary         = data.get("summary", result.summary)
    result.recommendations = data.get("key_recommendations", result.recommendations)
    result.anomalies.extend(data.get("additional_risks", []))
    return result
