import os
from flask import Flask, request
from twilio.rest import Client
from dotenv import load_dotenv

from github_helper import get_user_repos, get_repo_url, get_open_issues, get_issue_details, create_issue
from ai_helper import analyze_issue
from sessions import get_session, set_session, clear_session
from scheduler import start_scheduler

load_dotenv()

app = Flask(__name__)

twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))


def send_message(to: str, body: str):
    twilio_client.messages.create(
        from_=os.getenv("TWILIO_WHATSAPP_FROM"),
        to=to,
        body=body,
    )


@app.route("/webhook", methods=["POST"])
def webhook():
    from_number = request.form.get("From")
    incoming_msg = request.form.get("Body", "").strip().lower()
    session = get_session(from_number)

    print(f"[{from_number}] Message: '{incoming_msg}' | State: {session['state']}")

    # ── STATE: idle / awaiting yes or no ────────────────────────────────────
    if session["state"] in ("idle", "asked_initial"):

        if incoming_msg == "1":
            # User chose YES
            set_session(from_number, state="fetching_repos")
            try:
                repos = get_user_repos()
                if not repos:
                    send_message(from_number, "⚠️ No repositories found on your GitHub account.")
                    clear_session(from_number)
                    return "", 204

                set_session(from_number, state="awaiting_repo_choice", repos=repos)

                repo_list = "\n".join(
                    f"{i + 1}. {name}" for i, name in enumerate(repos)
                )
                send_message(
                    from_number,
                    f"📁 *Your GitHub Repositories:*\n\n{repo_list}\n\n"
                    "Reply with the *number* of the repo you want to work on.",
                )

            except Exception as e:
                print(f"GitHub error: {e}")
                send_message(
                    from_number,
                    "❌ Could not fetch repositories. Please check your GitHub token.",
                )
                clear_session(from_number)

        elif incoming_msg == "2":
            # User chose NO
            send_message(
                from_number,
                "✅ No problem! Have a productive day. See you tomorrow! 🚀",
            )
            clear_session(from_number)

        else:
            # First time or wrong input — show options
            set_session(from_number, state="asked_initial")
            send_message(
                from_number,
                "👋 *Good morning, Developer!*\n\n"
                "Do you want to make any project modifications or commits today?\n\n"
                "Reply with:\n"
                "1️⃣ *1* — Yes, let's work!\n"
                "2️⃣ *2* — No, not today",
            )

    # ── STATE: awaiting repo selection ───────────────────────────────────────
    elif session["state"] == "awaiting_repo_choice":
        repos = session.get("repos", [])

        if incoming_msg.isdigit():
            choice = int(incoming_msg)

            if 1 <= choice <= len(repos):
                selected_repo = repos[choice - 1]
                set_session(from_number, state="fetching_issues", selected_repo=selected_repo)

                send_message(from_number, f"🔍 Fetching open issues for *{selected_repo}*...")

                try:
                    issues = get_open_issues(selected_repo)

                    if not issues:
                        repo_url = get_repo_url(selected_repo)
                        send_message(
                            from_number,
                            f"🎉 Great news! *{selected_repo}* has no open issues!\n\n"
                            f"🔗 {repo_url}",
                        )
                        clear_session(from_number)
                        return "", 204

                    # Store issues in session
                    set_session(from_number, state="awaiting_issue_choice", issues=issues)

                    issue_list = "\n".join(
                        f"{i + 1}. #{issue['number']} — {issue['title']}"
                        for i, issue in enumerate(issues)
                    )
                    send_message(
                        from_number,
                        f"🐛 *Open Issues in {selected_repo}:*\n\n"
                        f"{issue_list}\n\n"
                        f"Reply with the *number* to view issue details\n"
                        f"Reply *N* to create a new issue\n"
                        f"Or reply *0* to go back to repo list",
                    )

                except Exception as e:
                    print(f"Issues fetch error: {e}")
                    send_message(from_number, "❌ Could not fetch issues. Please try again.")
                    clear_session(from_number)

            else:
                send_message(
                    from_number,
                    f"⚠️ Please enter a number between 1 and {len(repos)}.",
                )
        else:
            send_message(
                from_number,
                "⚠️ Please reply with the *number* of the repo from the list.",
            )

    # ── STATE: awaiting issue selection ──────────────────────────────────────
    elif session["state"] == "awaiting_issue_choice":
        issues = session.get("issues", [])
        repos = session.get("repos", [])

        if incoming_msg == "0":
            # Go back to repo list
            set_session(from_number, state="awaiting_repo_choice")
            repo_list = "\n".join(
                f"{i + 1}. {name}" for i, name in enumerate(repos)
            )
            send_message(
                from_number,
                f"📁 *Your GitHub Repositories:*\n\n{repo_list}\n\n"
                "Reply with the *number* of the repo you want to work on.",
            )

        elif incoming_msg == "n":
            set_session(from_number, state="awaiting_new_issue_title")
            send_message(
                from_number,
                "📝 *Create a New Issue*\n\n"
                "Please send the *title* of the issue.",
            )

        elif incoming_msg.isdigit():
            choice = int(incoming_msg)

            if 1 <= choice <= len(issues):
                issue = issues[choice - 1]
                selected_repo = session.get("selected_repo")

                # Send basic issue info immediately
                send_message(
                    from_number,
                    f"🐛 *Issue #{issue['number']}*\n\n"
                    f"📌 {issue['title']}\n\n"
                    f"🔗 {issue['url']}\n\n"
                    "⏳ Analyzing with AI...",
                )

                # Fetch full issue body and run AI analysis
                try:
                    details = get_issue_details(selected_repo, issue["number"])
                    suggestion = analyze_issue(details["title"], details["body"])
                    send_message(
                        from_number,
                        f"🤖 *AI Analysis:*\n\n{suggestion}\n\n"
                        "Reply with another issue number or *0* to go back.",
                    )
                except Exception as e:
                    print(f"AI analysis error: {e}")
                    send_message(
                        from_number,
                        "⚠️ AI analysis unavailable right now.\n\n"
                        "Reply with another issue number or *0* to go back.",
                    )
                # Stay in same state so they can pick another issue
            else:
                send_message(
                    from_number,
                    f"⚠️ Please enter a number between 1 and {len(issues)}, or *0* to go back.",
                )
        else:
            send_message(
                from_number,
                "⚠️ Reply with the issue *number*, *N* to create a new issue, or *0* to go back.",
            )

    # ── STATE: awaiting new issue title ──────────────────────────────────────
    elif session["state"] == "awaiting_new_issue_title":
        set_session(from_number, state="awaiting_new_issue_body", new_issue_title=incoming_msg)
        send_message(
            from_number,
            "📝 Got the title! Now send the *description* of the issue.\n\n"
            "Or reply *skip* to create the issue without a description.",
        )

    # ── STATE: awaiting new issue body ───────────────────────────────────────
    elif session["state"] == "awaiting_new_issue_body":
        selected_repo = session.get("selected_repo")
        title = session.get("new_issue_title", "")
        body = "" if incoming_msg == "skip" else incoming_msg

        try:
            new_issue = create_issue(selected_repo, title, body)
            set_session(from_number, state="awaiting_issue_choice", new_issue_title=None)
            send_message(
                from_number,
                f"✅ *Issue Created Successfully!*\n\n"
                f"📌 {title}\n"
                f"🔗 {new_issue['url']}\n\n"
                "Reply with an issue number to view details, *N* to create another, or *0* to go back.",
            )
        except Exception as e:
            print(f"Create issue error: {e}")
            send_message(
                from_number,
                "❌ Failed to create the issue. Please try again.\n"
                "Reply *0* to go back to the repo list.",
            )
            set_session(from_number, state="awaiting_issue_choice")

    # ── Fallback ─────────────────────────────────────────────────────────────
    else:
        clear_session(from_number)
        set_session(from_number, state="asked_initial")
        send_message(
            from_number,
            "👋 *Good morning, Developer!*\n\n"
            "Do you want to make any project modifications or commits today?\n\n"
            "Reply with:\n"
            "1️⃣ *1* — Yes, let's work!\n"
            "2️⃣ *2* — No, not today",
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