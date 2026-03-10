import os
from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

from github_helper import get_user_repos, get_repo_url
from sessions import get_session, set_session, clear_session
from scheduler import start_scheduler

load_dotenv()

app = Flask(__name__)

twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))


def send_message(to: str, body: str):
    """Send a WhatsApp message via Twilio."""
    twilio_client.messages.create(
        from_=os.getenv("TWILIO_WHATSAPP_FROM"),
        to=to,
        body=body,
    )


@app.route("/webhook", methods=["POST"])
def webhook():
    from_number = request.form.get("From")        # e.g. whatsapp:+91XXXXXXXXXX
    incoming_msg = request.form.get("Body", "").strip().lower()
    session = get_session(from_number)

    print(f"[{from_number}] Message: '{incoming_msg}' | State: {session['state']}")

    # ── STATE: idle / awaiting yes or no ────────────────────────────────────────
    if session["state"] in ("idle", "asked_initial"):

        if incoming_msg == "yes":
            set_session(from_number, state="fetching_repos")
            try:
                repos = get_user_repos()
                if not repos:
                    send_message(from_number, "⚠️ No repositories found on your GitHub account.")
                    clear_session(from_number)
                    return "", 204

                # Store repos in session so we can map number → repo name
                set_session(from_number, state="awaiting_repo_choice", repos=repos)

                # Build numbered list
                repo_list = "\n".join(
                    f"{i + 1}. {name}" for i, name in enumerate(repos)
                )
                send_message(
                    from_number,
                    f"📁 Here are your GitHub repositories:\n\n{repo_list}\n\n"
                    "Reply with the *number* of the repo you want to work on.",
                )

            except Exception as e:
                print(f"GitHub error: {e}")
                send_message(
                    from_number,
                    "❌ Could not fetch your repositories. Please check your GitHub token.",
                )
                clear_session(from_number)

        elif incoming_msg == "no":
            send_message(
                from_number,
                "✅ Thank you! Have a productive day. See you tomorrow! 🚀",
            )
            clear_session(from_number)

        else:
            # Prompt them if message is unexpected
            send_message(
                from_number,
                "🤔 Please reply with *yes* or *no*.\n\n"
                "Do you want to make any project modifications or commits today?",
            )
            set_session(from_number, state="asked_initial")

    # ── STATE: awaiting repo selection ──────────────────────────────────────────
    elif session["state"] == "awaiting_repo_choice":
        repos = session.get("repos", [])

        if incoming_msg.isdigit():
            choice = int(incoming_msg)

            if 1 <= choice <= len(repos):
                selected_repo = repos[choice - 1]

                try:
                    repo_url = get_repo_url(selected_repo)
                    send_message(
                        from_number,
                        f"🚀 Great choice! Here is the link to *{selected_repo}*:\n\n"
                        f"{repo_url}\n\n"
                        "Happy coding! 💻 More features coming soon...",
                    )
                except Exception as e:
                    print(f"Error fetching repo URL: {e}")
                    send_message(
                        from_number,
                        f"✅ Got it — you selected *{selected_repo}*. More actions coming soon!",
                    )

                clear_session(from_number)

            else:
                send_message(
                    from_number,
                    f"⚠️ Please enter a number between 1 and {len(repos)}.",
                )
        else:
            send_message(
                from_number,
                "⚠️ Please reply with the *number* of the repo from the list above.",
            )

    # ── Fallback ─────────────────────────────────────────────────────────────────
    else:
        clear_session(from_number)
        send_message(
            from_number,
            "👋 Hi! I'll send you a reminder at *10 AM* every day.\n"
            "You can also reply *yes* to get started now.",
        )

    return "", 204

@app.route("/test-reminder")
def test_reminder():
    from scheduler import send_daily_reminder
    send_daily_reminder()
    return "Reminder sent!", 200


if __name__ == "__main__":
    start_scheduler()
    port = int(os.getenv("PORT", 5001))
    app.run(debug=False, port=port)