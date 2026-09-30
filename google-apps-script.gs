/**
 * Serene Lee website — lead capture + blog subscriber webhook + email nurture + referrals
 * -------------------------------------------------------------
 * This is a COPY of the script that runs inside the "Serene Lee Website Leads"
 * Google Sheet (Extensions > Apps Script). The live version is the one in Google;
 * keep this copy in step with it when either changes.
 *
 * ⚠ SECRETS: this repository is PUBLIC. The real Telegram bot token is only in
 * the Google copy — here it is a placeholder. Never paste the real token into
 * this file. (If you copy this whole file into Google, put the real token back.)
 *
 * ONE script, ONE Google Sheet, THREE tabs:
 *   - Tab 1 (your existing leads tab — whatever you've named it): website
 *     leads from the calculator, contact form and upgrade checklist.
 *     Unchanged in behavior from before, except it's now addressed by
 *     position (first tab) instead of "whichever tab happens to be open" —
 *     see the note above doPost for why that matters now that there are
 *     several tabs in this Sheet.
 *   - "Subscribers" (created automatically the first time someone
 *     subscribes): subscriber emails, used by the "📧 Blog Broadcast" menu
 *     at the bottom of this file.
 *   - "Referrals" (created automatically on the first referral): the
 *     "Refer someone" form on subscribers.html (formType: "referral").
 *
 * All flows share the SAME Web App URL — the one already pasted into
 * calculator.html, contact.html, upgrade-checklist.html and main.js.
 * The forms tell this script apart by formType ("subscribe", "referral",
 * or none for leads).
 *
 * NEW — EMAIL NURTURE AUTOMATION (Sep 2026):
 * Any lead that includes an email address (in practice: Calculator leads,
 * and occasionally chatbot leads) now gets a 3-email nurture sequence:
 *   Email 1 — sent immediately: recap of their numbers.
 *   Email 2 — sent 2 days later, IF they haven't been marked Contacted/
 *             Converted yet: a helpful follow-up + soft nudge.
 *   Email 3 — sent 4 days after that, IF still not marked: a warmer,
 *             more direct WhatsApp nudge. Sequence then marks itself done.
 * The moment you type "Contacted" or "Converted" into that lead's
 * "Nurture Status" column, the sequence stops sending to them — so you
 * never have an automated email cross paths with a conversation you're
 * already having.
 *
 * This runs off a genuinely new function, runEmailNurture(), which needs
 * ONE new trigger set up (see step 4 below) — everything else in this file
 * (leads, subscribers, Telegram, blog broadcast) behaves exactly as before.
 *
 * SETUP (updating your EXISTING Apps Script project — the one already
 * deployed at the URL used by calculator.html / contact.html /
 * upgrade-checklist.html):
 * 1. Open that Google Sheet → Extensions > Apps Script.
 * 2. Select all the existing code in Code.gs and replace it with this
 *    entire file — then put your real Telegram bot token back in
 *    TELEGRAM_BOT_TOKEN below.
 * 3. On your LEADS tab (tab 1), add three new header labels at the end of
 *    row 1 (purely for your own readability — the script itself uses
 *    column position, not the header text): "Nurture Stage",
 *    "Next Send Date", "Nurture Status".
 * 4. In the Apps Script editor, click the clock icon ("Triggers") on the
 *    left sidebar → "+ Add Trigger" → Function: runEmailNurture →
 *    Event source: Time-driven → Type: Day timer → pick any time window
 *    (e.g. 9am–10am) → Save. You'll be asked to re-authorize — that's
 *    expected (same as the first time you ran this script).
 * 5. Deploy > Manage deployments > pencil icon on your existing deployment
 *    > Version: "New version" > Deploy. Keeps the SAME Web App URL, so
 *    nothing on the site itself needs to change.
 * 6. Optional: run previewNurtureEmailsToMe() once manually (function
 *    dropdown at the top > select it > Run) to get all 3 emails sent to
 *    yourself, so you can see exactly what a lead will receive before any
 *    real lead does.
 *
 * NOTE ON CORS: the site calls this webhook using `mode: 'no-cors'`, which
 * means the browser can't read a response back — but the POST still reaches
 * this script and still gets written to the Sheet. This is the standard,
 * reliable pattern for a static site + Apps Script combo.
 *
 * If you ever change the form fields in index.html/calculator.html/etc,
 * update the appendRow() order below to match — and keep the 3 new nurture
 * columns as the LAST three values in that same array.
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
const TELEGRAM_BOT_TOKEN = 'PASTE_REAL_TOKEN_IN_GOOGLE_ONLY'; // real value lives only in the Google copy — never commit it
const TELEGRAM_CHAT_ID = '1016354859';

// Leads tab (tab 1) column positions, 1-indexed — must match the appendRow()
// order in doPost below. The last three are the new nurture-tracking columns.
const LEAD_COL = {
  TIMESTAMP: 1, SOURCE: 2, NAME: 3, PHONE: 4, EMAIL: 5, BEST_TIME: 6,
  MAX_PRICE: 7, MONTHLY_MORTGAGE: 8, CASH_NEEDED: 9, TARGET_PRICE: 10,
  NURTURE_STAGE: 28, NEXT_SEND_DATE: 29, NURTURE_STATUS: 30
};

const NURTURE_WAIT_DAYS = { AFTER_EMAIL_1: 2, AFTER_EMAIL_2: 4 };
const NURTURE_STOP_STATUSES = ['Contacted', 'Converted', 'Stopped', 'Sequence Complete'];

/* IMPORTANT: leads are written to the FIRST tab of this spreadsheet by
   POSITION (Sheets[0]), not "whichever tab is currently open" (the old
   getActiveSheet() approach). That distinction didn't matter when this
   Sheet only had one tab — now that other tabs exist, getActiveSheet()
   would silently write leads into whichever tab you happen to be looking
   at, which is why this was changed. Your leads tab stays tab 1 no matter
   what you're viewing when a lead comes in. */
