"""
Page text and layout for /right-sizing-north (built weekly by build_town_pages.py).

Rules and amounts below were checked against official HDB, CPF, MOH and IRAS pages
on 20 Oct 2026. Re-check them when HDB/CPF announce changes (Budget in Feb,
National Day Rally in Aug) and update the "checked" date.
"""
import json, re

SITE = "https://sereneleeproperty.com"
CHECKED = "20 Oct 2026"
URL = SITE + "/right-sizing-north"

SRC = {
    "shb": "https://www.hdb.gov.sg/cs/infoweb/residential/living-in-an-hdb-flat/for-our-seniors/Monetising-Your-Flat-For-Retirement/silver-housing-bonus",
    "lbs": "https://www.hdb.gov.sg/cs/infoweb/residential/living-in-an-hdb-flat/for-our-seniors/Monetising-Your-Flat-For-Retirement/lease-buyback-scheme/how-it-works",
    "new": "https://www.hdb.gov.sg/cs/infoweb/residential/living-in-an-hdb-flat/for-our-seniors/Buying-a-New-Flat",
    "cca": "https://www.moh.gov.sg/newsroom/age-eligibility-for-community-care-apartments-lowered-from-65-to-55-years-old---monthly-fees-reduced-by-18--to-75--with-new-subsidies-/",
    "room": "https://www.hdb.gov.sg/cs/infoweb/apply-manage-and-renew-rental-of-bedroom/terms-and-conditions",
    "roomel": "https://www.hdb.gov.sg/cs/infoweb/residential/renting-out-a-flat-bedroom/renting-out-your-bedroom/eligibility",
    "flat": "https://www.hdb.gov.sg/cs/infoweb/residential/renting-a-flat/renting-from-the-open-market/regulations-for-renting-out-your-flat",
    "cpf": "https://www.cpf.gov.sg/member/infohub/educational-resources/selling-your-flat-age-55-cpf-refund",
    "hdbdata": "https://data.gov.sg/datasets/d_8b84c4ee58e3cfc0ece0d773c8ca6abc/view",
    "ura": "https://eservice.ura.gov.sg/maps/api/",
}

FT = {"2": "2-room", "3": "3-room", "4": "4-room", "5": "5-room", "E": "Executive"}

FAQS = [
    ("What is right-sizing?",
     "Selling a bigger home and moving to a smaller one, usually after the children have moved out. Most people do it to free up cash for retirement, cut upkeep and chores, or move closer to family, a clinic or an MRT station."),
    ("How much cash could I free up by right-sizing in Woodlands, Sembawang or Yishun?",
     "It depends on your flat and the home you move to. Using the last 12 months of HDB resale prices, moving from an Executive flat to a 3-room flat in the same town left a gap of roughly $230,000 to $510,000 before costs and CPF refunds. Use the estimator on this page for your own flat type."),
    ("What is the Silver Housing Bonus?",
     "A cash bonus of up to $30,000 (3-room) or up to $40,000 (2-room or smaller, including Community Care Apartments) for Singapore Citizens aged 55 and above who sell their home, buy a 3-room or smaller flat and commit part of the proceeds to their CPF Retirement Account. Household income must be $14,000 a month or less. HDB decides eligibility and the final amount."),
    ("Can I rent out a room instead of selling?",
     "Yes, if you own a 3-room or bigger flat. You must keep living in the flat with your tenants, each rental must be at least 6 months, and HDB must approve each tenant first ($9 per bedroom). A 3-room flat can rent out 1 bedroom; a 4-room or bigger flat up to 2."),
    ("What happens to my CPF when I sell at 55 or older?",
     "The CPF you used for the flat, plus accrued interest, is refunded to your CPF. From age 55, the refund first tops up your Retirement Account to the Full Retirement Sum; any balance stays in your Ordinary Account, where it can be used for your next home or withdrawn."),
    ("Should I sell first or buy first?",
     "If you buy another HDB flat first, you usually have 6 months after the purchase to sell your current flat. For the Silver Housing Bonus, you must book or buy the next flat before selling, or within 12 months after the sale. Selling first gives you a firm budget but may need a short stay elsewhere; Serene can help you plan the timing."),
]


