/**
 * TC001 — User Login with Valid Credentials
 * Katalon Studio Test Case (Groovy DSL)
 * Tests: Signup → Login → Dashboard access → Logout
 * Covers mTLS certificate detection, session creation, redirect.
 */
import static com.kms.katalon.core.checkpoint.CheckpointFactory.findCheckpoint
import static com.kms.katalon.core.testcase.TestCaseFactory.findTestCase
import static com.kms.katalon.core.testdata.TestDataFactory.findTestData
import static com.kms.katalon.core.testobject.ObjectRepository.findTestObject
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI
import com.kms.katalon.core.webservice.keyword.WSBuiltInKeywords as WS
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.model.FailureHandling

// ── Test Data ─────────────────────────────────────────────────────────────
def BASE_URL   = GlobalVariable.BASE_URL ?: 'http://localhost:5000'
def TEST_EMAIL = 'tc001_test@cms.test'
def TEST_PW    = 'TestPass2024!'
def TEST_NAME  = 'Test User TC001'

// ── Step 1: Signup new user ────────────────────────────────────────────────
WebUI.comment('STEP 1: Create test user via signup API')
def signupReq = findTestObject('Object Repository/API/POST_Signup')
signupReq.setBodyContent("""
{
  "full_name":   "${TEST_NAME}",
  "email":       "${TEST_EMAIL}",
  "password":    "${TEST_PW}",
  "department":  "QA",
  "phone":       "+250788000001"
}
""")
def signupResp = WS.sendRequest(signupReq)
WS.verifyResponseStatusCode(signupResp, 200)
def signupBody = WS.getElementPropertyValue(signupResp, 'status')
assert signupBody == 'ok' : "Signup failed: expected status=ok"
WebUI.comment("PASS: User ${TEST_EMAIL} created")

// ── Step 2: Open Login page ────────────────────────────────────────────────
WebUI.comment('STEP 2: Open login page')
WebUI.openBrowser("${BASE_URL}/auth/login")
WebUI.waitForPageLoad(10)
WebUI.verifyElementPresent(findTestObject('Page_Login/input_email'), 10)

// ── Step 3: Enter credentials ──────────────────────────────────────────────
WebUI.comment('STEP 3: Enter email and password')
WebUI.setText(findTestObject('Page_Login/input_email'),    TEST_EMAIL)
WebUI.setText(findTestObject('Page_Login/input_password'), TEST_PW)

// ── Step 4: Check mTLS badge ───────────────────────────────────────────────
WebUI.comment('STEP 4: Verify mTLS status badge is visible')
WebUI.verifyElementPresent(findTestObject('Page_Login/mtls_status'), 5,
    FailureHandling.OPTIONAL)

// ── Step 5: Submit login ───────────────────────────────────────────────────
WebUI.comment('STEP 5: Submit login form')
WebUI.click(findTestObject('Page_Login/btn_submit'))
WebUI.waitForPageLoad(10)

// ── Step 6: Verify redirect to dashboard ──────────────────────────────────
WebUI.comment('STEP 6: Verify dashboard loads')
WebUI.verifyCurrentUrl("${BASE_URL}/dashboard/")
WebUI.verifyElementPresent(findTestObject('Page_Dashboard/kpi_total'), 10)

// ── Step 7: Verify KPIs rendered ──────────────────────────────────────────
WebUI.comment('STEP 7: Verify KPI cards are populated')
WebUI.waitForElementNotHasAttribute(findTestObject('Page_Dashboard/kpi_total'), 'data-loading', 10)
String kpiText = WebUI.getText(findTestObject('Page_Dashboard/kpi_total'))
assert kpiText != '—' : "KPI total should be loaded, got: ${kpiText}"

// ── Step 8: Logout ─────────────────────────────────────────────────────────
WebUI.comment('STEP 8: Logout')
WebUI.click(findTestObject('Page_Dashboard/btn_logout'))
WebUI.waitForPageLoad(5)
WebUI.verifyCurrentUrl("${BASE_URL}/auth/login")

// ── Step 9: Verify session cleared ────────────────────────────────────────
WebUI.comment('STEP 9: Confirm dashboard is inaccessible after logout')
WebUI.navigateToUrl("${BASE_URL}/dashboard/")
WebUI.waitForPageLoad(5)
WebUI.verifyCurrentUrl("${BASE_URL}/auth/login")

WebUI.comment('TC001 PASSED: Full login/logout flow verified')
WebUI.closeBrowser()
