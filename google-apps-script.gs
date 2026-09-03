/**
 * Serene Lee website — lead capture webhook
 * ------------------------------------------
 * This script receives form submissions from sereneleeproperty.com (the main
 * calculator lead form AND the footer contact form) and appends each one
 * as a new row in this Google Sheet.
 *
 * SETUP (one-time):
 * 1. Create a new Google Sheet. Name it something like "Serene Lee Website Leads".
 * 2. In row 1, add these column headers (exact order matters for readability,
 *    not for the script — the script writes by position):
 *      Timestamp | Source | Name | Phone | Email | Best Time to Call |
 *      Est. Max Price | Est. Monthly Mortgage | Est. Cash Needed | Target Price |
 *      Property Type | Loan Type | Buyer Income | Buyer Age | Buyer Variable Income |
 *      Has Co-buyer | Co-buyer Income | Co-buyer Age | Co-buyer Variable Income |
 *      Buyer CPF OA | Co-buyer CPF OA | Car Loan | Other Debt | Cash on Hand |
 *      Loan Tenure (yrs) | Interest Rate (%) | LTV (%)
 *    (If you already have an older sheet with only the first 10 columns, just
 *    add these 17 extra headers starting at column K — new leads will fill
 *    them in going forward; existing rows won't be back-filled.)
 *    (There used to be a "Current HDB Price" column between "Cash on Hand" and
 *    "Loan Tenure" — the calculator no longer asks for that figure, so it was
 *    dropped from both the header list and the row data below. If your sheet
 *    still has that column, delete it so "Loan Tenure" lines back up.)
 * 3. In the Sheet, go to Extensions > Apps Script.
 * 4. Delete any placeholder code, paste this entire file in, and save
 *    (name the project "Serene Lee Leads Webhook" or similar).
 * 5. Click Deploy > New deployment.
 *    - Select type: "Web app"
 *    - Description: "Lead capture webhook"
 *    - Execute as: "Me"
 *    - Who has access: "Anyone"
 *    - Click Deploy, then "Authorize access" and approve the permissions
 *      (you'll see a Google warning screen for unverified apps — click
 *      "Advanced" > "Go to [project name] (unsafe)" — this is expected
 *      for a script you wrote yourself).
 * 6. Copy the "Web app URL" it gives you (ends in /exec).
 * 7. Paste that URL into index.html, in the line:
 *      const GAS_WEBHOOK_URL = "";
 *    so it reads:
 *      const GAS_WEBHOOK_URL = "https://script.google.com/macros/s/XXXXX/exec";
 * 8. Re-deploy the site (or just re-upload index.html) so the change goes live.
 *
 * NOTE ON CORS: the site calls this webhook using `mode: 'no-cors'`, which
 * means the browser can't read a response back — but the POST still reaches
 * this script and still gets written to the Sheet. This is the standard,
 * reliable pattern for a static site + Apps Script combo.
 *
 * If you ever change the form fields in index.html, update the appendRow()
 * order below to match.
 *
 * NOTE ON EMAIL NOTIFICATIONS: Google Sheets' own "Notification rules"
 * (Tools > Notification rules) will NOT email you for these rows, even if
 * you turn them on. That's because this script is deployed with
 * "Execute as: Me", so Sheets sees every row as an edit made by your own
 * account — and it never emails you for your own edits. So instead, this
 * script emails you directly every time a lead comes in (see the
 * MailApp.sendEmail call below). Change NOTIFY_EMAIL if you ever want the
 * alert sent somewhere else.
 *
 * NOTE ON THE PDF ATTACHMENT: when a lead comes from the affordability
 * calculator, the page sends along a base64 copy of the same PDF the visitor
 * just downloaded (data.pdfBase64 / data.pdfFilename). This script decodes
 * it and attaches it to your pre-alert email, so you get a copy of exactly
 * what they saw without needing to ask them for it. The footer contact form
 * doesn't generate a PDF, so those leads simply arrive with no attachment —
 * nothing to configure either way. The base64 text itself is NOT written to
 * the Sheet (it would make every row huge) — only the email gets it.
 */
