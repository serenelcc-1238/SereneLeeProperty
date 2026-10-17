/**
 * Cloudflare Worker — serves the static site AND powers the AI chat widget.
 *
 * This project deploys via `wrangler deploy` (see .github/workflows/deploy.yml),
 * which is different from Cloudflare Pages — there's no automatic "functions/"
 * folder routing here. Instead, ALL requests come through this one script:
 *   - POST /api/chat  -> handled right here (calls Claude, captures leads)
 *   - everything else -> served from static assets (env.ASSETS)
 *   The chatbot can also look up HDB resale, URA private transaction and
 *   new launch data from the weekly-refreshed files in data/ (see DATA_TOOLS).
 *
 * Requires one environment variable, set in the Cloudflare dashboard
 * (Workers & Pages > sereneleeproperty > Settings > Variables and secrets):
 *   ANTHROPIC_API_KEY   — your key from console.anthropic.com (add as a Secret)
 *
 * Optional environment variable:
 *   ANTHROPIC_MODEL     — defaults to "claude-haiku-5-5" (fast, cheap,
 *                          plenty capable for FAQ-style answers).
 *
 * Lead capture reuses the SAME Google Apps Script webhook already wired up to
 * the contact form, calculator and upgrade checklist — so chatbot leads land
 * in the same Google Sheet as everything else.
 */

const GAS_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbzxomLsd_yvi8pEaXvHK3qddAPdnX7889wnjU4i5AoxXIv7dQv7h973bZ9gwQq_1dk/exec";

const ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages";
const DEFAULT_MODEL = "claude-haiku-5-5";
const MAX_TOKENS = 900;

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
- new-launches.html — current new launch projects Serene is tracking, with prices, TOP dates, region/tenure filters.
- market-map.html — interactive map of HDB resale and private transactions by town/district, with "Check my block" and "Check my condo" lookups.
- million-dollar-hdb.html — every $1M+ HDB resale.
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
- For questions about actual prices, use the data tools instead of guessing:
  - hdb_resale_lookup for HDB resale prices (by town, flat type, street or block).
  - private_transactions_lookup for condo/EC/landed transaction prices (by project or postal district).
  - new_launches_lookup for current new launches (starting price, units left, TOP).
  - mrt_lookup for anything about MRT/LRT proximity: blocks or condos near a station, or the nearest station to a block or condo. Quote distances as "about Xm straight-line" and mention walking is a bit longer. For a map view, point to market-map.html (the block and condo check shows a OneMap location map).
- When you quote figures: give the median and range (and $psf), say how many deals and over what period, and name the source and the "data as of" date, e.g. "Based on 48 HDB resale deals in the last 12 months (data.gov.sg, updated 12 Oct 2026)". Round to the nearest $1,000. These are past transacted prices, not a valuation of the visitor's own unit — for a proper valuation or a specific unit, offer to connect them with Serene.
- Never invent numbers. If a tool returns no deals or an error, say so and point to market-map.html or WhatsApp Serene.
- Serene serves clients across ALL of Singapore, every HDB town and every district. Never say or imply that any town, estate or district is outside her area, focus, coverage or expertise, and never compare areas as ones she knows better or less well. Answer every location question with the same confidence, and offer Serene's help for any area.
- For a new launch's unit mix, floor plans or VIP preview access, point to new-launches.html and offer Serene's help.
- For a personal affordability/eligibility calculation, point to calculator.html or upgrade-checklist.html.
- Do not give definitive personal financial, mortgage, tax or legal advice — share the general rule, then suggest confirming specifics with Serene or the relevant authority (HDB/IRAS/CPF Board).
- You are not able to book viewings, see current asking prices/listings, or see a visitor's financial documents — for anything requiring that, direct them to WhatsApp Serene directly.
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
          "Short note on what they want, e.g. 'Interested in Serra Residences preview' or 'Wants help deciding sell-first vs buy-first'",
      },
    },
    required: ["name", "interest"],
  },
};

/* ---------- Market data tools (HDB resale + URA private transactions) ----------
   The chatbot reads the SAME data files the Market Map uses (data/*.json).
   update_market_data.py refreshes them every Monday ~6am SGT from:
     - HDB resale prices: data.gov.sg (official HDB dataset)
     - Private transactions: URA Data Service
     - New launches: ERA new launch portal (update_new_launches.py)
   So answers are as current as the latest weekly refresh — no extra API keys
   or calls to government servers from the chatbot itself. */

