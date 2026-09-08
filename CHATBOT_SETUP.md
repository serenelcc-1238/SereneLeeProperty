# Setting up your website chatbot

Your site now has an AI chat widget (the navy bubble, bottom-left corner — WhatsApp stays bottom-right). It answers visitor questions about HDB/condo buying, selling, renting, MOP, ABSD, financing, etc., points them to your calculator/new-launches/FAQ pages, and captures leads into your existing Google Sheet, tagged `source: chatbot`.

It needs one thing from you before it goes live: an Anthropic API key. Follow these steps.

## 1. Create an Anthropic account and get an API key

1. Go to **console.anthropic.com** and sign up (or log in).
2. In the left sidebar, click **API Keys**.
3. Click **Create Key**, give it a name like `sereneleeproperty-chatbot`, and copy the key immediately — it's only shown once. It looks like `sk-ant-api03-...`.
4. Click **Billing** in the left sidebar and add a payment method + top up credit (start with $5–10 — see cost estimate below).

## 2. Add the key to Cloudflare Pages

1. Log into your **Cloudflare dashboard** → **Workers & Pages** → click your `sereneleeproperty` project.
2. Go to **Settings** → **Environment variables**.
3. Under **Production**, click **Add variable**:
   - Variable name: `ANTHROPIC_API_KEY`
   - Value: paste the key from step 1
   - Click the **Encrypt** toggle so it's stored as a Secret (not plain text).
4. Click **Save**.
5. (Optional) Add a second variable `ANTHROPIC_MODEL` if you ever want to swap models later — leave it out for now, it defaults to a fast, low-cost model that's plenty capable for FAQ-style answers.
6. Cloudflare will prompt you to **redeploy** for the new variable to take effect — go ahead and redeploy (or it applies automatically on your next file upload).

## 3. Upload the new/changed files

Everything you need is in the zip I've sent — upload these into your GitHub repo (`SereneLeeProperty`) the same way you've been doing:

- `functions/api/chat.js` — **new file**, new folder structure (`functions/api/`)
- `chatbot.js` — new file
- `styles.css` — updated (added chat widget styling at the bottom, nothing else touched)
- All 13 `.html` pages — one line added to each (`<script src="chatbot.js"></script>`, right after the existing `main.js` line)

Cloudflare Pages auto-detects the `functions/` folder and deploys it as a serverless backend — no extra setup needed there.

## 4. Test it live

Once deployed and the API key is set:
1. Visit your live site, click the navy chat bubble bottom-left.
2. Ask something like "What's MOP for HDB?" — you should get a real answer within a few seconds.
3. Try giving it a name + phone/email + what you're interested in (e.g. "I'm Alex, 9123 4567, interested in a 2-bedder near Tampines") — check your Google Sheet a few seconds later for a new row tagged `chatbot`.

## Cost estimate

You're billed per conversation, not a flat monthly fee — roughly **US$0.001–0.003 per visitor conversation** with the default model (claude-3-5-haiku). That's about 300–1,000 conversations per US$1. For a site your size, $5–10 of credit should comfortably last months. Cloudflare Pages Functions themselves are free on your current plan for this volume.

## If something goes wrong

- **Chat bubble doesn't respond / shows "Chat isn't configured yet"** → the `ANTHROPIC_API_KEY` variable is missing or wasn't saved as Encrypted — recheck step 2.
- **Leads aren't showing in your Sheet** → the chatbot reuses the exact same webhook as your contact form, so if contact.html leads are working, chatbot leads will too — check the Sheet's `source` column for `chatbot` rows specifically, they may just be lower down.
- Send me the error message (or a screenshot) and I can debug from there.