def gap_range(data, money):
    gaps = []
    for x in data.values():
        big = x["sale"].get("E") or x["sale"].get("5")
        if big and x["next"].get("3"):
            gaps.append(big[1] - x["next"]["3"][1])
    gaps = [g for g in gaps if g > 0]
    if not gaps:
        return "a gap that varies by town"
    lo, hi = round(min(gaps), -4), round(max(gaps), -4)
    return f"a gap of roughly {money(lo)} to {money(hi)}"


def render(data, meta, head, header, footer, esc, money):
    faqs = [(q, a.replace("a gap of roughly $230,000 to $510,000", gap_range(data, money))) for q, a in FAQS]
    t = "Right-Sizing in Woodlands, Sembawang & Yishun | Serene Lee"
    d = ("Children moved out? See what you could free up by moving to a smaller home in the North, renting out rooms "
         "or the Lease Buyback Scheme. Live HDB and URA prices.")
    h = re.sub(r"<title>.*?</title>", f"<title>{esc(t)}</title>", head, flags=re.S)
    h = re.sub(r'(<meta (?:name|property)="(?:description|og:description|twitter:description)" content=")[^"]*', lambda m: m.group(1) + esc(d), h)
    h = re.sub(r'(<meta (?:property|name)="(?:og:title|twitter:title)" content=")[^"]*', lambda m: m.group(1) + esc(t), h)
    h = re.sub(r'(<link rel="canonical" href=")[^"]*', r"\g<1>" + URL, h)
    h = re.sub(r'(<meta property="og:url" content=")[^"]*', r"\g<1>" + URL, h)
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]}
    h = h.replace("</head>", f'<script type="application/ld+json">{json.dumps(faq_ld)}</script>\n{CSS}\n</head>')

    # ---- town summary rows (static, readable by Google)
    rows = ""
    for slug, x in data.items():
        s, n = x["sale"], x["next"]
        big = s.get("E") or s.get("5")
        bl = "Executive" if s.get("E") else "5-room"
        gap3 = (big[1] - n["3"][1]) if big and n.get("3") else 0
        rows += (f"<tr><td><a href='/{slug}'><b>{esc(x['name'])}</b></a></td>"
                 f"<td class='r'>{money(s['4'][1]) if s.get('4') else '–'}</td>"
                 f"<td class='r'>{money(s['5'][1]) if s.get('5') else '–'}</td>"
                 f"<td class='r'>{money(s['E'][1]) if s.get('E') else '–'}</td>"
                 f"<td class='r'>{money(n['3'][1]) if n.get('3') else '–'}</td>"
                 f"<td class='r'>{money(n['2'][1]) if n.get('2') else '–'}</td>"
                 f"<td class='r'>{money(n['condo'][1]) if n.get('condo') else '–'}</td>"
                 f"<td class='r'><b>{money(gap3) if gap3 > 0 else '–'}</b><br><span class='rs-mut'>{bl} → 3-room</span></td></tr>")

    wa = lambda txt: "https://wa.me/6580868568?text=" + txt.replace(" ", "%20")
    faq_html = "".join(f"<h3>{esc(q)}</h3><p>{esc(a)}</p>" for q, a in faqs)
    opts = "".join(f'<option value="{k}">{esc(v["name"])}</option>' for k, v in data.items())

    body = f"""
<div class="page-hero page-hero-wide container">
  <span class="eyebrow">Right-sizing guide · North</span>
  <h1 style="font-size:2.1rem;">Children moved out? Your options in Woodlands, Sembawang and Yishun</h1>
  <p>Selling your bigger flat, renting out rooms, or unlocking cash from your lease: what each option could mean for you, with real prices from your own town.</p>
  <p class="rs-upd">HDB resale prices {esc(meta['hdb_from'])} to {esc(meta['hdb_month'])} (retrieved {esc(meta['hdb_date'])}) · URA data retrieved {esc(meta['ura_date'])} · Scheme rules checked {CHECKED}</p>
</div>

<section style="padding-top:12px;"><div class="container">

  <div class="rs-card rs-check"><h2>Is it a good time to think about right-sizing?</h2>
    <ul class="rs-ticks">
      <li>Your children have moved out, and 1 or 2 rooms are mostly empty</li>
      <li>You'd like more cash or CPF savings for retirement</li>
      <li>Cleaning, repairs and bills for a big flat feel like more work than they're worth</li>
      <li>You'd like to live nearer your children, a clinic or an MRT station</li>
      <li>You're 55 or above (several schemes start at 55, the Lease Buyback Scheme at 65)</li>
    </ul>
    <p class="rs-note">Two or more ticks? It's worth working out the numbers. There's no rush and no obligation.</p>
  </div>

  <div class="rs-card" id="rsCalc"><h2>What could you free up? Quick estimate</h2>
    <div class="rs-form">
      <div class="field"><label for="rsTown">Your town</label><select id="rsTown">{opts}</select></div>
      <div class="field"><label for="rsFrom">Your flat now</label><select id="rsFrom"></select></div>
      <div class="field"><label for="rsTo">Moving to</label><select id="rsTo"></select></div>
      <div class="field"><label for="rsLoan">Home loan left ($)</label><input type="number" id="rsLoan" min="0" step="1000" value="0" inputmode="numeric"></div>
      <div class="field"><label for="rsCpf">CPF used for this flat, incl. interest ($)</label><input type="number" id="rsCpf" min="0" step="1000" value="0" inputmode="numeric"></div>
      <div class="field"><label for="rsAge">Age of the youngest owner</label><select id="rsAge"><option value="50">Under 55</option><option value="55" selected>55 to 64</option><option value="65">65 and above</option></select></div>
    </div>
    <details class="rs-adv"><summary>Change the prices or costs used</summary>
      <div class="rs-form">
        <div class="field"><label for="rsSell">Your selling price ($)</label><input type="number" id="rsSell" step="1000" inputmode="numeric"></div>
        <div class="field"><label for="rsBuy">Next home price ($)</label><input type="number" id="rsBuy" step="1000" inputmode="numeric"></div>
        <div class="field"><label for="rsFee">Agent fee on your sale (%)</label><input type="number" id="rsFee" step="0.5" min="0" value="2"></div>
        <div class="field"><label for="rsMove">Moving, renovation and legal ($)</label><input type="number" id="rsMove" step="1000" min="0" value="20000"></div>
      </div>
    </details>
    <div id="rsOut" aria-live="polite"></div>
    <p class="rs-src">Prices are medians of actual resales in the last 12 months: HDB from <a href="{SRC['hdbdata']}" target="_blank" rel="noopener">data.gov.sg</a>; smaller condos are resale units up to {meta['small_sqm']} sqm (about 750 sqft) within 500 m of the town's HDB blocks, from <a href="{SRC['ura']}" target="_blank" rel="noopener">URA</a>. Stamp duty uses IRAS residential rates. This is a rough guide, not a valuation or financial advice: your own flat's floor, condition and lease change the numbers.</p>
  </div>

  <div class="rs-card"><h2>Typical prices in the North, last 12 months</h2>
    <div class="rs-tablewrap"><table class="rs-table"><thead><tr><th>Town</th><th class="r">4-room</th><th class="r">5-room</th><th class="r">Executive</th><th class="r">3-room</th><th class="r">2-room</th><th class="r">Smaller condo</th><th class="r">Possible gap</th></tr></thead>
    <tbody>{rows}</tbody></table></div>
    <p class="rs-src">Median resale prices, {esc(meta['hdb_from'])} to {esc(meta['hdb_month'])}. "Possible gap" is before agent fees, stamp duty, moving costs and CPF refunds. Tap a town for its full guide.</p>
  </div>

  <h2 class="rs-h2">Your four options</h2>
  <div class="rs-opts">
    <div class="rs-card rs-opt"><span class="rs-tag">Option 1</span><h3>Sell and buy a smaller resale home</h3>
      <p class="rs-who">Suits you if you want to move soon and choose your exact block and floor.</p>
      <ul>
        <li>Move to a 3-room or 2-room HDB flat, or a smaller condo, often in the same town</li>
        <li>Buying a 3-room or smaller HDB flat may qualify for the <b>Silver Housing Bonus</b> (see below)</li>
        <li>No resale levy when you buy an HDB resale flat without a grant</li>
        <li>Buying another HDB flat first? You usually have 6 months after buying to sell your current one</li>
        <li>Buying a condo before selling your HDB flat means paying Additional Buyer's Stamp Duty upfront (20% for Singapore Citizens on a second home); married couples can usually claim it back if the flat is sold within 6 months</li>
      </ul></div>
    <div class="rs-card rs-opt"><span class="rs-tag">Option 2</span><h3>Sell and buy a new flat from HDB</h3>
      <p class="rs-who">Suits you if you can wait for a new flat and want the lowest price.</p>
      <ul>
        <li><b>2-room Flexi on a short lease</b>: for buyers aged 55 and above; choose a lease of 15 to 45 years (in 5-year steps) that lasts until you are at least 95</li>
        <li><b>Community Care Apartments</b>: studio homes with care services built in; from the October 2026 sales exercise, open to buyers aged 55 and above (was 65)</li>
        <li>Household income ceiling $14,000 a month; you must sell your current flat within 6 months of completing the purchase</li>
        <li>Second-timers pay the lower of the resale levy or $30,000, pro-rated to the lease chosen</li>
        <li>Also qualifies for the Silver Housing Bonus (up to $40,000)</li>
      </ul></div>
    <div class="rs-card rs-opt"><span class="rs-tag">Option 3</span><h3>Keep your flat and rent out</h3>
      <p class="rs-who">Suits you if you'd rather stay put but want a monthly income.</p>
      <ul>
        <li><b>Rent out rooms</b>: 3-room flats can rent out 1 bedroom, 4-room and bigger up to 2. You must keep living in the flat, each tenancy is at least 6 months, and HDB approves each tenant first ($9 per bedroom)</li>
        <li><b>Rent out the whole flat</b>: possible if you live elsewhere (for example with your children), once the minimum occupation period is met and if all owners are Singapore Citizens; minimum 6 months per tenancy</li>
        <li>Rental income is taxable; keep records of repairs and agent fees</li>
        <li>Pros: keep your home and its value. Cons: less privacy, you're a landlord, and the lease keeps shortening</li>
      </ul>
      <div id="rsRent"></div></div>
    <div class="rs-card rs-opt"><span class="rs-tag">Option 4</span><h3>Keep your flat and sell part of the lease (Lease Buyback Scheme)</h3>
      <p class="rs-who">Suits you if you're 65+ and want to stay in your home for life.</p>
      <ul>
        <li>Sell the tail end of your lease to HDB and keep 15 to 35 years, depending on the youngest owner's age</li>
        <li>Proceeds first top up your CPF Retirement Account (one owner: to the Full Retirement Sum, $220,400 for ages 65–69 in 2026); you can keep up to $100,000 in cash</li>
        <li>LBS bonus up to $30,000 (3-room or smaller), $15,000 (4-room) or $7,500 (5-room and bigger)</li>
        <li>All flat types except short-lease flats; household income $14,000 a month or less; at least 20 years of lease left</li>
        <li>Pros: no moving. Cons: smaller payout than selling, and your flat can't be passed on with a full lease</li>
      </ul></div>
  </div>

  <div class="rs-card rs-bonus"><h2>Silver Housing Bonus: up to $40,000 when you move to a smaller flat</h2>
    <ul>
      <li>At least one owner is a Singapore Citizen aged 55 or above; household income $14,000 a month or less</li>
      <li>You sell an HDB flat (after its minimum occupation period) or a private home with an annual value of up to $31,000</li>
      <li>Your next home is a 3-room or smaller HDB flat (not a 3-room terrace), including 2-room Flexi and Community Care Apartments</li>
      <li>You commit sale proceeds to your CPF Retirement Account (up to $60,000 per household); CPF refunds count</li>
      <li><b>Amount:</b> up to $30,000 for a 3-room ($1 for every $2 committed); up to $40,000 for a 2-room or smaller (an extra $10,000 on top). Lower amounts apply if you sell a private home with annual value above $21,000</li>
      <li>Book or buy the next flat before selling, or within 12 months after the sale; apply within 1 year of the second transaction</li>
    </ul>
    <p class="rs-src">Enhanced from 1 Dec 2025. HDB decides eligibility and the final amount: <a href="{SRC['shb']}" target="_blank" rel="noopener">HDB Silver Housing Bonus</a>.</p>
  </div>

  <div class="rs-two">
    <div class="rs-card"><h2>Costs people often forget</h2>
      <ul>
        <li><b>CPF refund</b>: the CPF you used plus accrued interest goes back to your CPF, not your pocket. From 55, it first tops up your Retirement Account to the Full Retirement Sum; the rest stays in your Ordinary Account, which you can withdraw or use for the next home</li>
        <li><b>Agent fees</b> on your sale (plus GST)</li>
        <li><b>Buyer's stamp duty</b> on your next home</li>
        <li><b>Legal fees</b> for both the sale and the purchase</li>
        <li><b>Moving, renovation and new furniture</b></li>
        <li><b>Somewhere to stay</b> if your sale completes before your new home is ready</li>
      </ul></div>
    <div class="rs-card"><h2>A typical timeline</h2>
      <ol class="rs-steps">
        <li><b>Month 1:</b> work out your numbers (sale price, CPF refund, budget) and apply for your HDB Flat Eligibility (HFE) letter if buying HDB</li>
        <li><b>Months 1–2:</b> view smaller homes; book or buy the next flat first if you want the Silver Housing Bonus with the least risk</li>
        <li><b>Months 2–4:</b> list your flat; HDB resales usually complete about 8 weeks after the HDB application</li>
        <li><b>After both deals:</b> apply for the Silver Housing Bonus within 1 year</li>
      </ol>
      <p class="rs-src">Every household is different. Serene can map out sell-first or buy-first for you.</p></div>
  </div>

  <div class="rs-card rs-faq"><h2>Common questions</h2>{faq_html}</div>

  <div class="rs-card"><h2>Sources</h2>
    <p class="rs-src">Rules and amounts checked on {CHECKED} against: <a href="{SRC['shb']}" target="_blank" rel="noopener">HDB Silver Housing Bonus</a> · <a href="{SRC['lbs']}" target="_blank" rel="noopener">HDB Lease Buyback Scheme</a> · <a href="{SRC['new']}" target="_blank" rel="noopener">HDB buying a new flat as a senior</a> · <a href="{SRC['cca']}" target="_blank" rel="noopener">MOH Community Care Apartments</a> · <a href="{SRC['roomel']}" target="_blank" rel="noopener">HDB renting out a bedroom</a> · <a href="{SRC['room']}" target="_blank" rel="noopener">HDB bedroom rental terms</a> · <a href="{SRC['flat']}" target="_blank" rel="noopener">HDB rental regulations</a> · <a href="{SRC['cpf']}" target="_blank" rel="noopener">CPF selling your flat after 55</a> · Median rents: <a href="{esc(meta['rent_url'])}" target="_blank" rel="noopener">HDB public housing data, {esc(meta['rent_q'])}</a>. Rules change; please confirm with HDB, CPF Board or Serene before deciding. This page is general information, not financial or legal advice.</p>
  </div>
</div></section>

<section class="cta-banner"><div class="container cta-banner">
  <h2>Want a right-sizing plan for your own flat?</h2>
  <div class="btns">
    <a href="/market-map" class="btn btn-navy">Check My Block's Prices</a>
    <a href="{wa('Hi Serene, my children have moved out and I am thinking of right-sizing. Could you work out my options?')}" target="_blank" rel="noopener" class="btn" style="background:#fff;color:var(--navy-900);" data-rs="cta">Get a Free Right-Sizing Plan</a>
  </div>
</div></section>
<script>
(function(){{
var D={json.dumps(data, separators=(',', ':'))}, RENTQ={json.dumps(meta['rent_q'])};
var FT={json.dumps(FT)}, TO={{"3":"3-room HDB (resale)","2":"2-room HDB (resale)","condo":"Smaller condo (resale, up to 70 sqm)"}};
function $(i){{return document.getElementById(i);}}
function m(v){{return "$"+Math.round(v).toLocaleString("en-SG");}}
function bsd(p){{var t=[[180000,.01],[180000,.02],[640000,.03],[500000,.04],[1500000,.05],[1e12,.06]],d=0,r=p;for(var i=0;i<t.length&&r>0;i++){{var x=Math.min(r,t[i][0]);d+=x*t[i][1];r-=x;}}return d;}}
function track(e,p){{try{{window.posthog&&posthog.capture(e,p);}}catch(x){{}}}}
var touched={{sell:false,buy:false}};
function fill(){{var t=D[$("rsTown").value],f=$("rsFrom"),to=$("rsTo"),pf=f.value,pt=to.value;
  f.innerHTML=["E","5","4","3"].filter(function(k){{return t.sale[k];}}).map(function(k){{return '<option value="'+k+'">'+FT[k]+'</option>';}}).join("");
  to.innerHTML=["3","2","condo"].filter(function(k){{return t.next[k];}}).map(function(k){{return '<option value="'+k+'">'+TO[k]+'</option>';}}).join("");
  if(pf&&t.sale[pf])f.value=pf;else if(t.sale.E)f.value="E";else if(t.sale["5"])f.value="5";
  if(pt&&t.next[pt])to.value=pt;
  touched.sell=touched.buy=false;calc();}}
function calc(){{var t=D[$("rsTown").value],fk=$("rsFrom").value,tk=$("rsTo").value;if(!t.sale[fk]||!t.next[tk])return;
  if(!touched.sell)$("rsSell").value=t.sale[fk][1];if(!touched.buy)$("rsBuy").value=t.next[tk][1];
  var sell=+$("rsSell").value||0,buy=+$("rsBuy").value||0,loan=+$("rsLoan").value||0,cpf=+$("rsCpf").value||0,age=+$("rsAge").value;
  var fee=sell*(+$("rsFee").value||0)/100*1.09,duty=bsd(buy),move=+$("rsMove").value||0;
  var left=sell-loan-buy-fee-duty-move;
  var shb=0,shbTxt="";
  if(age>=55&&(tk==="3"||tk==="2")){{shb=tk==="2"?40000:30000;shbTxt='Plus a possible <b>Silver Housing Bonus of up to '+m(shb)+'</b> if you commit enough to your CPF Retirement Account (conditions apply).';}}
  else if(tk==="condo")shbTxt="A condo does not qualify for the Silver Housing Bonus.";
  else shbTxt="The Silver Housing Bonus starts at age 55.";
  var h='<div class="rs-res"><div class="rs-big"><div class="k">Estimated money freed up</div><div class="v'+(left<0?' neg':'')+'">'+(left<0?"− ":"")+m(Math.abs(left))+'</div>'
   +'<div class="s">'+FT[fk]+' in '+t.name+' → '+TO[tk]+'</div></div><table class="rs-break"><tbody>'
   +'<tr><td>Typical sale price ('+FT[fk]+', '+t.sale[fk][0]+' resales)</td><td class="r">'+m(sell)+'</td></tr>'
   +(loan?'<tr><td>Less home loan left</td><td class="r">− '+m(loan)+'</td></tr>':'')
   +'<tr><td>Less next home ('+t.next[tk][0]+' resales)</td><td class="r">− '+m(buy)+'</td></tr>'
   +'<tr><td>Less agent fee incl. GST</td><td class="r">− '+m(fee)+'</td></tr>'
   +'<tr><td>Less buyer\\'s stamp duty</td><td class="r">− '+m(duty)+'</td></tr>'
   +'<tr><td>Less moving, renovation, legal</td><td class="r">− '+m(move)+'</td></tr></tbody></table></div>';
  var notes=[];
  if(cpf>0){{var back=Math.min(cpf,Math.max(sell-loan,0));notes.push('Of this, about <b>'+m(back)+'</b> goes back to your CPF first (the CPF you used plus interest), not to you in cash. '+(age>=55?'From 55, it tops up your Retirement Account to the Full Retirement Sum; any balance stays in your Ordinary Account, which you can withdraw or use for the next home.':'Under 55, it goes to your Ordinary Account and can pay for the next home.'));}}
  else notes.push('Add the CPF you used for this flat (see your Home Ownership Dashboard on the CPF website) to see how much returns to CPF rather than cash.');
  notes.push(shbTxt);
  if(left<0)notes.push('The next home costs more than you would free up at these prices. Try a smaller home, or ask Serene to check your actual flat value.');
  h+='<ul class="rs-notes">'+notes.map(function(x){{return '<li>'+x+'</li>';}}).join("")+'</ul>'
   +'<a class="btn btn-gold" target="_blank" rel="noopener" id="rsWa" href="https://wa.me/6580868568?text='+encodeURIComponent("Hi Serene, I used your right-sizing estimate: "+FT[fk]+" in "+t.name+" to "+TO[tk]+". Could you work out my actual numbers?")+'">Get my actual numbers</a>';
  $("rsOut").innerHTML=h;
  $("rsWa").onclick=function(){{track("whatsapp_clicked",{{button_text:"Get my actual numbers",button_location:"right-sizing estimator",page_path:location.pathname}});}};
  var r=t.rent[fk];$("rsRent").innerHTML=r?'<p class="rs-rent">Whole '+FT[fk]+' flats in '+t.name+' rented for a median <b>'+m(r)+' a month</b> ('+RENTQ+', HDB). Room rents are lower and vary.</p>':'';
}}
["rsTown"].forEach(function(i){{$(i).addEventListener("change",function(){{fill();track("rightsizing_estimate",{{town:$("rsTown").value}});}});}});
["rsFrom","rsTo"].forEach(function(i){{$(i).addEventListener("change",function(){{touched.sell=touched.buy=false;calc();track("rightsizing_estimate",{{town:$("rsTown").value,from:$("rsFrom").value,to:$("rsTo").value}});}});}});
$("rsSell").addEventListener("input",function(){{touched.sell=true;calc();}});$("rsBuy").addEventListener("input",function(){{touched.buy=true;calc();}});
["rsLoan","rsCpf","rsAge","rsFee","rsMove"].forEach(function(i){{$(i).addEventListener("input",calc);$(i).addEventListener("change",calc);}});
var q=new URLSearchParams(location.search).get("town");if(q&&D[q])$("rsTown").value=q;
fill();
var c=document.querySelector('[data-rs="cta"]');if(c)c.onclick=function(){{track("whatsapp_clicked",{{button_text:"Get a Free Right-Sizing Plan",button_location:"right-sizing cta",page_path:location.pathname}});}};
}})();
</script>
"""
    return h + header + body + footer


