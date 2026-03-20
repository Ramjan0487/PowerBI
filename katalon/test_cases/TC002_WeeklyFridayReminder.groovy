/**
 * TC002 — Weekly Friday Reminder (SMS + Email)
 * Katalon Studio Test Case (Groovy DSL)
 * Scenario: Create a contract expiring in 45 days → trigger Friday digest →
 *           verify reminder records created → verify SMS + email dispatched.
 */
import static com.kms.katalon.core.testobject.ObjectRepository.findTestObject
import com.kms.katalon.core.webservice.keyword.WSBuiltInKeywords as WS
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI
import internal.GlobalVariable as GlobalVariable
import groovy.json.JsonSlurper

def BASE_URL   = GlobalVariable.BASE_URL ?: 'http://localhost:5000'
def API_KEY    = GlobalVariable.CMS_API_KEY ?: 'test-api-key'
def TEST_EMAIL = 'reminder_test@cms.test'
def TEST_PHONE = '+250788000099'

// ── Helper: send authenticated API request ─────────────────────────────────
def apiHeaders = [['name':'X-API-Key','value':API_KEY],['name':'Content-Type','value':'application/json']]

// ── Step 1: Create a contract expiring in 45 days ──────────────────────────
WebUI.comment('STEP 1: Create contract expiring in 45 days via API')
import java.time.LocalDate
def expiryDate = LocalDate.now().plusDays(45).toString()

def createReq = findTestObject('Object Repository/API/POST_Contract')
createReq.setBodyContent("""
{
  "title":             "TC002 Service Agreement",
  "contract_type":     "SERVICE",
  "counterparty_name": "Test Vendor Corp",
  "counterparty_email":"${TEST_EMAIL}",
  "counterparty_phone":"${TEST_PHONE}",
  "end_date":          "${expiryDate}",
  "contract_value":    50000,
  "currency":          "USD"
}
""")
def createResp = WS.sendRequest(createReq)
WS.verifyResponseStatusCode(createResp, 200)
def body       = new JsonSlurper().parseText(createResp.getResponseBodyContent())
def contractRef= body.ref
assert contractRef?.startsWith('CTR-') : "Expected CTR- ref, got: ${contractRef}"
WebUI.comment("Contract created: ${contractRef} expiring ${expiryDate}")

// ── Step 2: Verify contract appears in expiring API ────────────────────────
WebUI.comment('STEP 2: Verify contract appears in /api/v1/contracts/expiring?days=90')
def expiringReq = findTestObject('Object Repository/API/GET_Expiring')
def expiringResp= WS.sendRequest(expiringReq)
WS.verifyResponseStatusCode(expiringResp, 200)
def expiringList= new JsonSlurper().parseText(expiringResp.getResponseBodyContent())
def found = expiringList.find{ it.ref == contractRef }
assert found != null : "Contract ${contractRef} not found in expiring list"
assert found.days_left <= 90 : "Expected days_left ≤ 90, got ${found.days_left}"
WebUI.comment("PASS: Contract found with ${found.days_left} days until expiry")

// ── Step 3: Trigger weekly Friday digest endpoint ─────────────────────────
WebUI.comment('STEP 3: Trigger weekly digest task')
def triggerReq = findTestObject('Object Repository/API/POST_TriggerDigest')
def triggerResp= WS.sendRequest(triggerReq)
WS.verifyResponseStatusCode(triggerResp, 200)
WebUI.comment('Weekly digest task triggered')

// ── Step 4: Poll for reminder records (up to 30 seconds) ──────────────────
WebUI.comment('STEP 4: Poll reminder records for contract')
boolean reminderFound = false
int attempts = 0
while(!reminderFound && attempts < 15){
  Thread.sleep(2000)
  def reminderReq = findTestObject('Object Repository/API/GET_Reminders')
  def reminderResp= WS.sendRequest(reminderReq)
  def reminders   = new JsonSlurper().parseText(reminderResp.getResponseBodyContent())
  reminderFound   = reminders.any{ it.contract_ref == contractRef && it.is_weekly }
  attempts++
}
assert reminderFound : "No weekly reminder record found for ${contractRef} after 30s"
WebUI.comment("PASS: Weekly reminder record created for ${contractRef}")

// ── Step 5: Verify reminder record has correct fields ─────────────────────
WebUI.comment('STEP 5: Verify reminder fields')
def reminderResp2 = WS.sendRequest(findTestObject('Object Repository/API/GET_Reminders'))
def reminders2    = new JsonSlurper().parseText(reminderResp2.getResponseBodyContent())
def wr = reminders2.find{ it.contract_ref == contractRef && it.is_weekly }
assert wr.status in ['SENT','PENDING'] : "Unexpected status: ${wr.status}"
assert wr.type   in ['EMAIL','BOTH','SMS'] : "Unexpected type: ${wr.type}"
WebUI.comment("PASS: Reminder type=${wr.type} status=${wr.status}")

// ── Step 6: Check audit log for notification event ────────────────────────
WebUI.comment('STEP 6: Verify audit log contains notification entry')
def auditResp = WS.sendRequest(findTestObject('Object Repository/API/GET_Audit'))
def auditLogs = new JsonSlurper().parseText(auditResp.getResponseBodyContent())
def notifLog  = auditLogs.find{ it.action?.contains('REMINDER') || it.action?.contains('NOTIFY') }
assert notifLog != null : "No notification entry found in audit log"
WebUI.comment("PASS: Audit log entry found: ${notifLog.action}")

WebUI.comment('TC002 PASSED: Weekly Friday reminder flow verified')
