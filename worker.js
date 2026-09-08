/**
 * Cloudflare Worker — serves the static site AND powers the AI chat widget.
 *
 * This project deploys via `wrangler deploy` (see .github/workflows/deploy.yml),
 * which is different from Cloudflare Pages — there's no automatic "functions/"
 * folder routing here. Instead, ALL requests come through this one script:
 *   - POST /api/chat  -> handled right here (calls Claude, captures leads)
 *   - everything else -> served from static assets (env.ASSETS)
 *
 * Requires one environment variable, set in the Cloudflare dashboard
 * (Workers & Pages > sereneleeproperty > Settings > Variables and secrets):
 *   ANTHROPIC_API_KEY   — your key from console.anthropic.com (add as a Secret)
 *
 * Optional environment variable:
 *   ANTHROPIC_MODEL     — defaults to "claude-3-5-haiku-20241022" (fast, cheap,
 *                          plenty capable for FAQ-style answers).
 *
 * Lead capture reuses the SAME Google Apps Script webhook already wired up to
 * the contact form, calculator and upgrade checklist — so chatbot leads land
 * in the same Google Sheet as everything else.
 */

const GAS_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbzxomLsd_yvi8pEaXvHK3qddAPdnX7889wnjU4i5AoxXIv7dQv7h973bZ9gwQq_1dk/exec";

const ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages";
const DEFAULT_MODEL = "claude-haiku-4-5-20251001";
const MAX_TOKENS = 700;

/* ---------- Knowledge base / system prompt ----------
   Condensed from sereneleeproperty.com's own FAQ, About and site content
   (current as of Sep 2026) so the bot answers from real facts rather than
   guessing. Figures here can go stale — update this block (or ask Claude to)
   whenever a rule changes, the same way the FAQ page itself gets updated. */
const SYSTEM_PROMPT = `You are the website assistant for Serene Lee, a property agent with ERA Realty Network Pte Ltd in Singapore (CEA Registration No. R027578Z, ERA Estate Agent Licence No. L3002382K). You answer visitor questions on sereneleeproperty.com.

ABOUT SERENE:
- Helps clients buy, sell and rent HDB and private property anywhere in Singapore.
- Specializes in HDB upgrading (sell-first-vs-buy-first decisions) and new launch condos.
- Numbers-first, no-pressure approach: understands a client's budget/timeline before showing listings.
- Contact: WhatsApp +65 8086 8568 (wa.me/6580868568), email serenelcc@gmail.com.
- ERA Realty Network Pte Ltd, 450 Lorong 6 Toa Payoh, #03-01 ERA APAC Centre, Singapore 319394. ERA main line +65 6226 2000.

SITE PAGES YOU CAN POINT VISITORS TO (use relative links exactly as written):
- new-launches.html — current new launch projects Serene is tracking, with prices, TOP dates, region/tenure filters. ALWAYS point here for specific project pricing/availability — you do not have live listing data yourself.
- calculator.html — free affordability calculator (TDSR/MSR, loan eligibility estimate).
- upgrade-checklist.html — free 2-minute HDB Upgrader Checklist with a readiness score.
- blog.html — guides on lease decay, HDB upgrading, new launch write-ups.
- faq.html — 27 detailed FAQs on buying, selling and renting.
- testimonials.html, about.html, contact.html.

KEY SINGAPORE PROPERTY FACTS (current as of Sep 2026 — always caveat that rules change and to verify time-sensitive figures with Serene or the relevant authority):
- MOP (Minimum Occupation Period): 5 years for Standard HDB flats, 10 years for Plus/Prime flats, before the flat can be sold. ECs: 5-year MOP/10-year full privatisation (GLS tenders closed before 8 May 2026) or 10-year MOP/15-year privatisation (tenders closing on/after 8 May 2026).
- ABSD (Additional Buyer's Stamp Duty): Singapore Citizens 0%/20%/30% on 1st/2nd/3rd+ property; PRs 5%/30%/35%; Foreigners flat 60%; Entities flat 65%. US/Switzerland/Liechtenstein/Norway/Iceland nationals get Citizen-equivalent treatment via FTA.
- TDSR caps all debt repayments at 55% of gross monthly income (all property types); MSR caps at 30% (HDB and new ECs only).
- HFE letter (HDB Flat Eligibility) is mandatory before a BTO/SBF application or before getting an OTP on a resale flat; valid 9 months.
- The 15-month wait-out for private property owners buying an HDB resale flat was REMOVED on 28 July 2026 (cash/bank loan purchases only — 30-month wait-out still applies if using a CPF grant, BTO/SBF/developer EC, or HDB loan).
- CPF refund on sale: principal withdrawn + accrued interest (2.5% p.a. floor rate) must be refunded to CPF.
- HDB resale levy (for 2nd-timers, flats booked on/after 3 Mar 2006): $15k (2-room) to $50k (Executive/Maisonette) — does not apply if buying resale without a CPF grant, or upgrading to private property.
- Renting: 6-month minimum lease for HDB, 3-month for private. Whole-flat HDB rental needs 5-year MOP met and ALL owners must be Singapore Citizens (a PR co-owner disqualifies it). Non-Citizen Quota: 8% neighbourhood / 11% block cap on foreign tenants (Malaysians exempt). HDB approval required via My HDBPage before tenancy starts ($20 fee).
- Full detail and more FAQs (income ceilings, CPF grants, SSD, tenant screening, tax) are on faq.html — point visitors there for anything more specific than the summary above.

HOW TO BEHAVE:
- Be warm, concise, and helpful — like a knowledgeable colleague, not a sales script. Short paragraphs or a few bullet points, not walls of text.
- Never use markdown formatting (no **asterisks** for bold, no _underscores_ for italics, no ## headers). Your replies are shown as plain text, so write emphasis in plain words instead, and use a plain "-" at the start of a line for lists.
- Answer general Singapore property questions directly using the facts above.
- For anything about a SPECIFIC new launch's price, unit mix, or availability, direct the visitor to new-launches.html rather than guessing — you don't have live data.
- For a personal affordability/eligibility calculation, point to calculator.html or upgrade-checklist.html.
- Do not give definitive personal financial, mortgage, tax or legal advice — share the general rule, then suggest confirming specifics with Serene or the relevant authority (HDB/IRAS/CPF Board).
- You are not able to book viewings, access MLS/private listing data, or see a visitor's financial documents — for anything requiring that, direct them to WhatsApp Serene directly.
- If a visitor shares their name AND a way to reach them (phone or email) AND what they're interested in, use the capture_lead tool ONCE to pass it to Serene — then let them know Serene will follow up. Don't ask for contact details unless the conversation naturally calls for a follow-up (e.g. they want a specific project's pricing when it's out, or want Serene to review their numbers) — don't be pushy about it.
- If asked who you are: you're an AI assistant answering on Serene's behalf, not Serene herself.`;