function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);

    if (data.formType === 'subscribe') {
      return handleSubscribe(data);
    }

    if (data.formType === 'referral') {
      return handleReferral(data);
    }

    console.log('doPost CODE-CHECK v5 is running (build 10-Sep-A, added email nurture automation)');
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];

    const hasEmail = !!(data.email && data.email.toString().trim());
    const now = new Date();

    sheet.appendRow([
      now,
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
      data.ltvPct || '',
      hasEmail ? 0 : '',       // Nurture Stage — 0 = "Email 1 not sent yet"
      hasEmail ? now : '',     // Next Send Date — due immediately
      ''                       // Nurture Status — blank until you mark it
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
    sendTelegramNotification(
      '🏠 New lead: ' + (data.name || 'Unknown') + '\n' +
      'Source: ' + (data.source || 'website') + '\n' +
      'Phone: ' + (data.phone || '-') + '\n' +
      'Email: ' + (data.email || '-') + '\n' +
      'Topic: ' + (data.topic || '-')
    );
  } catch (err) {
    // Don't let a notification failure block the lead from being saved —
    // the row above is already written even if this fails. Logged so it's
    // visible in Executions (View > Executions in the Apps Script editor).
    console.error('sendLeadNotification failed: ' + err);
  }
}

function sendTelegramNotification(text) {
  try {
    const url = 'https://api.telegram.org/bot' + TELEGRAM_BOT_TOKEN + '/sendMessage';
    UrlFetchApp.fetch(url, {
      method: 'post',
      contentType: 'application/x-www-form-urlencoded',
      payload: {
        chat_id: TELEGRAM_CHAT_ID,
        text: text
      },
      muteHttpExceptions: true
    });
  } catch (err) {
    console.error('sendTelegramNotification failed: ' + err);
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

/* =========================================================================
   EMAIL NURTURE AUTOMATION — runs once a day via a time-driven trigger
   (Triggers > + Add Trigger > runEmailNurture > Time-driven > Day timer)
   ========================================================================= */

// The daily job: find leads due for their next nurture email, send it, and
// schedule (or close out) the next step.
function runEmailNurture() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return; // no leads yet, nothing to do

  const numCols = LEAD_COL.NURTURE_STATUS;
  const range = sheet.getRange(2, 1, lastRow - 1, numCols);
  const rows = range.getValues();
  const now = new Date();

  rows.forEach(function (row, idx) {
    const sheetRow = idx + 2; // +2: skip header row, and getValues() is 0-indexed
    const email = (row[LEAD_COL.EMAIL - 1] || '').toString().trim();
    const status = (row[LEAD_COL.NURTURE_STATUS - 1] || '').toString();
    const stage = Number(row[LEAD_COL.NURTURE_STAGE - 1]) || 0;
    const nextSendRaw = row[LEAD_COL.NEXT_SEND_DATE - 1];

    if (!email) return; // no email on this lead — nothing to nurture
    if (NURTURE_STOP_STATUSES.indexOf(status) !== -1) return; // already contacted/converted/stopped
    if (stage >= 3) return; // sequence already finished
    if (!nextSendRaw) return; // shouldn't happen, but guard anyway
    if (new Date(nextSendRaw).getTime() > now.getTime()) return; // not due yet

    const name = (row[LEAD_COL.NAME - 1] || '').toString().trim() || 'there';
    const maxPrice = row[LEAD_COL.MAX_PRICE - 1];

    let subject, html, waitDays;
    if (stage === 0) {
      subject = 'Your affordability numbers, recapped';
      html = nurtureEmail1Html(name, maxPrice);
      waitDays = NURTURE_WAIT_DAYS.AFTER_EMAIL_1;
    } else if (stage === 1) {
      subject = "Thinking it over? Here's what most upgraders ask next";
      html = nurtureEmail2Html(name);
      waitDays = NURTURE_WAIT_DAYS.AFTER_EMAIL_2;
    } else {
      subject = 'Ready when you are, ' + name;
      html = nurtureEmail3Html(name);
      waitDays = null;
    }

    try {
      MailApp.sendEmail({ to: email, subject: subject, htmlBody: html, name: SENDER_NAME });
    } catch (err) {
      console.error('runEmailNurture: failed to email ' + email + ': ' + err);
      return; // leave stage/next-send untouched so it retries tomorrow
    }

    sheet.getRange(sheetRow, LEAD_COL.NURTURE_STAGE).setValue(stage + 1);
    if (waitDays !== null) {
      const next = new Date(now.getTime() + waitDays * 24 * 60 * 60 * 1000);
      sheet.getRange(sheetRow, LEAD_COL.NEXT_SEND_DATE).setValue(next);
    } else {
      sheet.getRange(sheetRow, LEAD_COL.NURTURE_STATUS).setValue('Sequence Complete');
    }
  });
}

function emailWrapper(innerHtml) {
  return '' +
    '<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#182430;">' +
    innerHtml +
    '  <hr style="border:none;border-top:1px solid #e6e2d8;margin:30px 0 16px;">' +
    '  <p style="font-size:12px;color:#5c6b78;line-height:1.6;">' +
    '    Serene Lee &middot; ERA Realty Network Pte Ltd &middot; CEA Registration No. R027578Z' +
    '  </p>' +
    '</div>';
}

function nurtureEmail1Html(name, maxPrice) {
  const priceLine = maxPrice
    ? '<p style="line-height:1.6;font-size:14px;">Based on what you entered, your estimated max purchase price was around <strong>' + escapeHtml(maxPrice.toString()) + '</strong>. That\'s a starting point, not a rule — happy to walk through it together if useful.</p>'
    : '';
  return emailWrapper(
    '  <h2 style="color:#0b2a4a;margin:0 0 14px;">Hi ' + escapeHtml(name) + ', here\'s your recap</h2>' +
    '  <p style="line-height:1.6;font-size:14px;">Thanks for running the numbers on the Affordability Calculator. No pressure at all — just wanted to make sure you have this recap in your inbox, not just on a page you might not revisit.</p>' +
    priceLine +
    '  <p style="margin:24px 0;">' +
    '    <a href="https://wa.me/6580868568" style="background:#c9a227;color:#0b2a4a;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;display:inline-block;font-size:14px;">Ask Serene a Question on WhatsApp &rarr;</a>' +
    '  </p>'
  );
}

function nurtureEmail2Html(name) {
  return emailWrapper(
    '  <h2 style="color:#0b2a4a;margin:0 0 14px;">Hi ' + escapeHtml(name) + '</h2>' +
    '  <p style="line-height:1.6;font-size:14px;">A couple of things HDB upgraders usually want to think through next, in case they\'re useful:</p>' +
    '  <ul style="line-height:1.8;font-size:14px;">' +
    '    <li><a href="https://sereneleeproperty.com/blog-sell-hdb-or-buy-condo-first.html" style="color:#0b2a4a;">Sell HDB or Buy Condo First? Here\'s How to Decide</a></li>' +
    '    <li><a href="https://sereneleeproperty.com/upgrade-checklist.html" style="color:#0b2a4a;">The 2-minute HDB Upgrader Checklist</a> — see your Upgrade Readiness Score</li>' +
    '  </ul>' +
    '  <p style="line-height:1.6;font-size:14px;">If it\'s easier to just talk it through, I\'m one WhatsApp message away.</p>' +
    '  <p style="margin:24px 0;">' +
    '    <a href="https://wa.me/6580868568" style="background:#c9a227;color:#0b2a4a;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;display:inline-block;font-size:14px;">WhatsApp Serene &rarr;</a>' +
    '  </p>'
  );
}

function nurtureEmail3Html(name) {
  return emailWrapper(
    '  <h2 style="color:#0b2a4a;margin:0 0 14px;">Hi ' + escapeHtml(name) + ', still here if you need me</h2>' +
    '  <p style="line-height:1.6;font-size:14px;">Most upgraders find a short WhatsApp chat clears up more than the numbers alone can — no obligation, and no scripted sales pitch, just a straight answer to whatever\'s on your mind.</p>' +
    '  <p style="margin:24px 0;">' +
    '    <a href="https://wa.me/6580868568" style="background:#c9a227;color:#0b2a4a;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;display:inline-block;font-size:14px;">Chat with Serene on WhatsApp &rarr;</a>' +
    '  </p>' +
    '  <p style="line-height:1.6;font-size:12px;color:#5c6b78;">This is the last email in this series — no more follow-ups unless you reach out.</p>'
  );
}

// Run this ONE TIME manually (function dropdown at top > select it > Run) to
// send all 3 nurture emails to yourself, so you can see exactly what a lead
// receives before any real lead does.
function previewNurtureEmailsToMe() {
  MailApp.sendEmail({ to: NOTIFY_EMAIL, subject: '[PREVIEW] Your affordability numbers, recapped', htmlBody: nurtureEmail1Html('Alex', '$850,000'), name: SENDER_NAME });
  MailApp.sendEmail({ to: NOTIFY_EMAIL, subject: "[PREVIEW] Thinking it over? Here's what most upgraders ask next", htmlBody: nurtureEmail2Html('Alex'), name: SENDER_NAME });
  MailApp.sendEmail({ to: NOTIFY_EMAIL, subject: '[PREVIEW] Ready when you are, Alex', htmlBody: nurtureEmail3Html('Alex'), name: SENDER_NAME });
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
   BLOG SUBSCRIBERS — "Subscribers" tab of this same Sheet
   ========================================================================= */

/* ---------- Website signup (POST from the Subscribe form) ---------- */
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
    sendTelegramNotification(
      '📧 New subscriber: ' + email + '\n' +
      'Source: ' + (data.source || 'website')
    );
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

/* ---------- Subscribers tab — created automatically on first subscribe ---------- */
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

/* ---------- Referrals (subscribers page "Refer someone" form) ----------
   Each referral becomes a row in a "Referrals" tab (created automatically on
   the first referral), and Serene gets an email alert, like a lead. */
const REFERRALS_SHEET_NAME = 'Referrals';

function handleReferral(data) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(REFERRALS_SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(REFERRALS_SHEET_NAME);
    sheet.appendRow([
      'Timestamp', 'Referred by', 'Referrer phone / email', 'Friend name', 'Friend phone',
      'Friend email', 'Looking to', 'Notes', 'Consent confirmed', 'Page', 'Status'
    ]);
    sheet.setFrozenRows(1);
  }

  // A leading = + - @ would make Sheets treat typed text as a formula.
  const clean = (v) => {
    const s = String(v || '').trim().slice(0, 500);
    return /^[=+\-@]/.test(s) ? "'" + s : s;
  };

  sheet.appendRow([
    new Date(),
    clean(data.referrerName),
    clean(data.referrerContact),
    clean(data.friendName),
    clean(data.friendPhone),
    clean(data.friendEmail),
    clean(data.lookingTo),
    clean(data.notes),
    data.consent ? 'Yes' : 'No',
    clean(data.page),
    'New'
  ]);

  try {
    MailApp.sendEmail(
      NOTIFY_EMAIL,
      'New referral: ' + (data.friendName || 'Unknown') + ' (from ' + (data.referrerName || 'unknown') + ')',
      [
        'A new referral just came in from your Subscribers page:',
        '',
        'Referred by: ' + (data.referrerName || '-') + ' (' + (data.referrerContact || '-') + ')',
        '',
        'Friend: ' + (data.friendName || '-'),
        'Phone: ' + (data.friendPhone || '-'),
        'Email: ' + (data.friendEmail || '-'),
        'Looking to: ' + (data.lookingTo || '-'),
        'Notes: ' + (data.notes || '-'),
        '',
        'The referrer confirmed the friend agreed to be contacted: ' + (data.consent ? 'Yes' : 'No'),
        '',
        'Open the Sheet (Referrals tab) to see the full list.'
      ].join('\n')
    );
  } catch (err) {
    console.error('Referral email failed: ' + err); // the row is already saved
  }

  sendTelegramNotification(
    '🤝 New referral: ' + (data.friendName || 'Unknown') + '\n' +
    'Phone: ' + (data.friendPhone || '-') + '\n' +
    'Looking to: ' + (data.lookingTo || '-') + '\n' +
    'Referred by: ' + (data.referrerName || '-') + ' (' + (data.referrerContact || '-') + ')' +
    (data.notes ? '\nNotes: ' + data.notes : '')
  );

  return ContentService
    .createTextOutput(JSON.stringify({ status: 'ok' }))
    .setMimeType(ContentService.MimeType.JSON);
}