const FLAT_TYPE_CODES = {
  "1": "1-room", "2": "2-room", "3": "3-room", "4": "4-room",
  "5": "5-room", E: "Executive", M: "Multi-generation",
};
const SALE_TYPES = { 1: "New sale", 2: "Sub sale", 3: "Resale" };
const PROP_TYPES = { C: "Condo/Apartment", E: "Executive Condo", L: "Landed" };
const SQM_TO_SQFT = 10.7639;

const DATA_TOOLS = [
  {
    name: "hdb_resale_lookup",
    description:
      "Look up actual HDB resale transactions (official HDB data via data.gov.sg, refreshed weekly). Use for any question about HDB resale prices in a town, street or block — e.g. 'how much is a 4-room in Woodlands', 'recent sales at Blk 574B Woodlands Dr 16'. Covers the last 36 months of deals.",
    input_schema: {
      type: "object",
      properties: {
        town: {
          type: "string",
          description: "HDB town, e.g. 'Woodlands', 'Sembawang', 'Yishun', 'Ang Mo Kio', 'Kallang/Whampoa'.",
        },
        flat_type: {
          type: "string",
          enum: ["2", "3", "4", "5", "E", "M"],
          description: "Optional. 2/3/4/5 = 2- to 5-room, E = Executive, M = Multi-generation.",
        },
        street: { type: "string", description: "Optional street name or part of it, e.g. 'Woodlands Dr 16'." },
        block: { type: "string", description: "Optional block number, e.g. '574B'." },
        months: { type: "integer", description: "Look-back window in months (default 12, max 36)." },
      },
      required: ["town"],
    },
  },
  {
    name: "private_transactions_lookup",
    description:
      "Look up actual private property transactions (official URA caveat data, refreshed weekly) for a condo/EC/landed project or a postal district. Use for questions like 'what did units at Forestville sell for', 'condo prices in district 25', 'EC resale prices in Sembawang'. Covers the last 5 years.",
    input_schema: {
      type: "object",
      properties: {
        project: { type: "string", description: "Optional project name or part of it, e.g. 'Forestville', 'Parc Canberra'." },
        district: {
          type: "string",
          description: "Optional 2-digit postal district, e.g. '25' (Woodlands/Admiralty), '27' (Yishun/Sembawang), '26' (Upper Thomson/Springleaf).",
        },
        property_type: { type: "string", enum: ["C", "E", "L"], description: "Optional. C = condo/apartment, E = executive condo, L = landed." },
        sale_type: { type: "string", enum: ["new", "resale", "sub"], description: "Optional filter on type of sale." },
        months: { type: "integer", description: "Look-back window in months (default 12, max 60)." },
      },
    },
  },
  {
    name: "new_launches_lookup",
    description:
      "List current new launch condo/EC projects (from the ERA new launch feed, refreshed weekly) with district, region, TOP, tenure, total/available units and starting price. Filter by district, region or name.",
    input_schema: {
      type: "object",
      properties: {
        district: { type: "string", description: "Optional 2-digit district, e.g. '25'." },
        region: { type: "string", enum: ["CCR", "RCR", "OCR"], description: "Optional market region." },
        name: { type: "string", description: "Optional project name or part of it." },
      },
    },
  },
  {
    name: "mrt_lookup",
    description:
      "Find MRT/LRT proximity using OneMap (Singapore Land Authority) locations, refreshed weekly. Two uses: (1) give a station to list HDB blocks and private projects near it, e.g. 'which HDB in Pasir Ris is near MRT'; (2) give an HDB block (town + block, optionally street) or a private project name to get its nearest stations and distances. Distances are straight-line metres, not walking routes.",
    input_schema: {
      type: "object",
      properties: {
        station: { type: "string", description: "Station name, e.g. 'Pasir Ris', 'Woodlands South', 'Canberra'. Use for 'what's near X MRT'." },
        town: { type: "string", description: "HDB town of the block, e.g. 'Yishun'. When asking about a town in general without a station, give the town and the tool lists its stations." },
        street: { type: "string", description: "Optional street of the HDB block, e.g. 'Yishun St 31'." },
        block: { type: "string", description: "HDB block number, e.g. '335C'." },
        project: { type: "string", description: "Private condo/EC/landed project name, e.g. 'Forestville'." },
        radius_m: { type: "integer", description: "For station searches: radius in metres (default 500, max 1000)." },
      },
    },
  },
];

