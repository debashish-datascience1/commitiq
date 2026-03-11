# 🤖 CommitIQ

> Your AI-powered GitHub assistant on WhatsApp — stay consistent, commit smarter, and ship faster.

[![Python](https://img.shields.io/badge/Python-3.9+-blue?style=flat-square&logo=python)](https://python.org)
[![Twilio](https://img.shields.io/badge/Twilio-WhatsApp-red?style=flat-square&logo=twilio)](https://twilio.com)
[![GitHub API](https://img.shields.io/badge/GitHub-API-black?style=flat-square&logo=github)](https://docs.github.com/en/rest)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

---

## 📌 What is CommitIQ?

**CommitIQ** is an intelligent developer assistant that lives inside your WhatsApp. It connects to your GitHub account and keeps you on track with your projects — sending daily reminders, helping you navigate your repositories, and (soon) letting you make commits, resolve issues, and get AI-powered code suggestions — all without leaving your phone.

Whether you're a solo developer trying to maintain consistency or a team lead who wants quick repo access on the go, CommitIQ brings your entire GitHub workflow to a single WhatsApp chat.

---

## ✨ Features

### ✅ Current Features
- 📅 **Daily Reminder at 10 AM** — Sends a WhatsApp message every morning asking if you plan to make any commits or modifications
- 📁 **GitHub Repo Listing** — Fetches and displays all your repositories when you're ready to work
- 🔗 **Quick Repo Access** — Select a repo by number and get the direct GitHub link instantly
- 🔐 **Secure via Environment Variables** — GitHub token and WhatsApp credentials stored safely in `.env`
- 💬 **Conversational Flow** — Simple yes/no interaction that feels natural on WhatsApp

### 🚀 Upcoming Features (Roadmap)
- 🤖 **AI-Powered Auto Commits** — Describe what you changed in plain English, and CommitIQ will generate the commit message and push it for you
- 🐛 **AI Issue Resolver** — Ask CommitIQ to analyze open GitHub issues and suggest or apply fixes automatically
- 📊 **Commit Streak Tracking** — Track your daily commit streak like a coding fitness app
- 🌿 **Branch Management** — Create, switch, and merge branches directly from WhatsApp
- 📝 **PR Creation** — Open pull requests with AI-generated descriptions from your chat
- 🔔 **Smart Notifications** — Get alerted when PRs are reviewed, issues are opened, or CI/CD fails
- 📈 **Weekly Summary Reports** — Receive a weekly digest of your GitHub activity every Sunday

---

## 🏗️ Project Architecture

```
commitiq/
├── app.py              # Flask server — handles incoming WhatsApp webhooks
├── scheduler.py        # APScheduler — sends daily 10 AM reminder
├── github_helper.py    # GitHub REST API integration
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
| Scheduler | APScheduler |
| HTTP Client | Requests |
| Config | python-dotenv |
| Tunnel (dev) | Ngrok / Cloudflared |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- A [Twilio account](https://twilio.com) (free)
- A [GitHub Personal Access Token](https://github.com/settings/tokens)
- WhatsApp on your phone

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/commitiq.git
cd commitiq
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory:
```env
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
USER_WHATSAPP_TO=whatsapp:+91XXXXXXXXXX

GITHUB_USERNAME=your_github_username
GITHUB_TOKEN=your_github_personal_access_token

PORT=5000
```

### 5. Activate Twilio WhatsApp Sandbox
1. Go to Twilio Console → **Messaging → Try it out → Send a WhatsApp message**
2. Send the join keyword to `+1 415 523 8886` from your WhatsApp
3. In **Sandbox Settings**, set the webhook URL to `https://your-ngrok-url/webhook`

### 6. Run the Bot
```bash
# Terminal 1 — Start Flask
python app.py

# Terminal 2 — Expose locally with ngrok
ngrok http 5000
```

### 7. Test Immediately
Visit this URL in your browser to trigger the reminder right away:
```
http://localhost:5000/test-reminder
```

---

## 💬 Conversation Flow

```
Bot: "Do you want to commit today?"
     1 — Yes, let's work!
     2 — No, not today
          │
     ┌────┴────┐
     1         2
     │         │
     ▼         ▼
 Repo list   "Have a great day!"
     │
     ▼
 User picks repo number
     │
     ▼
 "🔍 Fetching open issues..."
     │
     ▼
 Show issues list
 1. #23 — Fix login bug
 2. #19 — Update README
     │
     ▼
 User picks issue number
     │
     ▼
 Show issue details + GitHub link
 (AI fix coming soon!)
     │
  reply 0
     │
     ▼
 Back to repo list ↩️
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
| `PORT` | Flask server port (default: 5000) |

---

## 🛣️ Roadmap

- [x] Daily WhatsApp reminder at 10 AM
- [x] GitHub repo listing via WhatsApp
- [x] Repo selection and redirect
- [ ] AI-generated commit messages
- [ ] Auto-push commits from WhatsApp
- [ ] GitHub issue AI resolution
- [ ] Branch creation and management
- [ ] Pull request creation with AI descriptions
- [ ] Commit streak tracker
- [ ] Weekly activity summary
- [ ] Multi-user support
- [ ] Web dashboard for configuration

---

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/your-feature`)
3. Make your changes and commit (`git commit -m "Add your feature"`)
4. Push to your branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

Built with ❤️ by [@YOUR_USERNAME](https://github.com/YOUR_USERNAME)

---

> **CommitIQ** — Because great developers ship consistently, not occasionally.
