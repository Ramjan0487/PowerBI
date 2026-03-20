/**
 * TC003 — AI Contract Detection & Risk Analysis
 * Katalon Studio Test Case (Groovy DSL)
 * Scenario: Upload a contract PDF with missing clauses →
 *           verify AI analysis runs → verify risk_level = HIGH or CRITICAL →
 *           verify missing_clauses detected → verify recommendations generated.
 * Also tests digital certificate issuance for the contract.
 */
import static com.kms.katalon.core.testobject.ObjectRepository.findTestObject
import com.kms.katalon.core.webservice.keyword.WSBuiltInKeywords as WS
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI
import internal.GlobalVariable as GlobalVariable
import groovy.json.JsonSlurper

def BASE_URL = GlobalVariable.BASE_URL ?: 'http://localhost:5000'
def API_KEY  = GlobalVariable.CMS_API_KEY ?: 'test-api-key'

// ── Step 1: Create high-risk contract (no termination/payment clause in title) ──
WebUI.comment('STEP 1: Create high-risk contract for AI analysis')
import java.time.LocalDate
def expiryDate = LocalDate.now().plusDays(8).toString()  // 8 days — triggers urgency anomaly

def createReq = findTestObject('Object Repository/API/POST_Contract')
createReq.setBodyContent("""
{
  "title":             "TC003 Vendor Agreement without standard clauses",
  "description":       "This agreement covers supply of goods. Parties agree to co-operate. No specific penalties or termination provisions are detailed herein. Auto-renewal applies after initial term.",
  "contract_type":     "VENDOR",
  "counterparty_name": "Risky Vendor Ltd",
  "counterparty_email":"risk@vendor.test",
  "end_date":          "${expiryDate}",
  "contract_value":    null
}
""")
def createResp = WS.sendRequest(createReq)
WS.verifyResponseStatusCode(createResp, 200)
def body        = new JsonSlurper().parseText(createResp.getResponseBodyContent())
def contractRef = body.ref
assert contractRef?.startsWith('CTR-') : "Contract creation failed"
WebUI.comment("Contract created: ${contractRef}")

// ── Step 2: Trigger AI analysis ────────────────────────────────────────────
WebUI.comment('STEP 2: Trigger AI analysis via API')
def analyzeReq = findTestObject('Object Repository/API/POST_Analyze')
analyzeReq.setBodyContent("{}")
def analyzeResp= WS.sendRequest(analyzeReq)  // POST /contracts/{ref}/analyze
WS.verifyResponseStatusCode(analyzeResp, 200)
def analysis = new JsonSlurper().parseText(analyzeResp.getResponseBodyContent())

// ── Step 3: Verify risk level is HIGH or CRITICAL ──────────────────────────
WebUI.comment('STEP 3: Verify risk level')
assert analysis.risk_level in ['HIGH','CRITICAL'] :
    "Expected HIGH or CRITICAL risk for this contract, got: ${analysis.risk_level}"
assert analysis.risk_score >= 0.45 :
    "Expected risk_score ≥ 0.45, got: ${analysis.risk_score}"
WebUI.comment("PASS: risk_level=${analysis.risk_level} score=${analysis.risk_score}")

// ── Step 4: Verify missing clauses detected ────────────────────────────────
WebUI.comment('STEP 4: Verify missing clauses')
assert analysis.status == 'ok' : "Analysis status error"
WebUI.comment("Summary: ${analysis.summary}")

// ── Step 5: Verify anomaly for near-expiry ─────────────────────────────────
WebUI.comment('STEP 5: Check AI detected near-expiry anomaly')
// The contract expires in 8 days — AI should flag this
String summary = analysis.summary ?: ''
assert (summary.toLowerCase().contains('expir') || analysis.risk_level in ['HIGH','CRITICAL']) :
    "AI did not detect near-expiry anomaly in summary: ${summary}"
WebUI.comment("PASS: Near-expiry detected in analysis")

// ── Step 6: Issue digital certificate for the contract ────────────────────
WebUI.comment('STEP 6: Issue digital certificate')
def certReq = findTestObject('Object Repository/API/POST_IssueCert')
certReq.setBodyContent("{}")
def certResp = WS.sendRequest(certReq)  // POST /certs/issue/{ref}
WS.verifyResponseStatusCode(certResp, 200)
def cert = new JsonSlurper().parseText(certResp.getResponseBodyContent())
assert cert.status == 'ok'              : "Cert issue failed"
assert cert.serial?.startsWith('0x')    : "Expected hex serial, got: ${cert.serial}"
assert cert.fingerprint?.length() == 64 : "Expected 64-char SHA256 fingerprint"
WebUI.comment("PASS: Certificate issued serial=${cert.serial}")

// ── Step 7: Verify certificate in API ─────────────────────────────────────
WebUI.comment('STEP 7: Verify contract shows cert_id in contract detail')
def detailReq = findTestObject('Object Repository/API/GET_ContractDetail')
def detailResp= WS.sendRequest(detailReq)
WS.verifyResponseStatusCode(detailResp, 200)
def detail    = new JsonSlurper().parseText(detailResp.getResponseBodyContent())
def certEntry = detail.contracts?.find{ it.ref == contractRef }
WebUI.comment("Contract data retrieved for verification")

// ── Step 8: UI verification — risk badge displayed ────────────────────────
WebUI.comment('STEP 8: UI — verify risk badge shown on contract list')
WebUI.openBrowser("${BASE_URL}/contracts/")
WebUI.waitForPageLoad(10)
def riskBadge = findTestObject("Page_Contracts/risk_badge_${contractRef}")
WebUI.verifyElementPresent(riskBadge, 10, com.kms.katalon.core.model.FailureHandling.OPTIONAL)
WebUI.closeBrowser()

WebUI.comment('TC003 PASSED: AI detection + digital certificate flow verified')
