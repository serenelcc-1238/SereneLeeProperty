# SEO Audit — iamserenelee.com

Prepared for Serene Lee, ERA Realty · 30 Aug 2026
Method note: no SEO tool (Ahrefs/Semrush/Search Console) is connected to this session, so keyword difficulty and "opportunity score" below are directional — based on search-result competition, People-Also-Ask patterns, and what comparable individual-agent sites are ranking for, not verified search-volume data. Connecting Google Search Console (free) would let a future pass show your actual impressions, clicks, and current rankings.

## Executive Summary

Your site's biggest strength is the custom affordability calculator — very few individual agents in Singapore build their own MSR/TDSR calculator, and "HDB affordability calculator Singapore" is a real, searched-for term with visible competition from dedicated calculator sites. That's a genuine, ownable asset worth pushing harder in your titles and copy.

Your biggest weakness is that your Property Insights page currently has zero original content — every article links out to era.com.sg. Google can only rank iamserenelee.com for what actually lives on iamserenelee.com, so right now that page contributes nothing to your own search visibility, no matter how often you update it. A direct competitor (an individual CEA agent running a near-identical HDB-upgrade-focused site) publishes 2,500–3,000-word original guides on their own domain and is very likely outranking you for exactly the terms your clients search before they call you.

Three priorities, in order of impact: (1) turn 2–3 of your Property Insights links into real, original articles hosted on your own domain, (2) tighten your title tags and meta descriptions — several are currently too long and get cut off in Google's results, and none are optimized around how people actually phrase these searches, and (3) add the technical basics that are completely missing — no sitemap, no robots.txt, no Open Graph tags (meaning your links look bare when shared on WhatsApp), and no structured data.

Overall assessment: **needs work, but with one standout asset to build around.** None of this is a rebuild — it's targeted additions to what's already a clean, fast, mobile-friendly site.

---

## 1. Keyword Opportunity Table

| Keyword | Est. Difficulty | Opportunity Score | Current Ranking | Intent | Recommended Content Type |
|---|---|---|---|---|---|
| HDB affordability calculator Singapore | Moderate | **High** | Not ranking (calculator page not optimized for this phrase) | Transactional | Optimize existing calculator page title/H1/intro copy |
| HDB to condo upgrade guide | Hard | **High** | Not ranking (no original content) | Informational → Commercial | New long-form guide (own domain) |
| can I afford to upgrade from HDB to condo | Moderate | **High** | Not ranking | Informational, high intent | Blog post / calculator intro copy |
| new launch condo Singapore 2026 | Hard | Medium | Not ranking | Commercial | New Launches page title + intro |
| HDB MOP upgrade timeline | Moderate | **High** | Not ranking | Informational | New long-form guide |
| new Executive Condo vs private condo | Moderate | Medium | Not ranking | Commercial | Blog post |
| MSR TDSR calculator | Moderate | Medium | Not ranking | Transactional | Calculator page copy |
| how much cash do I need to upgrade from HDB | Easy–Moderate | **High** | Not ranking | Informational, high intent | Blog post, links to calculator |
| ABSD remission HDB upgrade | Moderate | Medium | Not ranking | Informational | Blog post |
| bridging loan Singapore HDB upgrade | Moderate | Medium | Not ranking | Informational | Blog post |
| National Day Rally 2026 housing changes | Easy (time-sensitive) | **High** | Not ranking (article links to ERA, not hosted) | Informational, high intent right now | Rewrite as original post on own domain |
| [district] new launch condo (e.g. "Bedok new launch condo") | Easy per-district | Medium | Not ranking | Commercial | Add a short paragraph per project on New Launches page |
| CEA registered agent Singapore | Hard (huge competition) | Low | Not ranking | Navigational | Not worth chasing directly — brand search only |
| HDB resale vs new launch which is better | Moderate | Medium | Not ranking | Informational | Blog post |
| Singapore property agent numbers-first approach | Easy (near-unique phrase) | Medium | Likely rankable — it's already your tagline | Branded | Reinforce in title tags |
| free property affordability calculator | Hard (portals dominate) | Low–Medium | Not ranking | Transactional | Long-tail variant instead ("HDB affordability calculator") |
| ERA new launch listings 2026 | Moderate | Medium | Not ranking | Commercial | New Launches intro paragraph |
| HDB loan vs bank loan for upgraders | Moderate | Medium | Not ranking | Informational | Blog post |
| first time HDB upgrader guide Singapore | Moderate | **High** | Not ranking | Informational, high intent | Pillar guide |
| property agent testimonials Singapore [your name] | Easy (branded) | Low (until reviews exist) | Not ranking — page nearly empty | Navigational/trust | Add real reviews first |

---

## 2. On-Page Issues Table

