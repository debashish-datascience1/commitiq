import os
from twilio.rest import Client
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()

client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))


def send_daily_reminder():
    print("Sending daily reminder...")
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
    # Runs every day at 10:00 AM (server local time)
    scheduler.add_job(send_daily_reminder, "cron", hour=10, minute=0)
    scheduler.start()
    print("Scheduler started — daily reminder set for 10:00 AM")
    return scheduler