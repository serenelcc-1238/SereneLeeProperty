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