| Page | Issue | Severity | Recommended Fix |
|---|---|---|---|
| index.html | Title tag is 72 characters — gets truncated in Google results | High | Shorten to ~53 chars, keyword-first (see Section 5) |
| index.html | Meta description is 177 characters — gets cut off | High | Rewrite to ~154 chars with a clear CTA (Section 5) |
| index.html | H1 ("Your trusted guide...") contains no target keyword | Medium | Rework to include "HDB Upgrade" / "New Launch" (Section 5) |
| calculator.html | Title/H1 don't contain "HDB" or "Singapore" despite that being how people actually search for this tool | High | Add both terms to title tag (Section 5) |
| blog.html (Property Insights) | Every article is an external link to era.com.sg — zero original content on your own domain | **Critical** | Convert top 2–3 topics into original posts (Section 3) |
| testimonials.html | Page is ~111 words, entirely "reviews coming soon" placeholder — thin content | Medium | Add 2–3 real quotes as they come in, or keep off main nav until populated |
| All pages | No canonical tag | Low | Add self-referencing `<link rel="canonical">` on each page |
| All pages | No Open Graph / Twitter Card tags — links shared via WhatsApp show no preview image or custom text | High | Add `og:title`, `og:description`, `og:image` to every page (Section 4) |
| All pages | No structured data (schema.org) at all | Medium–High | Add RealEstateAgent/Organization schema sitewide, FAQPage on calculator (Section 4) |
| New Launches cards | Rich factual detail (tenure, TOP, developer) but no descriptive sentence per project | Low | Add one keyword-natural sentence per card (Section 5) |

---

## 3. Content Gap Recommendations

**1. Original HDB-upgrade guide on your own domain**
Why it matters: this is the exact niche your business is built on, and it's the single biggest gap — your closest comparable competitor (another individual CEA agent) has a 2,500–3,000-word original guide covering MOP rules, ABSD remission, CPF usage, bridging loans, and a step-by-step timeline, hosted on their own site. You currently have nothing on iamserenelee.com covering this at all — only a link out to ERA. Recommended format: long-form guide (aim for 1,200+ words to start — doesn't need to match 3,000 on day one). Priority: **High**. Effort: substantial (multi-day, but can be built from material you already know well).

**2. "How much cash do I need to upgrade" — calculator-linked post**
Why it matters: high search intent, directly matches what your calculator already answers, and gives you a natural place to link straight into the tool (keeps the visitor on your site instead of bouncing to ERA). Priority: **High**. Effort: moderate (half day).

**3. Rewrite the National Day Rally 2026 housing piece as original content**
Why it matters: it's timely (people are searching for this right now), you already did the underlying research for the calculator's income-ceiling update, and right now that research effort isn't earning you any search visibility because the article link points to era.com.sg. Priority: **High**. Effort: quick win (1–2 hours) — you already have the facts from the calculator update.

**4. Real testimonials**
Why it matters: thin, near-empty pages are a mild negative quality signal, and social proof matters more for conversion than for raw SEO — but it's an easy win once you have even 2–3 clients willing to give a short quote. Priority: Medium. Effort: quick win once quotes are in hand.

**5. Per-district new launch context**
Why it matters: "[district] new launch condo" is a real, lower-competition long-tail pattern, and you already have the raw data (district, tenure, TOP) on each card — just needs a sentence of narrative. Priority: Medium. Effort: quick win.

---

## 4. Technical SEO Checklist

| Check | Status | Details |
|---|---|---|
| HTTPS | Pass | Served via Cloudflare, secure by default |
| Mobile-friendly | Pass | Responsive nav, media queries confirmed at 860px/600px breakpoints |
| Image alt text | Pass | Every image checked has descriptive alt text |
| Page speed / lightweight | Pass | Static HTML/CSS/JS, no heavy framework; external assets (Google Fonts, jsPDF, IG embed) are reasonable in number |
| robots.txt | **Fail** | Does not exist — add one (simple allow-all + sitemap reference) |
| XML sitemap | **Fail** | Does not exist — needed for Google to discover all 7 pages efficiently |
| Canonical tags | **Fail** | Missing on every page |
| Open Graph / Twitter Card tags | **Fail** | Missing on every page — directly hurts how your links look when shared on WhatsApp, which is your primary CTA channel |
| Structured data (schema.org) | **Fail** | None present — no RealEstateAgent, Organization, or FAQPage markup anywhere |
| Google Search Console | Unknown | Can't verify from the HTML — worth confirming this is set up, since it's how you'd see real ranking/click data going forward |
| Broken links | Pass (spot-checked) | No broken internal links found during this audit |

---

## 5. Ready-to-Use Wording (copy-paste)

