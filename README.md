# 🤖 CommitIQ

> Your AI-powered GitHub assistant on WhatsApp — stay consistent, commit smarter, and ship faster.

[![Python](https://img.shields.io/badge/Python-3.9+-blue?style=flat-square&logo=python)](https://python.org)
[![Twilio](https://img.shields.io/badge/Twilio-WhatsApp-red?style=flat-square&logo=twilio)](https://twilio.com)
[![GitHub API](https://img.shields.io/badge/GitHub-API-black?style=flat-square&logo=github)](https://docs.github.com/en/rest)
[![AWS Bedrock](https://img.shields.io/badge/AWS-Bedrock-orange?style=flat-square&logo=amazonaws)](https://aws.amazon.com/bedrock/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

---

## 📌 What is CommitIQ?

**CommitIQ** is an intelligent developer assistant that lives inside your WhatsApp. It connects to your GitHub account and keeps you on track with your projects — sending daily reminders, helping you navigate your repositories, letting you browse files, make commits, create and analyze issues with AI — all without leaving your phone.

---

## ✨ Features

### ✅ Done
- 📅 **Daily Reminder at 10 AM** — Sends a WhatsApp message every morning asking if you plan to work today
- 📁 **GitHub Repo Listing** — Fetches and displays your 20 most recently updated repositories
- 🔀 **Repo Action Menu** — After selecting a repo, choose between managing issues or making a commit
- 🐛 **Issue Management** — Browse open issues, view details, and create new issues directly from WhatsApp
- 🤖 **AI Issue Analysis** — Powered by AWS Bedrock (Claude 3 Haiku): get actionable fix suggestions for any open issue
- 📂 **File Browser** — Navigate your repo's folders and files interactively, going in and out of directories
- 💾 **Commit from WhatsApp** — Select any file, add a blank line or a comment (auto-detects syntax by file extension), write a commit message, and push — all from chat

### 🚀 Upcoming Features (Roadmap)
- 🔧 **AI Auto-Fix Commits** — Describe the bug, let AI write the fix and commit it automatically
- 🐛 **AI Issue Resolver** — Ask CommitIQ to apply a suggested fix directly to the codebase
- 🌿 **Branch Management** — Create, switch, and merge branches from WhatsApp
- 📝 **PR Creation** — Open pull requests with AI-generated descriptions from your chat
- 📊 **Commit Streak Tracking** — Track your daily commit streak like a coding fitness app
- 🔔 **Smart Notifications** — Get alerted when PRs are reviewed, issues are opened, or CI/CD fails
- 📈 **Weekly Summary Reports** — Receive a weekly digest of your GitHub activity every Sunday

---

## 🏗️ Project Architecture

```
commitiq/
├── app.py              # Flask server — state machine, webhook handler
├── scheduler.py        # APScheduler — sends daily 10 AM reminder
├── github_helper.py    # GitHub REST API: repos, issues, file contents, commits
├── ai_helper.py        # AWS Bedrock (Claude 3 Haiku) — issue analysis
├── sessions.py         # In-memory session/state management per user
├── .env                # Environment variables (never commit this)
├── requirements.txt    # Python dependencies
└── README.md
```

---

## ⚙️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.9+ |
| Web Framework | Flask |
| WhatsApp API | Twilio WhatsApp Sandbox |
| GitHub Integration | GitHub REST API v3 |
| AI | AWS Bedrock — Claude 3 Haiku (`anthropic.claude-3-haiku-20240307-v1:0`) |
| Scheduler | APScheduler |
| HTTP Client | Requests |
| Config | python-dotenv |
| Tunnel (dev) | Ngrok / Cloudflared |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- A [Twilio account](https://twilio.com) (free sandbox)
- A [GitHub Personal Access Token](https://github.com/settings/tokens) (repo scope)
- AWS account with Bedrock access enabled for Claude 3 Haiku in your region

### 1. Clone & Install
```bash
git clone https://github.com/YOUR_USERNAME/commitiq.git
cd commitiq
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
```env
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
USER_WHATSAPP_TO=whatsapp:+91XXXXXXXXXX

GITHUB_USERNAME=your_github_username
GITHUB_TOKEN=your_github_personal_access_token

AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=ap-south-1

PORT=5001
```

### 3. Run the Bot
```bash
# Terminal 1 — Start Flask
python app.py

# Terminal 2 — Expose locally with ngrok
ngrok http 5001
```

Set the ngrok URL as the webhook in **Twilio Console → Messaging → Sandbox Settings**:
```
https://<your-ngrok-id>.ngrok-free.app/webhook
```

### 4. Test Without Waiting for 10 AM
```bash
curl http://localhost:5001/test-reminder
```

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

| Variable | Description |
|---|---|
| `TWILIO_ACCOUNT_SID` | Your Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Your Twilio Auth Token |
| `TWILIO_WHATSAPP_FROM` | Twilio sandbox WhatsApp number |
| `USER_WHATSAPP_TO` | Your personal WhatsApp number |
| `GITHUB_USERNAME` | Your GitHub username |
| `GITHUB_TOKEN` | GitHub Personal Access Token (repo scope) |
| `AWS_ACCESS_KEY_ID` | AWS credentials for Bedrock |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials for Bedrock |
| `AWS_REGION` | AWS region where Bedrock is enabled (e.g. `ap-south-1`) |
| `PORT` | Flask server port (default: 5001) |

---

## 🛣️ Roadmap

- [x] Daily WhatsApp reminder at 10 AM
- [x] GitHub repo listing via WhatsApp
- [x] Repo action menu (Issues vs Commit)
- [x] View open issues with AI analysis (AWS Bedrock — Claude 3 Haiku)
- [x] Create new GitHub issues from WhatsApp
- [x] File browser — navigate folders and files interactively
- [x] Commit from WhatsApp — add blank line or comment, push with custom message
- [ ] AI auto-fix commits (AI writes and commits the fix)
- [ ] AI issue resolver (apply suggested fix to codebase)
- [ ] Branch creation and management
- [ ] Pull request creation with AI-generated descriptions
- [ ] Commit streak tracker
- [ ] Weekly activity summary
- [ ] Multi-user support
- [ ] Web dashboard for configuration

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

> **CommitIQ** — Because great developers ship consistently, not occasionally.
# hello this is a test
