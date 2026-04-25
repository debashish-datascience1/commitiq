import os
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()

_twilio_client = None

def _get_client():
    global _twilio_client
    if _twilio_client is None:
        sid = os.getenv("TWILIO_ACCOUNT_SID")
        token = os.getenv("TWILIO_AUTH_TOKEN")
        if sid and token:
            from twilio.rest import Client
            _twilio_client = Client(sid, token)
    return _twilio_client


def _send_whatsapp(body: str):
    """Send a WhatsApp message to the bot owner. No-op if Twilio not configured."""
    client = _get_client()
    if not client:
        print("⚠️  Twilio not configured — skipping WhatsApp message.")
        return
    message = client.messages.create(
        from_=os.getenv("TWILIO_WHATSAPP_FROM"),
        to=os.getenv("USER_WHATSAPP_TO"),
        body=body,
    )
    print(f"✅ Message sent! SID: {message.sid}")


def send_daily_reminder():
    print("Sending daily reminder...")
    try:
        _send_whatsapp(
            "👋 *Good morning, Developer!*\n\n"
            "Do you want to make any project modifications or commits today?\n\n"
            "Reply with:\n"
            "1️⃣ *1* — Yes, let's work!\n"
            "2️⃣ *2* — No, not today"
        )
    except Exception as e:
        print(f"❌ ERROR sending daily reminder: {e}")


def send_weekly_summary():
    print("Sending weekly summary...")
    try:
        from github_helper import get_weekly_activity
        from ai_helper import generate_weekly_summary

        activity = get_weekly_activity()
        summary = generate_weekly_summary(activity)

        repos_text = ", ".join(activity["repos"]) if activity["repos"] else "none"
        stats = (
            f"📊 *This week's stats:*\n"
            f"• Commits: {activity['commits']}\n"
            f"• Issues opened: {activity['issues_opened']}\n"
            f"• PRs opened: {activity['prs_opened']}\n"
            f"• Active repos: {repos_text}"
        )
        _send_whatsapp(f"📅 *Weekly GitHub Summary*\n\n{summary}\n\n{stats}")
    except Exception as e:
        print(f"❌ ERROR sending weekly summary: {e}")


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_daily_reminder, "cron", hour=10, minute=0)
    scheduler.add_job(send_weekly_summary, "cron", day_of_week="sun", hour=9, minute=0)
    scheduler.start()
    print("Scheduler started — daily reminder at 10:00 AM, weekly summary on Sundays at 9:00 AM")
    return scheduler
