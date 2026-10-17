/* Site-wide AI chat widget — floating bubble (bottom-left) that opens a panel
   talking to /api/chat (a Cloudflare Pages Function backed by Claude).
   Include this file on every page, after main.js:
     <script src="chatbot.js"></script>
   No page-specific markup needed — this builds its own DOM on load. */
(function () {
  "use strict";

  /* Phone check: Singapore mobiles are 8 digits starting with 8 or 9 (optional
     +65). Overseas numbers must start with + and a country code. Obvious fakes
     (all one digit, running sequences, the form's example number) are refused.
     This checks the number is real-looking; it cannot prove the visitor owns it
     (that would need an SMS code). */
  function checkPhone(raw) {
    var s = String(raw || "").trim();
    var plus = s.charAt(0) === "+";
    var d = s.replace(/[^0-9]/g, "");
    if (/[a-z]/i.test(s)) return { ok: false, msg: "Please enter numbers only." };
    if (plus && d.indexOf("65") === 0) { d = d.slice(2); plus = false; }
    else if (!plus && d.length === 10 && d.indexOf("65") === 0) d = d.slice(2);
    if (!plus) {
      if (d.length !== 8) return { ok: false, msg: "Singapore mobile numbers have 8 digits, e.g. 9xxx xxxx." };
      if (!/^[89]/.test(d)) return { ok: false, msg: "Please enter a mobile number starting with 8 or 9." };
      var fake = /^(\d)\1{7}$/.test(d) || "0123456789".indexOf(d.slice(1)) >= 0 || "9876543210".indexOf(d.slice(1)) >= 0 ||
        ["91234567", "81234567", "98765432", "87654321", "90000000", "80000000", "91111111", "81111111"].indexOf(d) >= 0 ||
        /^(\d\d)\1{3}$/.test(d) || /^(\d{4})\1$/.test(d);
      if (fake) return { ok: false, msg: "That number doesn't look real. Please enter your actual mobile number." };
      return { ok: true, phone: "+65 " + d.slice(0, 4) + " " + d.slice(4), overseas: false };
    }
    if (d.length < 8 || d.length > 15 || /^0/.test(d) || /^(\d)\1+$/.test(d)) return { ok: false, msg: "Please enter a valid number with country code, e.g. +60 12 345 6789." };
    return { ok: true, phone: "+" + d, overseas: true };
  }
  function checkName(raw) {
    var n = String(raw || "").replace(/\s+/g, " ").trim();
    if (n.length < 2 || n.length > 60) return { ok: false, msg: "Please enter your name." };
    if (/[0-9@<>]/.test(n) || /^(test|asdf|abc|na|nil|none|anonymous|xxx+)$/i.test(n)) return { ok: false, msg: "Please enter your real name." };
    return { ok: true, name: n };
  }

  // How many questions a visitor can ask before we ask for name + mobile.
  var FREE_QUESTIONS = 3;
  var LEAD_KEY = "sl_chat_lead";
  function loadLead() {
    try { var l = JSON.parse(localStorage.getItem(LEAD_KEY) || "null"); return l && l.name && l.phone ? l : null; } catch (e) { return null; }
  }
  function saveLead(l) { try { localStorage.setItem(LEAD_KEY, JSON.stringify(l)); } catch (e) {} }

  function init() {
    if (document.getElementById("chatbotFab")) return; // already injected

    var wrap = document.createElement("div");
    wrap.innerHTML =
      '<button id="chatbotFab" class="chatbot-fab" aria-label="Chat with Serene\'s assistant">' +
      '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>' +
      '</button>' +
      '<div id="chatbotPanel" class="chatbot-panel" hidden>' +
      '<div class="chatbot-header">' +
      '<div><div class="chatbot-title">Ask Serene’s Assistant</div><div class="chatbot-subtitle">Usually replies in seconds</div></div>' +
      '<button id="chatbotClose" class="chatbot-close" aria-label="Close chat">&times;</button>' +
      "</div>" +
      '<div id="chatbotMessages" class="chatbot-messages"></div>' +
      '<div class="chatbot-input-row">' +
      '<textarea id="chatbotInput" class="chatbot-input" placeholder="Ask about MOP, new launches, financing…" rows="1"></textarea>' +
      '<button id="chatbotSend" class="chatbot-send" aria-label="Send">' +
      '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M3 20l18-8L3 4v6l12 2-12 2z"/></svg>' +
      "</button>" +
      "</div>" +
      '<div class="chatbot-disclaimer">AI assistant · general info only, not financial or legal advice. Contact details you share go to Serene so she can follow up. <a href="/privacy" target="_blank" rel="noopener">Privacy</a></div>' +
      "</div>";
    document.body.appendChild(wrap);

    var fab = document.getElementById("chatbotFab");
    var panel = document.getElementById("chatbotPanel");
    var closeBtn = document.getElementById("chatbotClose");
    var messagesEl = document.getElementById("chatbotMessages");
    var input = document.getElementById("chatbotInput");
    var sendBtn = document.getElementById("chatbotSend");

    var history = []; // { role: 'user' | 'assistant', content: string }
    var sending = false;
    var opened = false;
    var lead = loadLead();
    var leadFormEl = null;
    var DEFAULT_PH = input.placeholder;

    function userCount() { return history.filter(function (m) { return m.role === "user"; }).length; }
    function needLead() { return !lead && userCount() >= FREE_QUESTIONS; }
    function lockInput(on) {
      input.disabled = on; sendBtn.disabled = on;
      input.placeholder = on ? "Share your name and mobile above to continue" : DEFAULT_PH;
    }

    function showLeadForm() {
      lockInput(true);
      if (leadFormEl) { leadFormEl.scrollIntoView({ block: "nearest" }); return; }
      var box = document.createElement("form");
      box.className = "chatbot-msg chatbot-msg-bot chatbot-lead";
      box.setAttribute("novalidate", "");
      box.innerHTML =
        '<p>Happy to keep helping! So Serene can follow up with the right figures if needed, may I have your name and mobile number?</p>' +
        '<label>Name<input type="text" name="name" autocomplete="name" maxlength="60" required></label>' +
        '<label>Mobile number<input type="tel" name="phone" autocomplete="tel" inputmode="tel" placeholder="e.g. 8xxx xxxx" maxlength="20" required></label>' +
        '<div class="chatbot-lead-err" role="alert"></div>' +
        '<button type="submit" class="chatbot-lead-btn">Continue</button>' +
        '<p class="chatbot-lead-note">Serene Lee (ERA Realty) may contact you about your enquiry. See our <a href="/privacy" target="_blank" rel="noopener">Privacy Policy</a>.</p>';
      messagesEl.appendChild(box);
      messagesEl.scrollTop = messagesEl.scrollHeight;
      leadFormEl = box;
      var err = box.querySelector(".chatbot-lead-err");
      box.querySelector('[name="name"]').focus();
      box.addEventListener("submit", async function (e) {
        e.preventDefault();
        var n = checkName(box.name.value), ph = checkPhone(box.phone.value);
        if (!n.ok) { err.textContent = n.msg; box.name.focus(); return; }
        if (!ph.ok) { err.textContent = ph.msg; box.phone.focus(); return; }
        err.textContent = "";
        var btn = box.querySelector(".chatbot-lead-btn");
        btn.disabled = true; btn.textContent = "Saving…";
        try {
          var res = await fetch("/api/chat-lead", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: n.name, phone: ph.phone, messages: history, page: window.location.href }),
          });
          var data = await res.json().catch(function () { return {}; });
          if (!res.ok || !data.ok) { err.textContent = data.error || "Couldn't save that. Please check your number and try again."; btn.disabled = false; btn.textContent = "Continue"; return; }
          lead = { name: n.name, phone: data.phone || ph.phone };
          saveLead(lead);
          box.remove(); leadFormEl = null;
          lockInput(false);
          addBubble("assistant", "Thanks, " + n.name.split(" ")[0] + "! What would you like to know next? If you'd rather talk to Serene directly, tap below to continue on WhatsApp.");
          var asked = history.filter(function (m) { return m.role === "user"; }).map(function (m) { return m.content.replace(/\s+/g, " ").slice(0, 120); });
          var wa = document.createElement("a");
          wa.className = "chatbot-wa";
          wa.target = "_blank"; wa.rel = "noopener";
          wa.href = "https://wa.me/6580868568?text=" + encodeURIComponent("Hi Serene, I'm " + n.name + ". I was asking your website assistant about: " + asked.join(" / "));
          wa.textContent = "Continue with Serene on WhatsApp";
          wa.addEventListener("click", function () { try { window.posthog && posthog.capture("chatbot_whatsapp_click"); } catch (x) {} });
          messagesEl.appendChild(wa);
          messagesEl.scrollTop = messagesEl.scrollHeight;
          try { window.posthog && posthog.capture("chatbot_lead_captured", { overseas: !!ph.overseas }); } catch (x) {}
          input.focus();
        } catch (x) {
          err.textContent = "Couldn't reach the server. Please try again, or WhatsApp Serene at +65 8086 8568.";
          btn.disabled = false; btn.textContent = "Continue";
        }
      });
      try { window.posthog && posthog.capture("chatbot_lead_form_shown"); } catch (x) {}
    }

    function addBubble(role, text) {
      var bubble = document.createElement("div");
      bubble.className = "chatbot-msg " + (role === "user" ? "chatbot-msg-user" : "chatbot-msg-bot");
      bubble.textContent = text;
      messagesEl.appendChild(bubble);
      messagesEl.scrollTop = messagesEl.scrollHeight;
      return bubble;
    }

    function addWelcome() {
      addBubble(
        "assistant",
        "Hi! I'm Serene's website assistant. Ask me about recent HDB resale or condo prices (e.g. a 4-room in Woodlands), HDB upgrading, financing, or current new launches."
      );
    }

    function showTyping() {
      var typing = document.createElement("div");
      typing.className = "chatbot-msg chatbot-msg-bot chatbot-typing";
      typing.id = "chatbotTyping";
      typing.innerHTML = "<span></span><span></span><span></span>";
      messagesEl.appendChild(typing);
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function hideTyping() {
      var typing = document.getElementById("chatbotTyping");
      if (typing) typing.remove();
    }

    function autoResize() {
      input.style.height = "auto";
      input.style.height = Math.min(input.scrollHeight, 110) + "px";
    }

    async function sendMessage() {
      var text = input.value.trim();
      if (!text || sending) return;
      if (needLead()) { showLeadForm(); return; } // keep their typed question until details are in

      addBubble("user", text);
      history.push({ role: "user", content: text });
      input.value = "";
      autoResize();
      sending = true;
      sendBtn.disabled = true;
      showTyping();

      try {
        var res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ messages: history, page: window.location.href, lead: lead }),
        });
        var data = await res.json();
        hideTyping();

        if (data.needLead) {
          // Server says details are needed first: take the question back so it can be re-sent
          history.pop();
          var bubbles = messagesEl.querySelectorAll(".chatbot-msg-user");
          if (bubbles.length) bubbles[bubbles.length - 1].remove();
          input.value = text;
          lead = null; saveLead(null);
          showLeadForm();
        } else if (!res.ok || data.error) {
          addBubble("assistant", data.error || "Something went wrong — please try again or WhatsApp Serene directly.");
        } else {
          addBubble("assistant", data.reply);
          history.push({ role: "assistant", content: data.reply });
        }
      } catch (err) {
        hideTyping();
        addBubble("assistant", "I couldn't reach the server — please try again or WhatsApp Serene directly.");
      } finally {
        sending = false;
        if (needLead()) showLeadForm();
        else { sendBtn.disabled = false; input.focus(); }
      }
    }

    fab.addEventListener("click", function () {
      panel.hidden = !panel.hidden;
      if (!panel.hidden) {
        fab.classList.add("chatbot-fab-open");
        if (!opened) {
          opened = true;
          addWelcome();
        }
        input.focus();
      } else {
        fab.classList.remove("chatbot-fab-open");
      }
    });

    closeBtn.addEventListener("click", function () {
      panel.hidden = true;
      fab.classList.remove("chatbot-fab-open");
    });

    sendBtn.addEventListener("click", sendMessage);
    input.addEventListener("input", autoResize);
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
