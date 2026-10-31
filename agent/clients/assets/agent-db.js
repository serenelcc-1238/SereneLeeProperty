/* Connects the original "My Contact for Customers" app to Serene's own
   Cloudflare database (/agent/api/clients-sync), replacing Supabase.
   Sign-in is the Agent app password; the email box is ignored. */
(function () {
  const USER = { id: "serene-agent", email: "serene" };
  let session = null; const subs = [];
  const notify = () => subs.forEach((cb) => { try { cb(session ? "SIGNED_IN" : "SIGNED_OUT", session); } catch (e) {} });
  async function check() {
    try { const r = await fetch("/agent/api/clients-sync?limit=1", { credentials: "same-origin" }); return r.ok; } catch (e) { return !!session; }
  }
  const auth = {
    async getSession() { session = (await check()) ? { user: USER } : null; return { data: { session } }; },
    onAuthStateChange(cb) { subs.push(cb); return { data: { subscription: { unsubscribe() { const i = subs.indexOf(cb); if (i >= 0) subs.splice(i, 1); } } } }; },
    async signInWithPassword({ password }) {
      try {
        const r = await fetch("/agent/login", { method: "POST", body: new URLSearchParams({ password: password || "" }), credentials: "same-origin", redirect: "manual" });
        if (!(await check())) return { error: { message: "Invalid login credentials" } };
        session = { user: USER }; notify(); return { error: null };
      } catch (e) { return { error: { message: "You are offline. Connect to the internet to sign in." } }; }
    },
    async signOut() { try { await fetch("/agent/logout", { credentials: "same-origin", redirect: "manual" }); } catch (e) {} session = null; notify(); return { error: null }; }
  };
  function from(table) {
    if (table !== "clients") throw new Error("Unknown table " + table);
    return {
      select() {
        const q = { after: null, limit: 1000 };
        const b = {
          order() { return b; }, limit(n) { q.limit = n; return b; }, gt(col, v) { q.after = v; return b; },
          then(res, rej) {
            const u = "/agent/api/clients-sync?limit=" + q.limit + (q.after ? "&after=" + encodeURIComponent(q.after) : "");
            return fetch(u, { credentials: "same-origin" }).then(async (r) => {
              if (r.status === 401) { session = null; notify(); return { data: null, error: { message: "Signed out" } }; }
              if (!r.ok) return { data: null, error: { message: "Sync problem (" + r.status + ")" } };
              return { data: await r.json(), error: null };
            }, () => ({ data: null, error: { message: "Failed to fetch" } })).then(res, rej);
          }
        };
        return b;
      },
      async upsert(rows) {
        try {
          const r = await fetch("/agent/api/clients-sync", { method: "POST", credentials: "same-origin", headers: { "content-type": "application/json" }, body: JSON.stringify(rows) });
          if (r.status === 401) { session = null; notify(); return { error: { message: "Signed out" } }; }
          return r.ok ? { error: null } : { error: { message: "Sync problem (" + r.status + ")" } };
        } catch (e) { return { error: { message: "Failed to fetch" } }; }
      }
    };
  }
  window.__agentDb = { auth, from };
})();

/* Stamp duty helpers for the Purchase form (IRAS rates for residential
   property bought on/after 27 Apr 2023 / 15 Feb 2023 for BSD tiers). */
(function () {
  const num = (v) => { const n = Number(String(v || "").replace(/[^0-9.]/g, "")); return n > 0 ? n : 0; };
  const fmt = (n) => "S$" + Math.round(n).toLocaleString("en-SG");
  function bsdOf(p) {
    const tiers = [[180000, .01], [180000, .02], [640000, .03], [500000, .04], [1500000, .05], [Infinity, .06]];
    let left = p, t = 0;
    for (const [band, r] of tiers) { const x = Math.min(left, band); t += x * r; left -= x; if (left <= 0) break; }
    return Math.floor(t);
  }
  const RATES = ["0%", "5%", "20%", "30%", "35%", "60%"];
  function autoRate(e) {
    const c = e.citizenship || "", own = e.propertiesOwned || "";
    if (!c || own === "") return "";
    if (c === "Foreigner") return "60%";
    const i = own === "0" ? 0 : own === "1" ? 1 : 2;
    return (c === "Singapore PR" ? ["5%", "30%", "35%"] : ["0%", "20%", "30%"])[i];
  }
  const rateOf = (e) => e.absdRate || autoRate(e);
  window.__sd = {
    RATES,
    bsd: (e) => { const p = num(e.purchasePrice); return p ? String(bsdOf(p)) : ""; },
    bsdHint: (e) => num(e.purchasePrice) ? "Worked out from the purchase price (1% to 6% tiers). Type over it if the valuation is higher." : "Enter the purchase price to work this out.",
    rate: autoRate,
    rateHint: (e) => {
      const a = autoRate(e);
      return (a ? "Suggested from citizenship and properties owned: " + a + ". " : "Set citizenship and 'properties currently owned' to suggest a rate. ") +
        "SC 0/20/30%, PR 5/30/35%, foreigner 60%. Joint buyers pay the highest rate among them. Married couple with a Singapore Citizen spouse: 1st home remitted; 2nd home refundable if the 1st is sold within 6 months.";
    },
    absd: (e) => { const p = num(e.purchasePrice), r = parseFloat(rateOf(e)); return p && !isNaN(r) ? String(Math.floor(p * r / 100)) : ""; },
    absdHint: (e) => { const p = num(e.purchasePrice), r = parseFloat(rateOf(e)); return p && !isNaN(r) ? r + "% of " + fmt(p) : "Needs the purchase price and ABSD rate."; },
    total: (e) => { const b = num(e.bsd) || num(window.__sd.bsd(e)), a = num(e.absd) || num(window.__sd.absd(e)); return b || a ? String(b + a) : ""; }
  };
})();
