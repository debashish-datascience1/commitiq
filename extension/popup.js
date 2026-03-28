const SERVER = "https://commitiq-production.up.railway.app";  // your deployed backend

// ── DOM refs ──────────────────────────────────────────────────────────────────
const setupScreen  = document.getElementById("setup-screen");
const chatScreen   = document.getElementById("chat-screen");
const inputUsername = document.getElementById("input-username");
const inputToken   = document.getElementById("input-token");
const toggleToken  = document.getElementById("toggle-token");
const setupSave    = document.getElementById("setup-save");
const setupError   = document.getElementById("setup-error");
const settingsBtn  = document.getElementById("settings-btn");
const headerUser   = document.getElementById("header-username");
const messagesEl   = document.getElementById("messages");
const inputEl      = document.getElementById("input");
const sendBtn      = document.getElementById("send-btn");
const chipsEl      = document.getElementById("chips");
const statusDot    = document.getElementById("status-dot");
const offlineBanner = document.getElementById("offline-banner");

let GH_TOKEN    = null;
let GH_USERNAME = null;
let SESSION_ID  = null;
let history     = [];

// ── Boot: load saved credentials & session ────────────────────────────────────
chrome.storage.local.get(["commitiq_creds", "commitiq_session", "commitiq_history"], (res) => {
  const creds = res.commitiq_creds;
  SESSION_ID  = res.commitiq_session || "ext-" + Math.random().toString(36).slice(2);
  history     = res.commitiq_history || [];

  chrome.storage.local.set({ commitiq_session: SESSION_ID });

  if (creds && creds.token && creds.username) {
    GH_TOKEN    = creds.token;
    GH_USERNAME = creds.username;
    showChat();
  } else {
    showSetup();
  }
});

// ── Setup screen ──────────────────────────────────────────────────────────────
function showSetup(prefill = {}) {
  setupScreen.style.display = "flex";
  chatScreen.style.display  = "none";
  if (prefill.username) inputUsername.value = prefill.username;
  setupError.style.display = "none";
}

function showChat() {
  setupScreen.style.display = "none";
  chatScreen.style.display  = "flex";
  headerUser.textContent    = "@" + GH_USERNAME;

  if (history.length > 0) {
    const welcome = messagesEl.querySelector(".welcome");
    if (welcome) welcome.remove();
    history.forEach(({ text, role }) => appendBubble(text, role));
  } else {
    setTimeout(() => sendMessage("hi"), 100);
  }
}

toggleToken.addEventListener("click", () => {
  const show = inputToken.type === "password";
  inputToken.type = show ? "text" : "password";
  toggleToken.textContent = show ? "🙈" : "👁";
});

setupSave.addEventListener("click", async () => {
  const username = inputUsername.value.trim();
  const token    = inputToken.value.trim();

  if (!username || !token) {
    showSetupError("Please fill in both fields.");
    return;
  }
  if (!token.startsWith("ghp_") && !token.startsWith("github_pat_") && token.length < 20) {
    showSetupError("That doesn't look like a valid GitHub token.");
    return;
  }

  setupSave.disabled = true;
  setupSave.textContent = "Verifying…";
  setupError.style.display = "none";

  // Verify token by hitting the GitHub API
  try {
    const res = await fetch(`https://api.github.com/users/${username}`, {
      headers: { Authorization: `token ${token}`, Accept: "application/vnd.github.v3+json" },
    });
    if (!res.ok) throw new Error("Invalid credentials");

    GH_TOKEN    = token;
    GH_USERNAME = username;

    chrome.storage.local.set({
      commitiq_creds: { token, username },
      commitiq_history: [],
      commitiq_session: SESSION_ID,
    });

    history = [];
    messagesEl.innerHTML = `
      <div class="welcome">
        <div class="icon">🚀</div>
        <h2>CommitIQ</h2>
        <p>Browse repos, manage issues,<br>and make commits — no WhatsApp needed.</p>
      </div>`;

    showChat();

  } catch (err) {
    showSetupError("Could not verify credentials. Check your username and token.");
  }

  setupSave.disabled = false;
  setupSave.textContent = "Connect →";
});

function showSetupError(msg) {
  setupError.textContent = msg;
  setupError.style.display = "block";
}

// Settings gear → go back to setup screen pre-filled
settingsBtn.addEventListener("click", () => {
  showSetup({ username: GH_USERNAME });
});