const LEAD_TOOL = {
  name: "capture_lead",
  description:
    "Record a website visitor's contact details so Serene can follow up personally. Only call this once you have the visitor's name AND at least one contact method (phone or email) AND a clear sense of what they want. Call it at most once per conversation.",
  input_schema: {
    type: "object",
    properties: {
      name: { type: "string", description: "Visitor's name" },
      phone: { type: "string", description: "Visitor's phone number, if given" },
      email: { type: "string", description: "Visitor's email, if given" },
      interest: {
        type: "string",
        description:
          "Short note on what they want, e.g. 'Interested in Serra Residences VIP preview' or 'Wants help deciding sell-first vs buy-first'",
      },
    },
    required: ["name", "interest"],
  },
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function callClaude(env, messages) {
  const model = env.ANTHROPIC_MODEL || DEFAULT_MODEL;
  const res = await fetch(ANTHROPIC_API_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": env.ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model,
      max_tokens: MAX_TOKENS,
      system: SYSTEM_PROMPT,
      tools: [LEAD_TOOL],
      messages,
    }),
  });

  if (!res.ok) {
    const errText = await res.text().catch(() => "");
    throw new Error(`Anthropic API error ${res.status}: ${errText}`);
  }
  return res.json();
}

async function sendLeadToSheet(lead, pageUrl) {
  try {
    await fetch(GAS_WEBHOOK_URL, {
      method: "POST",
      headers: { "Content-Type": "text/plain" },
      body: JSON.stringify({
        source: "chatbot",
        name: lead.name || "",
        phone: lead.phone || "",
        email: lead.email || "",
        topic: lead.interest || "",
        page: pageUrl || "",
      }),
    });
  } catch (err) {
    // Fire-and-forget — a failed lead post shouldn't break the chat reply.
    console.error("Lead webhook failed:", err);
  }
}

function extractText(content) {
  const text = content
    .filter((block) => block.type === "text")
    .map((block) => block.text)
    .join("\n")
    .trim();

  // Safety net: strip any markdown bold/italic markers that slip through
  // despite the system prompt instruction, since the widget renders plain text.
  return text
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/__(.*?)__/g, "$1");
}

async function handleChatPost(request, env) {
  if (!env.ANTHROPIC_API_KEY) {
    return json(
      { error: "Chat isn't configured yet — ANTHROPIC_API_KEY is missing." },
      500
    );
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: "Invalid request body." }, 400);
  }

  const incoming = Array.isArray(body.messages) ? body.messages : [];
  if (!incoming.length) {
    return json({ error: "No messages provided." }, 400);
  }

  // Keep the conversation bounded — last 20 turns is plenty for an FAQ bot
  // and keeps per-request cost predictable.
  const messages = incoming.slice(-20).map((m) => ({
    role: m.role === "assistant" ? "assistant" : "user",
    content: m.content,
  }));

  const pageUrl = typeof body.page === "string" ? body.page : "";

  try {
    let result = await callClaude(env, messages);

    // Tool-use loop: if Claude wants to capture a lead, do it, then ask it
    // to produce the actual reply to show the visitor.
    let guard = 0;
    while (result.stop_reason === "tool_use" && guard < 2) {
      guard++;
      const toolUse = result.content.find((b) => b.type === "tool_use");
      if (!toolUse) break;

      if (toolUse.name === "capture_lead") {
        await sendLeadToSheet(toolUse.input || {}, pageUrl);
      }

      messages.push({ role: "assistant", content: result.content });
      messages.push({
        role: "user",
        content: [
          {
            type: "tool_result",
            tool_use_id: toolUse.id,
            content: "Saved. Let the visitor know Serene will follow up.",
          },
        ],
      });

      result = await callClaude(env, messages);
    }

    const reply = extractText(result.content) || "Sorry, I didn't catch that — could you rephrase?";
    return json({ reply });
  } catch (err) {
    console.error(err);
    return json(
      { error: "Something went wrong reaching the assistant. Please try again or WhatsApp Serene directly." },
      502
    );
  }
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === "/api/chat") {
      if (request.method === "POST") {
        return handleChatPost(request, env);
      }
      if (request.method === "GET") {
        return json({ ok: true, message: "POST a message to chat." });
      }
    }

    // Everything else: serve the static site exactly as before.
    return env.ASSETS.fetch(request);
  },
};
