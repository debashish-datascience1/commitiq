# 🤖 CommitIQ

> Your AI-powered GitHub assistant — available on WhatsApp, Web, and as a Chrome Extension.

[![Python](https://img.shields.io/badge/Python-3.9+-blue?style=flat-square&logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-Web%20UI-lightgrey?style=flat-square&logo=flask)](https://flask.palletsprojects.com)
[![Chrome Extension](https://img.shields.io/badge/Chrome-Extension-yellow?style=flat-square&logo=googlechrome)](https://developer.chrome.com/docs/extensions/)
[![Twilio](https://img.shields.io/badge/Twilio-WhatsApp-red?style=flat-square&logo=twilio)](https://twilio.com)
[![GitHub API](https://img.shields.io/badge/GitHub-API-black?style=flat-square&logo=github)](https://docs.github.com/en/rest)
[![AWS Bedrock](https://img.shields.io/badge/AWS-Bedrock-orange?style=flat-square&logo=amazonaws)](https://aws.amazon.com/bedrock/)
[![Railway](https://img.shields.io/badge/Deployed-Railway-purple?style=flat-square&logo=railway)](https://railway.app)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

---

## 📌 What is CommitIQ?

**CommitIQ** is an intelligent developer assistant that connects to your GitHub account and keeps you on track with your projects. Browse repositories, manage issues with AI analysis, navigate files, and make commits — all through a conversational interface.

It works across **three interfaces**:
- 💬 **WhatsApp** (via Twilio) — the original chat experience
- 🌐 **Web UI** — browser-based chat, no WhatsApp needed
- 🧩 **Chrome Extension** — quick-access popup from any tab

---

## ✨ Features

### ✅ Done
- 📅 **Daily Reminder at 10 AM** — WhatsApp message every morning asking if you plan to work today
- 📁 **GitHub Repo Listing** — Fetches your 20 most recently updated repositories
- 🔀 **Repo Action Menu** — Choose between managing issues or making a commit
- 🐛 **Issue Management** — Browse open issues, view details, and create new issues
- 🤖 **AI Issue Analysis** — Powered by AWS Bedrock (Claude 3 Haiku): actionable fix suggestions
- 📂 **File Browser** — Navigate repo folders and files interactively
- 💾 **Commit from Chat** — Add a blank line or comment, write a commit message, push to GitHub
- 🌐 **Web Chat UI** — Full chat interface at `/chat`, no WhatsApp or Twilio required
- 🧩 **Chrome Extension** — Install as a browser extension, works with any user's GitHub account
- ☁️ **Cloud Deployed** — Hosted on Railway, accessible to any user anywhere

### 🚀 Upcoming Features (Roadmap)
- 🔧 **AI Auto-Fix Commits** — Describe the bug, AI writes the fix and commits it automatically
- 🐛 **AI Issue Resolver** — Apply a suggested fix directly to the codebase
- 🌿 **Branch Management** — Create, switch, and merge branches from chat
- 📝 **PR Creation** — Open pull requests with AI-generated descriptions
- 📊 **Commit Streak Tracking** — Track daily commit streaks like a coding fitness app
- 🔔 **Smart Notifications** — Get alerted when PRs are reviewed, issues opened, or CI/CD fails
- 📈 **Weekly Summary Reports** — Weekly digest of GitHub activity every Sunday
- 🔴 **Persistent Sessions** — Redis-backed sessions so state survives server restarts
- 📱 **Mobile Web App (PWA)** — Installable on Android/iOS home screen

---

## 🏗️ Project Architecture

```
commitiq/
├── app.py                  # Flask server — state machine, all routes
├── scheduler.py            # APScheduler — daily 10 AM WhatsApp reminder
├── github_helper.py        # GitHub REST API: repos, issues, files, commits
├── ai_helper.py            # AWS Bedrock (Claude 3 Haiku) — issue analysis
├── sessions.py             # In-memory session/state management per user
├── templates/
│   └── chat.html           # Web chat UI (served at /chat)
├── extension/
│   ├── manifest.json       # Chrome Extension manifest (v3)
│   ├── popup.html          # Extension popup shell
│   ├── popup.js            # Extension chat logic + GitHub credential flow
│   ├── popup.css           # Extension dark theme styles
│   ├── generate_icons.py   # Script to generate PNG icons
│   └── icons/              # Extension icons (16, 48, 128px)
├── Procfile                # Railway/Heroku deployment command
├── render.yaml             # Render one-click deployment config
├── requirements.txt        # Python dependencies
└── .env                    # Environment variables (never commit this)
```

---

## ⚙️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.9+ |
| Web Framework | Flask + Flask-CORS |
| WhatsApp API | Twilio WhatsApp Sandbox |
| Browser Extension | Chrome Extension (Manifest V3) |
| GitHub Integration | GitHub REST API v3 |
| AI | AWS Bedrock — Claude 3 Haiku |
| Scheduler | APScheduler |
| Deployment | Railway (cloud) / Gunicorn |
| Config | python-dotenv |

---

## 🚀 Getting Started

### Option A — Run Locally

#### Prerequisites
- Python 3.9+
- A [GitHub Personal Access Token](https://github.com/settings/tokens) (`repo` scope)
- AWS account with Bedrock access (for AI analysis)
- Twilio account (optional — only needed for WhatsApp reminders)

#### 1. Clone & Install
```bash
git clone https://github.com/YOUR_USERNAME/commitiq.git
cd commitiq
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 2. Configure Environment Variables
Create a `.env` file:
```env
GITHUB_USERNAME=your_github_username
GITHUB_TOKEN=your_github_personal_access_token

AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=ap-south-1

# Optional — only needed for WhatsApp reminders
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
USER_WHATSAPP_TO=whatsapp:+91XXXXXXXXXX

PORT=5001
```

#### 3. Run the Server
```bash
python app.py
```

#### 4. Access the Web UI
Open your browser at:
```
http://localhost:5001/chat
```

#### 5. (Optional) WhatsApp via Twilio
```bash
# Expose locally with ngrok
ngrok http 5001
```
Set the ngrok URL as webhook in **Twilio Console → Messaging → Sandbox Settings**:
```
https://<your-ngrok-id>.ngrok-free.app/webhook
```

#### 6. Test the Daily Reminder
```bash
curl http://localhost:5001/test-reminder
```

---

### Option B — Deploy to Railway (Cloud)

1. Install the [Railway CLI](https://docs.railway.app/develop/cli):
```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

2. In the Railway dashboard → your service → **Variables** tab, add:
```
GITHUB_TOKEN
GITHUB_USERNAME
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_REGION
```

3. Go to your service → **Settings** → **Networking** → **Generate Domain**

4. Your app is live at `https://your-app.up.railway.app/chat`

---

## 🧩 Chrome Extension — User Guide

The Chrome Extension lets anyone use CommitIQ directly from their browser without needing to set up a server.

### Installing the Extension (Developer Mode)

1. Download or clone this repository
2. Generate the extension icons (one-time):
```bash
python extension/generate_icons.py
```
3. Open Chrome and go to `chrome://extensions`
4. Enable **Developer mode** (toggle in the top-right)
5. Click **Load unpacked** and select the `extension/` folder
6. The CommitIQ icon will appear in your Chrome toolbar

### First-Time Setup

When you click the extension icon for the first time, you'll see a setup screen:

1. **GitHub Username** — your GitHub username (e.g. `octocat`)
2. **Personal Access Token** — click **"+ Create token"** to open GitHub's token page
   - Select `repo` scope
   - Generate and copy the token
3. Click **Connect** — your credentials are verified against GitHub and stored only in your browser

### Using the Extension

Once connected, you can:

| Action | How |
|---|---|
| Browse your repos | Reply `1` to start |
| View open issues | Select a repo → reply `1` |
| AI analysis of an issue | Select an issue number |
| Create a new issue | Reply `N` in the issues screen |
| Browse files & make a commit | Select a repo → reply `2` |
| Go back | Always reply `0` |
| Change GitHub account | Click the ⚙️ icon in the header |

### Quick-Reply Chips

The extension shows clickable shortcut buttons below the chat so you don't need to type numbers manually.

### Notes
- Your GitHub token is stored only in your browser (`chrome.storage.local`) — it is never stored on the server
- Chat history is preserved when you close and reopen the extension popup
- The extension requires the CommitIQ backend to be running (either locally or on Railway)

---

## 💬 Conversation Flow

```
Bot: "Do you want to commit today?"  1=Yes / 2=No
          │
          1
          │
     Repo list → pick a number
          │
     ┌────┴────────────┐
     1 (Issues)        2 (Commit)
     │                 │
     Issue list        File browser (folders + files)
     │                 │
     Pick issue        Navigate into folders (0 = go up)
     │                 │
     Issue details     Pick a file
     + AI analysis     │
     │                 1=Add blank line
     N = create        2=Add a comment → enter comment text
     new issue         │
                       Enter commit message
                       │
                       🚀 Committed to GitHub
```

---

## 🔐 Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `GITHUB_USERNAME` | Yes | Your GitHub username |
| `GITHUB_TOKEN` | Yes | GitHub Personal Access Token (`repo` scope) |
| `AWS_ACCESS_KEY_ID` | Yes | AWS credentials for Bedrock |
| `AWS_SECRET_ACCESS_KEY` | Yes | AWS credentials for Bedrock |
| `AWS_REGION` | Yes | AWS region where Bedrock is enabled (e.g. `ap-south-1`) |
| `TWILIO_ACCOUNT_SID` | Optional | Twilio Account SID (WhatsApp only) |
| `TWILIO_AUTH_TOKEN` | Optional | Twilio Auth Token (WhatsApp only) |
| `TWILIO_WHATSAPP_FROM` | Optional | Twilio sandbox WhatsApp number |
| `USER_WHATSAPP_TO` | Optional | Your personal WhatsApp number |
| `PORT` | Optional | Server port (default: 5001) |

---

## 🛣️ Roadmap

- [x] Daily WhatsApp reminder at 10 AM
- [x] GitHub repo listing
- [x] Repo action menu (Issues vs Commit)
- [x] View open issues with AI analysis (AWS Bedrock — Claude 3 Haiku)
- [x] Create new GitHub issues from chat
- [x] File browser — navigate folders and files interactively
- [x] Commit from chat — add blank line or comment, push with custom message
- [x] Web Chat UI — browser-based interface, no WhatsApp needed
- [x] Chrome Extension — install as browser extension with per-user GitHub credentials
- [x] Cloud deployment — hosted on Railway, accessible to anyone
- [ ] AI auto-fix commits (AI writes and commits the fix)
- [ ] AI issue resolver (apply suggested fix to codebase)
- [ ] Branch creation and management
- [ ] Pull request creation with AI-generated descriptions
- [ ] Commit streak tracker
- [ ] Weekly GitHub activity summary
- [ ] Redis-backed persistent sessions (survive server restarts)
- [ ] Mobile PWA (installable on Android/iOS)
- [ ] Chrome Web Store publication

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

> **CommitIQ** — Because great developers ship consistently, not occasionally.
