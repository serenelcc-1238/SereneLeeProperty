/* Site-wide AI chat widget — floating bubble (bottom-left) that opens a panel
   talking to /api/chat (a Cloudflare Pages Function backed by Claude).
   Include this file on every page, after main.js:
     <script src="chatbot.js"></script>
   No page-specific markup needed — this builds its own DOM on load. */
(function () {
  "use strict";

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
      '<div class="chatbot-disclaimer">AI assistant · general info only, not financial or legal advice.</div>' +
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
        "Hi! I'm Serene's website assistant. Ask me about HDB upgrading, MOP, financing, or her current new launches — or I can point you to the right page."
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
          body: JSON.stringify({ messages: history, page: window.location.href }),
        });
        var data = await res.json();
        hideTyping();

        if (!res.ok || data.error) {
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
        sendBtn.disabled = false;
        input.focus();
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
