import os
from twilio.rest import Client
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()

client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))


def send_daily_reminder():
    """Send the daily 10 AM WhatsApp reminder."""
    print("Sending daily reminder...")
    client.messages.create(
        from_=os.getenv("TWILIO_WHATSAPP_FROM"),
        to=os.getenv("USER_WHATSAPP_TO"),
        body=(
            "👋 Good morning! Today, do you want to make any "
            "project modifications or commits?\n\nReply *yes* or *no*"
        ),
    )


def start_scheduler():
    scheduler = BackgroundScheduler()
    # Runs every day at 10:00 AM (server local time)
    scheduler.add_job(send_daily_reminder, "cron", hour=10, minute=0)
    scheduler.start()
    print("Scheduler started — daily reminder set for 10:00 AM")
    return scheduler