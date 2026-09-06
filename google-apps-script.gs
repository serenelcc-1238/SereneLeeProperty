/**
 * Serene Lee website — lead capture + blog subscriber webhook
 * -------------------------------------------------------------
 * ONE script, ONE Google Sheet, TWO tabs:
 *   - Tab 1 (your existing leads tab — whatever you've named it): website
 *     leads from the calculator, contact form and upgrade checklist.
 *     Unchanged in behavior from before, except it's now addressed by
 *     position (first tab) instead of "whichever tab happens to be open" —
 *     see the note above doPost for why that matters now that there are
 *     two tabs in this Sheet.
 *   - Tab 2 ("Subscribers", created automatically the first time someone
 *     subscribes on the blog): blog subscriber emails, used by the
 *     "📧 Blog Broadcast" menu at the bottom of this file.
 *
 * Both flows share the SAME Web App URL — the one already pasted into
 * calculator.html, contact.html and upgrade-checklist.html. The blog's
 * Subscribe form (main.js) posts to that same URL with formType: "subscribe",
 * which is how this script tells the two kinds of submission apart.
 *
 * SETUP (one-time, updating your EXISTING Apps Script project — the one
 * already deployed at the URL used by calculator.html / contact.html /
 * upgrade-checklist.html):
 * 1. Open that Google Sheet → Extensions > Apps Script.
 * 2. Select all the existing code in Code.gs and replace it with this
 *    entire file.
 * 3. Click the "+" next to "Files" → "HTML" → name the new file exactly
 *    SendDialog (Apps Script adds the .html itself). Paste in the contents
 *    of SendDialog.html (in this same delivery) and save.
 * 4. Deploy > Manage deployments > click the pencil (edit) icon on your
 *    existing deployment > under "Version" choose "New version" > Deploy.
 *    This keeps the SAME Web App URL, so calculator.html, contact.html and
 *    upgrade-checklist.html need no changes at all.
 * 5. Reload the Google Sheet tab in your browser (so the new
 *    "📧 Blog Broadcast" menu appears at the top).
 * That's it — no new URL, no changes needed anywhere else on the site.
 *
 * NOTE ON CORS: the site calls this webhook using `mode: 'no-cors'`, which
 * means the browser can't read a response back — but the POST still reaches
 * this script and still gets written to the Sheet. This is the standard,
 * reliable pattern for a static site + Apps Script combo.
 *
 * If you ever change the form fields in index.html/calculator.html/etc,
 * update the appendRow() order below to match.
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
const SUBSCRIBERS_SHEET_NAME = 'Subscribers';
const SENDER_NAME = 'Serene Lee, ERA Realty';

/* IMPORTANT: leads are written to the FIRST tab of this spreadsheet by
   POSITION (Sheets[0]), not "whichever tab is currently open" (the old
   getActiveSheet() approach). That distinction didn't matter when this
   Sheet only had one tab — now that a second "Subscribers" tab exists,
   getActiveSheet() would silently write leads into whichever tab you
   happen to be looking at, which is why this was changed. Your leads tab
   stays tab 1 no matter what you're viewing when a lead comes in. */
function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);

    if (data.formType === 'subscribe') {
      return handleSubscribe(data);
    }

    console.log('doPost CODE-CHECK v4 is running (build 30-Aug-D, dropped Current HDB Price column)');
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];

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

// Sanity-check the deployment by visiting the /exec URL directly in a
// browser — you should see {"status":"ready"}. Also handles the
// unsubscribe link inside every blog broadcast email (?unsubscribe=TOKEN).
function doGet(e) {
  const token = e.parameter.unsubscribe;
  if (token) {
    const sheet = getSubscribersSheet();
    const rows = sheet.getDataRange().getValues();
    for (let i = 1; i < rows.length; i++) {
      if (rows[i][4] === token) {
        sheet.getRange(i + 1, 4).setValue('unsubscribed');
        return HtmlService.createHtmlOutput(
          wrapHtml("You've been unsubscribed. You won't receive any further blog updates from Serene Lee.")
        );
      }
    }
    return HtmlService.createHtmlOutput(wrapHtml('Link not found, or already unsubscribed.'));
  }

  return ContentService
    .createTextOutput(JSON.stringify({ status: 'ready' }))
    .setMimeType(ContentService.MimeType.JSON);
}