CSS = """<style>
.rs-upd{font-size:.82rem;color:var(--muted)}
.rs-card{background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:18px 20px;margin-bottom:20px;min-width:0}
.rs-card h2{font-size:1.2rem;margin:0 0 10px}
.rs-card h3{font-size:1.05rem;margin:4px 0 6px}
.rs-card ul,.rs-card ol{margin:0;padding-left:20px}
.rs-card li{margin:5px 0;font-size:.93rem}
.rs-h2{font-size:1.35rem;margin:28px 0 12px}
.rs-ticks{list-style:none;padding-left:0!important}
.rs-ticks li{padding-left:28px;position:relative}
.rs-ticks li:before{content:"\\2713";position:absolute;left:4px;color:var(--gold-dark,#a8861c);font-weight:700}
.rs-note{margin:10px 0 0;font-weight:600;color:var(--navy-900)}
.rs-form{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px 16px;margin-bottom:12px}
@media(max-width:760px){.rs-form{grid-template-columns:1fr 1fr}}
@media(max-width:460px){.rs-form{grid-template-columns:1fr}}
.rs-form .field{margin:0;min-width:0}
.rs-form select,.rs-form input{width:100%;min-width:0;border:1px solid var(--line);border-radius:10px;padding:10px 12px;font:inherit;background:#fff}
.rs-form label{display:block;font-size:.8rem;font-weight:600;color:var(--navy-900);margin-bottom:4px}
.rs-adv{margin:0 0 12px}
.rs-adv summary{cursor:pointer;font-weight:600;color:var(--navy-900);font-size:.88rem;margin-bottom:10px}
.rs-res{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.4fr);gap:16px;align-items:start;background:var(--cream);border-radius:12px;padding:16px}
@media(max-width:760px){.rs-res{grid-template-columns:1fr}}
.rs-big .k{font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.rs-big .v{font:600 2rem/1.2 'Fraunces',Georgia,serif;color:var(--navy-900);margin:4px 0;font-variant-numeric:tabular-nums}
.rs-big .v.neg{color:#b3412e}
.rs-big .s{font-size:.85rem;color:var(--muted)}
.rs-break{width:100%;border-collapse:collapse;font-size:.88rem}
.rs-break td{padding:5px 0;border-bottom:1px solid var(--line)}
.rs-break .r,.rs-table .r{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.rs-notes{margin:12px 0!important;font-size:.9rem}
.rs-rent{background:var(--cream);border-radius:10px;padding:10px 12px;margin:12px 0 0;font-size:.9rem}
.rs-src{font-size:.75rem;color:var(--muted);margin:10px 0 0;line-height:1.5}
.rs-src a{color:inherit}
.rs-tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px}
.rs-table{width:100%;border-collapse:collapse;font-size:.86rem}
.rs-table th{text-align:left;font-size:.7rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);background:var(--cream);padding:9px 12px;white-space:nowrap}
.rs-table td{padding:9px 12px;border-top:1px solid var(--line);vertical-align:top}
.rs-table a{color:var(--navy-900)}
.rs-mut{color:var(--muted);font-size:.76rem}
.rs-opts{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px;margin-bottom:20px}
@media(max-width:860px){.rs-opts{grid-template-columns:1fr}}
.rs-opts .rs-card{margin-bottom:0}
.rs-tag{display:inline-block;font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;background:var(--gold);color:var(--navy-900);border-radius:999px;padding:3px 10px}
.rs-who{color:var(--muted);font-size:.9rem;margin:0 0 8px}
.rs-bonus{border-color:var(--gold)}
.rs-two{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px;margin-bottom:20px}
.rs-two .rs-card{margin-bottom:0}
@media(max-width:860px){.rs-two{grid-template-columns:1fr}}
.rs-steps li{margin:8px 0}
.rs-faq h3{font-size:1rem;margin:16px 0 4px}
.rs-faq p{color:var(--muted);font-size:.92rem;margin:0;max-width:820px}
</style>"""