### Homepage (index.html)
- **Title tag** — current is 72 characters (gets truncated in Google's results). Replace with (53 chars):
  `HDB Upgrade & New Launch Specialist | Serene Lee, ERA`
- **Meta description** — current is 177 characters (gets cut off). Replace with (154 chars):
  `Thinking of upgrading from HDB to condo, or eyeing a new launch in Singapore? Get real numbers first with a free affordability check from Serene Lee, ERA.`
- **H1** — currently has no keyword. Replace:
  `Your trusted guide through Singapore's property market`
  with:
  `Your HDB Upgrade & New Launch Specialist in Singapore`

### Affordability Calculator (calculator.html)
- **Title tag** — replace `Affordability Calculator | Serene Lee, ERA Realty` (49 chars) with (56 chars):
  `HDB Affordability Calculator Singapore | Serene Lee, ERA`
- Add one sentence near the top of the page (above or below the H1) containing the phrase naturally, e.g.:
  `This free HDB affordability calculator uses the same MSR and TDSR formulas MAS and HDB apply, so you get a realistic answer before you start viewing units.`

### New Launches (new-launches.html)
- **Title tag** — replace `New Launches | Serene Lee, ERA Realty` (37 chars, currently under-using the space) with (57 chars):
  `Singapore New Launch Condos 2026 | Serene Lee, ERA Realty`
- Add one sentence to the intro paragraph naming the current districts covered, e.g.:
  `Currently covering new launches across Bedok, Buona Vista, Orchard/River Valley, Upper Thomson, Bukit Timah, Dairy Farm, Tanjong Pagar and Marina South.`
  (This single sentence naturally seeds several "[district] new launch" long-tail phrases at once.)

### Property Insights (blog.html)
- **Title tag** — current `Property Insights | Serene Lee, ERA Realty` is fine to keep, but it only works once real content sits behind it (see Section 3, item 1).
- Once original articles exist, each one needs its own title tag in the pattern:
  `[Specific Topic] — HDB Upgrade Guide | Serene Lee, ERA`

### About (about.html)
- **Title tag** — replace `About Serene Lee | ERA Realty` (29 chars, currently under-using the space) with (59 chars):
  `About Serene Lee | HDB Upgrade & New Launch Specialist, ERA`

### Sitewide — Open Graph tags (add to every page's `<head>`)
```html
<meta property="og:title" content="[same as that page's title tag]">
<meta property="og:description" content="[same as that page's meta description]">
<meta property="og:image" content="https://iamserenelee.com/assets/serene-photo.jpg">
<meta property="og:url" content="https://iamserenelee.com/[page].html">
<meta property="og:type" content="website">
```

---

## 6. Competitor Comparison Summary

| Dimension | Your Site | JetSet Homes (individual agent, HDB-upgrade niche) | Stacked Homes (large content publisher) |
|---|---|---|---|
| Original content on own domain | None (links to ERA) | 2,500–3,000-word guides | Hundreds of articles |
| Custom affordability calculator | **Yes — you win here** | No | No (links to third-party tools) |
| Title/meta optimization | Partial, several truncated | Optimized, keyword-first | Fully optimized |
| Structured data | None | Unknown/likely partial | Extensive |
| Publishing frequency | New launches updated ad hoc | Guide-style, less frequent but deep | Very frequent |
| Winner | — | **Content depth** | **Content volume** |

The takeaway isn't to out-publish Stacked Homes — that's not a realistic goal for a solo agent. It's to close the gap with JetSet Homes on your specific niche, where you already have a stronger tool (the calculator) than they do.

---

## Prioritized Action Plan

**Quick Wins (do this week):**
- Fix the homepage and calculator title tags and meta descriptions (Section 5) — under 30 minutes, directly fixes truncation in search results. *Impact: Medium-High. Effort: quick win.*
- Add Open Graph tags to all 7 pages (Section 5) — fixes how every WhatsApp-shared link looks. *Impact: High (you already drive most traffic via WhatsApp shares). Effort: quick win.*
- Rewrite the National Day Rally 2026 article as original content instead of a link-out — you already have the research. *Impact: High. Effort: quick win.*
- Add a robots.txt and XML sitemap. *Impact: Medium. Effort: quick win.*

**Strategic Investments (plan for this quarter):**
- Write 2–3 original long-form guides covering HDB-upgrade fundamentals (MOP timeline, cash needed to upgrade, EC vs private condo), hosted on iamserenelee.com. *Impact: High. Effort: substantial. Dependency: none — you already have the subject knowledge from building the calculator.*
- Add schema.org structured data (RealEstateAgent/Organization sitewide, FAQPage on the calculator). *Impact: Medium. Effort: moderate.*
- Set up Google Search Console if not already done, to get real ranking/click data for the next audit. *Impact: enables measurement of everything else. Effort: quick win, but needs your Google account access.*
- Once real client reviews come in, replace the Testimonials placeholder and add Review schema. *Impact: Medium (trust + conversion more than raw ranking). Effort: ongoing.*

---

Would you like me to:
- Draft the actual first long-form HDB-upgrade guide as a ready-to-publish article?
- Write the exact HTML for the Open Graph tags, robots.txt, and sitemap.xml so you can just upload them?
- Draft the FAQPage / RealEstateAgent schema markup?
- Turn the National Day Rally article into original content now?