const NOTIFY_EMAIL = 'serenelcc@gmail.com';

function doPost(e) {
  console.log('doPost CODE-CHECK v4 is running (build 30-Aug-D, dropped Current HDB Price column)');
  try {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    const data = JSON.parse(e.postData.contents);

    sheet.appendRow([
      new Date(),
      data.source || '',
      data.name || '',
      data.phone || '',
      data.email || '',
      data.bestTime || '',
      data.maxPrice || '',
      data.monthlyMortgage || '',
      data.cashNeeded || '',
      data.targetPrice || '',
      data.propertyType || '',
      data.loanType || '',
      data.buyerIncome || '',
      data.buyerAge || '',
      data.buyerVariableIncome || '',
      data.hasCobuyer || '',
      data.cobuyerIncome || '',
      data.cobuyerAge || '',
      data.cobuyerVariableIncome || '',
      data.buyerCpfOA || '',
      data.cobuyerCpfOA || '',
      data.carLoan || '',
      data.otherDebt || '',
      data.cashOnHand || '',
      data.loanTenureYears || '',
      data.interestRatePct || '',
      data.ltvPct || ''
    ]);

    sendLeadNotification(data);

    return ContentService
      .createTextOutput(JSON.stringify({ status: 'ok' }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: 'error', message: err.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function sendLeadNotification(data) {
  try {
    const subject = 'New website lead: ' + (data.name || 'Unknown name');
    const body = [
      'A new lead just came in from ' + (data.source || 'your website') + ':',
      '',
      'Name: ' + (data.name || '-'),
      'Phone: ' + (data.phone || '-'),
      'Email: ' + (data.email || '-'),
      'Best time to call: ' + (data.bestTime || '-'),
      'Topic: ' + (data.topic || '-'),
      '',
      'Calculator figures (if applicable):',
      'Est. Max Price: ' + (data.maxPrice || '-'),
      'Est. Monthly Mortgage: ' + (data.monthlyMortgage || '-'),
      'Est. Cash Needed: ' + (data.cashNeeded || '-'),
      'Target Price: ' + (data.targetPrice || '-'),
      '',
      'Open the Sheet to see the full log.'
    ].join('\n');

    const options = {};
    if (data.pdfBase64) {
      try {
        const pdfBlob = Utilities.newBlob(
          Utilities.base64Decode(data.pdfBase64),
          MimeType.PDF,
          data.pdfFilename || 'Affordability-Breakdown.pdf'
        );
        options.attachments = [pdfBlob];
      } catch (attachErr) {
        // Don't let a bad/oversized PDF block the email itself — it'll just
        // arrive without the attachment. Logged so it's visible in Executions.
        console.error('Could not attach PDF: ' + attachErr);
      }
    }

    console.log('Attempting MailApp.sendEmail now...');
    MailApp.sendEmail(NOTIFY_EMAIL, subject, body, options);
    console.log('MailApp.sendEmail returned with no error.');
  } catch (err) {
    // Don't let a notification failure block the lead from being saved —
    // the row above is already written even if this fails. Logged so it's
    // visible in Executions (View > Executions in the Apps Script editor).
    console.error('sendLeadNotification failed: ' + err);
  }
}

// Run this ONE TIME manually from the Apps Script editor (select "testEmail"
// in the function dropdown at the top, then click Run) to confirm mail
// permission is authorized. Unlike doPost, this is NOT wrapped in a
// try/catch, so if something is wrong, Apps Script will show you the real
// error directly instead of it being silently swallowed.
function testEmail() {
  MailApp.sendEmail(NOTIFY_EMAIL, 'Test email from your website script', 'If you got this, email sending is working.');
}

// Optional: lets you sanity-check the deployment by visiting the /exec URL
// directly in a browser — you should see {"status":"ready"}.
function doGet(e) {
  return ContentService
    .createTextOutput(JSON.stringify({ status: 'ready' }))
    .setMimeType(ContentService.MimeType.JSON);
}
