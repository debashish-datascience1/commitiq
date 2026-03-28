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


def send_daily_reminder():
    print("Sending daily reminder...")
    client = _get_client()
    if not client:
        print("⚠️  Twilio not configured — skipping WhatsApp reminder.")
        return
    try:
        message = client.messages.create(
            from_=os.getenv("TWILIO_WHATSAPP_FROM"),
            to=os.getenv("USER_WHATSAPP_TO"),
            body=(
                "👋 *Good morning, Developer!*\n\n"
                "Do you want to make any project modifications or commits today?\n\n"
                "Reply with:\n"
                "1️⃣ *1* — Yes, let's work!\n"
                "2️⃣ *2* — No, not today"
            ),
        )
        print(f"✅ Reminder sent! SID: {message.sid}")
    except Exception as e:
        print(f"❌ ERROR sending message: {e}")


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_daily_reminder, "cron", hour=10, minute=0)
    scheduler.start()
    print("Scheduler started — daily reminder set for 10:00 AM")
    return scheduler