async function loadData(env, origin, path) {
  const res = await env.ASSETS.fetch(new Request(`${origin}/${path}`));
  if (!res.ok) throw new Error(`Data file ${path} not available (${res.status})`);
  return res.json();
}

function slugTown(t) {
  return t.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function norm(s) {
  return String(s || "")
    .toUpperCase()
    .replace(/\bDRIVE\b/g, "DR").replace(/\bAVENUE\b/g, "AVE").replace(/\bSTREET\b/g, "ST")
    .replace(/\bROAD\b/g, "RD").replace(/\bCRESCENT\b/g, "CRES").replace(/\bCENTRAL\b/g, "CTRL")
    .replace(/[^A-Z0-9 ]/g, " ").replace(/\s+/g, " ").trim();
}

function monthsAgo(n) {
  const d = new Date(Date.now() + 8 * 3600e3); // SGT
  d.setUTCMonth(d.getUTCMonth() - n);
  return d.toISOString().slice(0, 7);
}

function stats(prices) {
  if (!prices.length) return null;
  const s = [...prices].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  const median = s.length % 2 ? s[mid] : Math.round((s[mid - 1] + s[mid]) / 2);
  return { count: s.length, median, min: s[0], max: s[s.length - 1] };
}

async function hdbLookup(env, origin, input) {
  const months = Math.min(Math.max(parseInt(input.months) || 12, 1), 36);
  const since = monthsAgo(months);
  const market = await loadData(env, origin, "data/market-data.json");
  const towns = Object.keys(market.hdb.towns);
  const want = norm(input.town).replace(/ /g, "");
  const town = towns.find((t) => norm(t).replace(/ /g, "") === want) ||
    towns.find((t) => norm(t).replace(/ /g, "").includes(want));
  if (!town) return { error: `Unknown HDB town '${input.town}'. Valid towns: ${towns.join(", ")}` };

  const file = await loadData(env, origin, `data/hdb/${market.hdb.towns[town].file}.json`);
  const streetQ = input.street ? norm(input.street) : "";
  const blockQ = input.block ? String(input.block).toUpperCase().replace(/^BLK\s*/, "").trim() : "";
  const ft = input.flat_type || "";

  const deals = [];
  for (const [street, blocks] of Object.entries(file.streets)) {
    if (streetQ && !norm(street).includes(streetQ)) continue;
    for (const [blk, rows] of Object.entries(blocks)) {
      if (blockQ && blk !== blockQ) continue;
      for (const r of rows) {
        // [month, flat_type, storey_from, sqm, model_idx, lease_start, price]
        if (r[0] < since) continue;
        if (ft && r[1] !== ft) continue;
        deals.push({
          month: r[0], block: blk, street, flat_type: FLAT_TYPE_CODES[r[1]] || r[1],
          storey: `${String(r[2]).padStart(2, "0")}-${String(r[2] + 2).padStart(2, "0")}`,
          sqm: r[3], model: file.models[r[4]] || "", lease_start: r[5], price: r[6],
          psf: Math.round(r[6] / (r[3] * SQM_TO_SQFT)),
        });
      }
    }
  }
  deals.sort((a, b) => (a.month < b.month ? 1 : -1));

  const s = stats(deals.map((d) => d.price));
  const psf = stats(deals.map((d) => d.psf));
  // Quarterly town trend (average price, $k) for the selected flat type, last 4 full quarters.
  const series = ft ? market.hdb.towns[town].ft[ft] : market.hdb.towns[town];
  const q = market.hdb.quarters;
  const lastFull = market.hdb.last_partial ? q.length - 2 : q.length - 1;
  const trend = series
    ? q.slice(lastFull - 3, lastFull + 1).map((label, i) => ({
        quarter: label,
        deals: series.n[lastFull - 3 + i],
        avg_price_k: series.p[lastFull - 3 + i],
      }))
    : [];

  return {
    source: "HDB resale flat prices (data.gov.sg)",
    data_as_of: market.hdb.fetched,
    town,
    filters: { flat_type: ft ? FLAT_TYPE_CODES[ft] : "all", street: input.street || "", block: blockQ, since },
    summary: s ? { ...s, median_psf: psf.median } : "No resale deals match these filters in this period.",
    town_quarterly_trend: trend,
    latest_deals: deals.slice(0, 8),
  };
}

async function privateLookup(env, origin, input) {
  const months = Math.min(Math.max(parseInt(input.months) || 12, 1), 60);
  const since = monthsAgo(months);
  if (!input.project && !input.district) return { error: "Give a project name or a district." };

  const projects = await loadData(env, origin, "data/ura/projects.json");
  // [name, street, district, segment, main_prop_type, tenure, deals, last_month]
  let matches = [];
  if (input.project) {
    const q = norm(input.project);
    matches = projects.filter((p) => norm(p[0]).includes(q));
    if (input.district) matches = matches.filter((p) => p[2] === String(input.district).padStart(2, "0"));
    if (!matches.length) return { error: `No private project matching '${input.project}' with deals in the last 5 years.` };
    matches = matches.sort((a, b) => b[6] - a[6]).slice(0, 3);
  }

  const districts = input.district
    ? [String(input.district).padStart(2, "0")]
    : [...new Set(matches.map((p) => p[2]))];
  const saleWant = { new: 1, sub: 2, resale: 3 }[input.sale_type] || 0;

  const deals = [];
  for (const d of districts) {
    const file = await loadData(env, origin, `data/ura/d${d}.json`);
    for (const [key, rows] of Object.entries(file)) {
      const [name, street] = key.split("|");
      if (matches.length && !matches.some((m) => m[0] === name && m[1] === street)) continue;
      for (const r of rows) {
        // [month, sale_type(1 new,2 sub,3 resale), sqm, floor_range, price, units, prop_type]
        if (r[0] < since) continue;
        if (saleWant && r[1] !== saleWant) continue;
        if (input.property_type && r[6] !== input.property_type) continue;
        if (r[5] > 1) continue; // skip bulk/en-bloc deals, they distort unit prices
        deals.push({
          month: r[0], project: name, street, district: d,
          sale_type: SALE_TYPES[r[1]], type: PROP_TYPES[r[6]] || r[6],
          sqft: Math.round(r[2] * SQM_TO_SQFT), floor: r[3], price: r[4],
          psf: Math.round(r[4] / (r[2] * SQM_TO_SQFT)),
        });
      }
    }
  }
  deals.sort((a, b) => (a.month < b.month ? 1 : -1));

  const s = stats(deals.map((d) => d.price));
  const psf = stats(deals.map((d) => d.psf));
  const market = await loadData(env, origin, "data/market-data.json");
  return {
    source: "URA private residential transactions (URA Data Service)",
    data_as_of: market.ura.fetched,
    projects_matched: matches.map((m) => ({ name: m[0], street: m[1], district: m[2], region: m[3], tenure: m[5] })),
    filters: { district: input.district || "", property_type: input.property_type || "all", sale_type: input.sale_type || "all", since },
    summary: s
      ? { ...s, median_psf: psf.median, psf_range: [psf.min, psf.max] }
      : "No private transactions match these filters in this period.",
    latest_deals: deals.slice(0, 8),
  };
}

async function newLaunchLookup(env, origin, input) {
  const data = await loadData(env, origin, "data/new-launches.json");
  let list = data.projects;
  if (input.district) list = list.filter((p) => p.district === `d${String(input.district).padStart(2, "0")}`);
  if (input.region) list = list.filter((p) => p.region === input.region);
  if (input.name) list = list.filter((p) => norm(p.name).includes(norm(input.name)));
  return {
    source: "ERA new launch feed",
    data_as_of: data.retrieved,
    count: list.length,
    projects: list.slice(0, 12).map((p) => ({
      name: p.name, status: p.status, district: p.district, region: p.region, developer: p.developer,
      tenure: p.tenure, top: p.top, units: p.units, available: p.available, from_price: p.minPrice,
    })),
    note: "Pinned spotlight projects (e.g. The Serra Residences) are on new-launches.html but not in this feed.",
  };
}


async function mrtLookup(env, origin, input) {
  let st;
  try {
    st = await loadData(env, origin, "data/geo/stations.json");
  } catch {
    return { error: "MRT locations are still being prepared (first OneMap run). Point the visitor to market-map.html or WhatsApp Serene." };
  }
  const stations = st.stations; // [name, codes, lat, lng]
  const label = (i) => `${stations[i][0]}${stations[i][1] ? " (" + stations[i][1] + ")" : ""}`;
  const near3 = (v) => v[3].map(([i, m]) => ({ station: label(i), metres: m }));
  const base = { source: "OneMap, Singapore Land Authority", data_as_of: st.fetched, distance_note: "Straight-line distance; walking is usually 20-40% longer." };

  // 1) Station -> what's nearby
  if (input.station) {
    const q = norm(input.station).replace(/\b(MRT|LRT|STATION|STN)\b/g, "").trim();
    const hits = stations
      .map((s, i) => ({ s, i }))
      .filter(({ s }) => norm(s[0]).replace(/\b(MRT|LRT)\b/g, "").trim() === q);
    const found = hits.length ? hits : stations.map((s, i) => ({ s, i })).filter(({ s }) => norm(s[0]).includes(q));
    if (!found.length) return { error: `No MRT/LRT station matching '${input.station}'.` };
    const radius = Math.min(Math.max(parseInt(input.radius_m) || 500, 100), 1000);
    const out = [];
    for (const { s, i } of found.slice(0, 2)) {
      const slug = s[0].toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
      const near = await loadData(env, origin, `data/geo/near/${slug}.json`);
      const hdb = near.hdb.filter((r) => r[3] <= radius);
      const pte = near.pte.filter((r) => r[3] <= radius);
      const byStreet = {};
      for (const [town, street, blk, m] of hdb) (byStreet[street] = byStreet[street] || { town, blocks: [] }).blocks.push(`${blk} (${m}m)`);
      out.push({
        station: label(i),
        radius_m: radius,
        hdb_block_count: hdb.length,
        hdb_by_street: Object.entries(byStreet).slice(0, 12).map(([street, v]) => ({ street, town: v.town, blocks: v.blocks.slice(0, 10) })),
        private_projects: pte.slice(0, 15).map(([name, street, d, m, pt, ten]) => ({ name, street, district: d, metres: m, type: PROP_TYPES[pt] || pt, tenure: ten })),
      });
    }
    return { ...base, results: out, note: "Only HDB blocks with a resale in the last 3 years and private projects with a deal in the last 5 years are listed." };
  }

  // 2) HDB block -> nearest stations
  if (input.block) {
    const blk = String(input.block).toUpperCase().replace(/^BLK\s*/, "").trim();
    const market = await loadData(env, origin, "data/market-data.json");
    let town = null;
    if (input.town) {
      const want = norm(input.town).replace(/ /g, "");
      town = Object.keys(market.hdb.towns).find((t) => norm(t).replace(/ /g, "") === want) ||
        Object.keys(market.hdb.towns).find((t) => norm(t).replace(/ /g, "").includes(want));
    }
    const towns = town ? [town] : [];
    if (!towns.length && input.street) {
      const ix = await loadData(env, origin, "data/hdb/index.json");
      const sq = norm(input.street);
      for (const [s, v] of Object.entries(ix)) if (norm(s).includes(sq) && v[1].includes(blk)) towns.push(v[0]);
    }
    if (!towns.length) return { error: "Need the town (or street) of the block." };
    const res = [];
    for (const t of [...new Set(towns)].slice(0, 3)) {
      const g = await loadData(env, origin, `data/geo/hdb/${market.hdb.towns[t].file}.json`).catch(() => ({}));
      const sq = input.street ? norm(input.street) : "";
      for (const [key, v] of Object.entries(g)) {
        const [street, b] = key.split("|");
        if (b !== blk || (sq && !norm(street).includes(sq))) continue;
        res.push({ block: b, street, town: t, postal: v[2], nearest_stations: near3(v) });
      }
    }
    if (!res.length) return { ...base, error: `No location on file for Blk ${blk}${input.street ? " " + input.street : ""}. It may not have had a resale in 3 years.` };
    return { ...base, results: res.slice(0, 5) };
  }

  // 3) Private project -> nearest stations
  if (input.project) {
    const projects = await loadData(env, origin, "data/ura/projects.json");
    const q = norm(input.project);
    const matches = projects.filter((p) => norm(p[0]).includes(q)).sort((a, b) => b[6] - a[6]).slice(0, 3);
    if (!matches.length) return { error: `No private project matching '${input.project}'.` };
    const res = [];
    for (const p of matches) {
      const g = await loadData(env, origin, `data/geo/ura/d${p[2]}.json`).catch(() => ({}));
      const v = g[`${p[0]}|${p[1]}`];
      if (v) res.push({ project: p[0], street: p[1], district: p[2], nearest_stations: near3(v) });
    }
    if (!res.length) return { ...base, error: "No location on file for that project yet." };
    return { ...base, results: res };
  }

  // 4) Town only -> stations within/near the town (by its blocks)
  if (input.town) {
    const market = await loadData(env, origin, "data/market-data.json");
    const want = norm(input.town).replace(/ /g, "");
    const t = Object.keys(market.hdb.towns).find((x) => norm(x).replace(/ /g, "").includes(want));
    if (!t) return { error: `Unknown HDB town '${input.town}'.` };
    const g = await loadData(env, origin, `data/geo/hdb/${market.hdb.towns[t].file}.json`).catch(() => ({}));
    const count = {};
    for (const v of Object.values(g)) { const [i, m] = v[3][0]; if (m <= 1500) count[i] = (count[i] || 0) + 1; }
    const list = Object.entries(count).sort((a, b) => b[1] - a[1]).slice(0, 10).map(([i, n]) => ({ station: label(+i), blocks_nearest_to_it: n }));
    return { ...base, town: t, stations: list, tip: "Call again with station to list the blocks within a radius." };
  }
  return { error: "Give a station, a block (with town or street), a project, or a town." };
}

async function runDataTool(env, origin, name, input) {
  try {
    if (name === "hdb_resale_lookup") return await hdbLookup(env, origin, input || {});
    if (name === "private_transactions_lookup") return await privateLookup(env, origin, input || {});
    if (name === "new_launches_lookup") return await newLaunchLookup(env, origin, input || {});
    if (name === "mrt_lookup") return await mrtLookup(env, origin, input || {});
    return { error: `Unknown tool ${name}` };
  } catch (err) {
    console.error(`Tool ${name} failed:`, err);
    return { error: "Data lookup failed. Tell the visitor you couldn't pull the figures right now and suggest market-map.html or WhatsApp Serene." };
  }
}

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
      tools: [LEAD_TOOL, ...DATA_TOOLS],
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

    // Tool-use loop: run every tool Claude asks for (lead capture and/or
    // HDB/URA/new-launch lookups), hand back the results, then let Claude
    // write the reply. Capped so one message can't loop forever.
    const origin = new URL(request.url).origin;
    let guard = 0;
    while (result.stop_reason === "tool_use" && guard < 4) {
      guard++;
      const toolUses = result.content.filter((b) => b.type === "tool_use");
      if (!toolUses.length) break;

      const toolResults = [];
      for (const tu of toolUses) {
        let content;
        if (tu.name === "capture_lead") {
          await sendLeadToSheet(tu.input || {}, pageUrl);
          content = "Saved. Let the visitor know Serene will follow up.";
        } else {
          content = JSON.stringify(await runDataTool(env, origin, tu.name, tu.input));
        }
        toolResults.push({ type: "tool_result", tool_use_id: tu.id, content });
      }

      messages.push({ role: "assistant", content: result.content });
      messages.push({ role: "user", content: toolResults });

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

// Google Analytics 4 tag (Measurement ID G-7DN22DCXLZ). Injected into every
// HTML page's <head> at the edge, so every current and future page gets
// tracked automatically — no need to paste this into each HTML file by hand.
class GtagInjector {
  element(head) {
    head.append(
      `<script async src="https://www.googletagmanager.com/gtag/js?id=G-7DN22DCXLZ"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-7DN22DCXLZ');
</script>`,
      { html: true }
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

    // Everything else: serve the static site, then inject the GA4 tag into
    // any HTML response before it reaches the visitor.
    const response = await env.ASSETS.fetch(request);
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("text/html")) {
      return new HTMLRewriter().on("head", new GtagInjector()).transform(response);
    }
    return response;
  },
};
