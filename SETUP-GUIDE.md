# Blog Subscriber System — Setup Guide (updated: reuses your existing Leads Sheet)

Good news — this no longer needs a new Google Sheet or a new Web App URL. It plugs into the SAME Apps Script project that already powers your calculator, contact form, and upgrade checklist leads. The subscriber list just becomes a second tab ("Subscribers") in that same Google Sheet.

**How it works once set up:**
1. Someone enters their email on sereneleeproperty.com (currently the subscribe box on the homepage) → it's saved as a new row in the **Subscribers** tab of your existing Leads Sheet.
2. You publish a new blog post as usual.
3. You open that same Google Sheet, click **📧 Blog Broadcast → Send New Post to Subscribers**, fill in the post details, and click Send.
4. Everyone active on the list gets an email with a "Read the Full Guide" button and an unsubscribe link.

Your website code (`main.js`) has already been updated to point at your existing Web App URL — you only need to update the Apps Script project itself. Do the steps below in order; they only need to be done once.

---

## Step 1 — Open your existing Apps Script project

1. Open the Google Sheet that already collects your calculator/contact/checklist leads.
2. Click **Extensions → Apps Script**. This opens the SAME project already deployed at the URL used by `calculator.html`, `contact.html`, and `upgrade-checklist.html`.

## Step 2 — Replace the code

1. Open **google-apps-script.gs** (in the main site delivery, not this folder) on your computer, select all, and copy it.
2. In the Apps Script editor, select all the existing code in **Code.gs** and paste over it with the new version.
3. Click the **+** next to "Files" → **HTML** → name the new file exactly `SendDialog` (Apps Script adds the `.html` itself).
4. Open **SendDialog.html** (in this same folder) on your computer, copy its entire contents, and paste it into that new file.
5. Click the save icon (or Ctrl/Cmd+S).

## Step 3 — Redeploy (keeps the same URL)

1. Top-right of the Apps Script editor: **Deploy → Manage deployments**.
2. Click the pencil (edit) icon on your existing deployment.
3. Under "Version," choose **New version**.
4. Click **Deploy**.
5. If Google asks you to re-authorize permissions, click through "Advanced" → "Go to (your project name) (unsafe)" — expected for your own script.

That's it — the Web App URL stays exactly the same, so nothing on your website needs to change. The subscribe box on your homepage should now work immediately.

## Step 4 — Reload the Sheet

Reload the Google Sheet tab in your browser once, so the new **📧 Blog Broadcast** menu appears at the top. The first time someone subscribes, a new tab named **Subscribers** will appear automatically in that Sheet — you don't need to create it yourself.

---

## Using it for every new post

Once it's live, sending an update takes under a minute:

1. Publish your new blog post as usual (upload the `.html` file, add it to `blog.html`).
2. Open your Leads Google Sheet.
3. Click the menu **📧 Blog Broadcast → Send New Post to Subscribers**. *(If you don't see this menu, refresh the Sheet tab — it only appears after the page fully reloads.)*
4. Fill in:
   - **Post title** — e.g. the H1 of your post
   - **Post URL** — the full link, e.g. `https://sereneleeproperty.com/blog-post-....html`
   - **Short teaser** — 1–2 sentences, this is what people read in the email
   - **Email subject line** — what shows in their inbox
5. Click **Send to All Subscribers**. You'll see a confirmation with how many people it went to.

## Where your subscriber list lives

It's the **Subscribers** tab in your existing Leads Sheet (tab 2) — columns are Timestamp, Email, Source, Status, and an internal unsubscribe token. `Status` is either `active` or `unsubscribed`; unsubscribes happen automatically when someone clicks the link in an email, so you don't need to manage that yourself. You can freely read/export this tab, but avoid editing the `UnsubToken` column — that's what makes each person's unsubscribe link work.

Your original leads tab (calculator/contact/checklist) is unaffected — it stays tab 1, and the updated script now always writes leads there by position rather than "whichever tab is currently open," so it can't accidentally get mixed up with the new Subscribers tab even if you're viewing that tab when a lead comes in.

## Good to know / limits

- **Sending limit:** a free Gmail/Google Workspace account can send roughly 100 emails a day through Apps Script (Workspace paid accounts get more). Fine for anything up to a few dozen subscribers per post; if your list grows past that, let me know and we can revisit moving to a proper email platform (Mailchimp, Brevo, MailerLite, etc.).
- **Deliverability:** emails send from your own Gmail address, so they land in regular inboxes rather than a marketing-tool "campaigns" address — good for open rates at this scale, but there's no bounce/spam-complaint handling like a dedicated email platform would give you.
- **This is intentionally simple.** No signup confirmation email, no analytics dashboard, no list segmentation. If you want any of that later, it's a reasonable next step up rather than something to bolt onto this.