/* =========================================================================
   BLOG SUBSCRIBERS — Tab 2 of this same Sheet
   ========================================================================= */

/* ---------- Website signup (POST from the blog's Subscribe form) ---------- */
function handleSubscribe(data) {
  try {
    const email = (data.email || '').toString().trim().toLowerCase();

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return jsonOutput({ ok: false, error: 'invalid email' });
    }

    const sheet = getSubscribersSheet();
    const rows = sheet.getDataRange().getValues();

    for (let i = 1; i < rows.length; i++) {
      if ((rows[i][1] || '').toString().toLowerCase() === email) {
        // Already on the list — if they'd unsubscribed before, welcome them back.
        sheet.getRange(i + 1, 4).setValue('active');
        return jsonOutput({ ok: true, existing: true });
      }
    }

    const token = Utilities.getUuid();
    sheet.appendRow([new Date(), email, data.source || '', 'active', token]);
    return jsonOutput({ ok: true });

  } catch (err) {
    return jsonOutput({ ok: false, error: err.message });
  }
}

function wrapHtml(message) {
  return '<div style="font-family:Arial,sans-serif;max-width:480px;margin:60px auto;text-align:center;color:#182430;">' +
    '<p style="font-size:16px;">' + message + '</p></div>';
}

function jsonOutput(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

/* ---------- Tab 2 itself — created automatically on first subscribe ---------- */
function getSubscribersSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(SUBSCRIBERS_SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SUBSCRIBERS_SHEET_NAME);
    sheet.appendRow(['Timestamp', 'Email', 'Source', 'Status', 'UnsubToken']);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function getActiveSubscriberCount() {
  const sheet = getSubscribersSheet();
  const rows = sheet.getDataRange().getValues();
  return rows.slice(1).filter(function (r) { return r[3] === 'active'; }).length;
}

/* ---------- The "📧 Blog Broadcast" menu + button ---------- */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('📧 Blog Broadcast')
    .addItem('Send New Post to Subscribers', 'showSendDialog')
    .addToUi();
}

function showSendDialog() {
  const html = HtmlService.createHtmlOutputFromFile('SendDialog')
    .setWidth(480)
    .setHeight(460);
  SpreadsheetApp.getUi().showModalDialog(html, 'Send New Post to Subscribers');
}

/* Called by the dialog's "Send to All Subscribers" button. */
function sendBroadcast(payload) {
  const sheet = getSubscribersSheet();
  const rows = sheet.getDataRange().getValues();
  const webAppUrl = ScriptApp.getService().getUrl();
  let sent = 0;

  for (let i = 1; i < rows.length; i++) {
    const email = rows[i][1];
    const status = rows[i][3];
    const token = rows[i][4];
    if (status !== 'active' || !email) continue;

    const unsubUrl = webAppUrl + '?unsubscribe=' + token;
    MailApp.sendEmail({
      to: email,
      subject: payload.subject,
      htmlBody: buildEmailHtml(payload, unsubUrl),
      name: SENDER_NAME
    });
    sent++;
    Utilities.sleep(200); // gentle pacing, well inside Gmail's daily quota
  }
  return sent;
}

function buildEmailHtml(payload, unsubUrl) {
  return '' +
    '<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#182430;">' +
    '  <p style="font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:#a9841a;font-weight:bold;margin:0 0 6px;">New Guide from Serene Lee</p>' +
    '  <h2 style="color:#0b2a4a;margin:0 0 14px;">' + escapeHtml(payload.title) + '</h2>' +
    '  <p style="line-height:1.6;font-size:14px;">' + escapeHtml(payload.excerpt) + '</p>' +
    '  <p style="margin:24px 0;">' +
    '    <a href="' + payload.url + '" style="background:#c9a227;color:#0b2a4a;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;display:inline-block;font-size:14px;">Read the Full Guide &rarr;</a>' +
    '  </p>' +
    '  <hr style="border:none;border-top:1px solid #e6e2d8;margin:30px 0 16px;">' +
    '  <p style="font-size:12px;color:#5c6b78;line-height:1.6;">' +
    '    Serene Lee &middot; ERA Realty Network Pte Ltd &middot; CEA Registration No. R027578Z<br>' +
    '    <a href="' + unsubUrl + '" style="color:#5c6b78;">Unsubscribe from these emails</a>' +
    '  </p>' +
    '</div>';
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