// ── Quick-reply chips ─────────────────────────────────────────────────────────
const CHIP_MAP = [
  { match: "1 — Yes, let",                  chips: ["1", "2"] },
  { match: "number of the repo",            chips: [] },
  { match: "View & manage issues",          chips: ["1", "2", "0"] },
  { match: "issue number",                  chips: ["N", "0"] },
  { match: "Create a New Issue",            chips: [] },
  { match: "description of the issue",      chips: ["skip"] },
  { match: "Add a blank line",              chips: ["1", "2", "0"] },
  { match: "comment say",                   chips: [] },
  { match: "commit message",                chips: [] },
  { match: "view issues, 2 to make another", chips: ["1", "2", "0"] },
];

const CHIP_LABELS = {
  "1": "1 — Yes / Select",
  "2": "2 — No / Commit",
  "0": "0 — Back",
  "N": "N — New issue",
  "skip": "skip",
};

function setChips(botText) {
  chipsEl.innerHTML = "";
  const plain = botText.replace(/\*/g, "").replace(/_/g, "");
  for (const { match, chips } of CHIP_MAP) {
    if (plain.includes(match)) {
      chips.forEach(key => {
        const chip = document.createElement("button");
        chip.className = "chip";
        chip.textContent = CHIP_LABELS[key] || key;
        chip.onclick = () => sendMessage(key);
        chipsEl.appendChild(chip);
      });
      return;
    }
  }
}

// ── Rendering ─────────────────────────────────────────────────────────────────
function formatText(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*(.*?)\*/g, "<strong>$1</strong>")
    .replace(/_(.*?)_/g, "<em>$1</em>")
    .replace(/`(.*?)`/g, "<code>$1</code>")
    .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function appendBubble(text, role) {
  const welcome = messagesEl.querySelector(".welcome");
  if (welcome) welcome.remove();

  const row = document.createElement("div");
  row.className = `msg-row ${role}`;

  const avatar = document.createElement("div");
  avatar.className = `avatar ${role}`;
  avatar.textContent = role === "bot" ? "🤖" : "👤";

  const bubble = document.createElement("div");
  bubble.className = `bubble ${role}`;
  bubble.innerHTML = formatText(text);

  row.appendChild(avatar);
  row.appendChild(bubble);
  messagesEl.appendChild(row);
  scrollToBottom();
}

function showTyping() {
  const row = document.createElement("div");
  row.className = "typing-row";
  row.id = "typing";

  const avatar = document.createElement("div");
  avatar.className = "avatar bot";
  avatar.textContent = "🤖";

  const bubble = document.createElement("div");
  bubble.className = "typing-bubble";
  bubble.innerHTML = `<div class="dot"></div><div class="dot"></div><div class="dot"></div>`;

  row.appendChild(avatar);
  row.appendChild(bubble);
  messagesEl.appendChild(row);
  scrollToBottom();
}

function hideTyping() {
  const t = document.getElementById("typing");
  if (t) t.remove();
}

function setOnline(online) {
  statusDot.className = "status-dot" + (online ? "" : " offline");
  offlineBanner.style.display = online ? "none" : "block";
}

function saveHistory() {
  if (history.length > 60) history = history.slice(-60);
  chrome.storage.local.set({ commitiq_history: history });
}

// ── Send message ──────────────────────────────────────────────────────────────
async function sendMessage(text) {
  text = (text || inputEl.value).trim();
  if (!text) return;

  inputEl.value = "";
  inputEl.style.height = "auto";
  chipsEl.innerHTML = "";
  sendBtn.disabled = true;

  appendBubble(text, "user");
  history.push({ text, role: "user" });

  showTyping();

  try {
    const res = await fetch(`${SERVER}/api/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id:  SESSION_ID,
        message:     text,
        gh_token:    GH_TOKEN,
        gh_username: GH_USERNAME,
      }),
    });

    const data = await res.json();
    hideTyping();
    setOnline(true);

    let lastBotText = "";
    for (const msg of data.responses) {
      appendBubble(msg, "bot");
      history.push({ text: msg, role: "bot" });
      lastBotText = msg;
    }

    saveHistory();
    if (lastBotText) setChips(lastBotText);

  } catch (err) {
    hideTyping();
    setOnline(false);
    appendBubble("❌ Cannot reach the server.\nMake sure Flask is running:\n  python app.py", "bot");
  }

  sendBtn.disabled = false;
  inputEl.focus();
}

// ── Input events ──────────────────────────────────────────────────────────────
inputEl.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

inputEl.addEventListener("input", () => {
  inputEl.style.height = "auto";
  inputEl.style.height = Math.min(inputEl.scrollHeight, 90) + "px";
});

sendBtn.addEventListener("click", () => sendMessage());
