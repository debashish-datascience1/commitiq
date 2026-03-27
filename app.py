import os
from flask import Flask, request
from twilio.rest import Client
from dotenv import load_dotenv

from github_helper import (
    get_user_repos, get_open_issues, get_issue_details,
    create_issue, get_repo_contents, get_file_content, commit_file_change,
)
from ai_helper import analyze_issue
from sessions import get_session, set_session, clear_session
from scheduler import start_scheduler

load_dotenv()

app = Flask(__name__)

twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))


COMMENT_PREFIX = {
    ".py": "#", ".sh": "#", ".rb": "#", ".yml": "#", ".yaml": "#",
    ".js": "//", ".ts": "//", ".jsx": "//", ".tsx": "//",
    ".java": "//", ".c": "//", ".cpp": "//", ".go": "//", ".rs": "//",
    ".html": "<!--", ".css": "/*",
}

def _comment_line(filename: str, text: str) -> str:
    ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
    prefix = COMMENT_PREFIX.get(ext, "#")
    if prefix == "<!--":
        return f"<!-- {text} -->"
    if prefix == "/*":
        return f"/* {text} */"
    return f"{prefix} {text}"


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
                set_session(from_number, state="awaiting_repo_action", selected_repo=selected_repo)
                send_message(
                    from_number,
                    f"📂 *{selected_repo}*\n\n"
                    "What would you like to do?\n\n"
                    "1️⃣ *1* — View & manage issues\n"
                    "2️⃣ *2* — Make a commit\n"
                    "0️⃣ *0* — Back to repo list",
                )

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
            send_message(
                from_number,
                f"✅ *Issue Created Successfully!*\n\n"
                f"📌 {title}\n"
                f"🔗 {new_issue['url']}",
            )

            # Re-fetch updated issue list and show it
            issues = get_open_issues(selected_repo)
            set_session(from_number, state="awaiting_issue_choice", issues=issues, new_issue_title=None)
            issue_list = "\n".join(
                f"{i + 1}. #{issue['number']} — {issue['title']}"
                for i, issue in enumerate(issues)
            )
            send_message(
                from_number,
                f"🐛 *Open Issues in {selected_repo}:*\n\n"
                f"{issue_list}\n\n"
                f"Reply with the *number* to view details & AI analysis\n"
                f"Reply *N* to create a new issue\n"
                f"Or reply *0* to go back to repo list",
            )
        except Exception as e:
            print(f"Create issue error: {e}")
            send_message(
                from_number,
                "❌ Failed to create the issue. Please try again.\n"
                "Reply *0* to go back to the repo list.",
            )
            set_session(from_number, state="awaiting_issue_choice")

    # ── STATE: repo action menu ───────────────────────────────────────────────
    elif session["state"] == "awaiting_repo_action":
        selected_repo = session.get("selected_repo")
        repos = session.get("repos", [])

        if incoming_msg == "0":
            set_session(from_number, state="awaiting_repo_choice")
            repo_list = "\n".join(f"{i + 1}. {name}" for i, name in enumerate(repos))
            send_message(from_number, f"📁 *Your GitHub Repositories:*\n\n{repo_list}\n\nReply with the *number* of the repo you want to work on.")

        elif incoming_msg == "1":
            # View issues
            try:
                issues = get_open_issues(selected_repo)
                set_session(from_number, state="awaiting_issue_choice", issues=issues)
                if not issues:
                    send_message(from_number, f"🎉 *{selected_repo}* has no open issues!\n\nReply *N* to create one or *0* to go back.")
                else:
                    issue_list = "\n".join(f"{i + 1}. #{iss['number']} — {iss['title']}" for i, iss in enumerate(issues))
                    send_message(from_number, f"🐛 *Open Issues in {selected_repo}:*\n\n{issue_list}\n\nReply with the *number* to view details & AI analysis\nReply *N* to create a new issue\nOr reply *0* to go back to repo list")
            except Exception as e:
                print(f"Issues fetch error: {e}")
                send_message(from_number, "❌ Could not fetch issues. Please try again.")

        elif incoming_msg == "2":
            # Browse files for commit
            try:
                items = get_repo_contents(selected_repo, "")
                set_session(from_number, state="browsing_files", current_path="", dir_contents=items)
                lines = []
                for i, item in enumerate(items):
                    icon = "📁" if item["type"] == "dir" else "📄"
                    lines.append(f"{i + 1}. {icon} {item['name']}")
                send_message(from_number, f"📂 *{selected_repo}/*\n\n" + "\n".join(lines) + "\n\nReply with the *number* to open\nReply *0* to go back")
            except Exception as e:
                print(f"File browse error: {e}")
                send_message(from_number, "❌ Could not fetch repo contents. Please try again.")

        else:
            send_message(from_number, "⚠️ Reply *1* for issues, *2* to make a commit, or *0* to go back.")

    # ── STATE: browsing files ─────────────────────────────────────────────────
    elif session["state"] == "browsing_files":
        selected_repo = session.get("selected_repo")
        current_path = session.get("current_path", "")
        items = session.get("dir_contents", [])
        repos = session.get("repos", [])

        if incoming_msg == "0":
            if current_path == "":
                # Back to repo action menu
                set_session(from_number, state="awaiting_repo_action")
                send_message(from_number, f"📂 *{selected_repo}*\n\nWhat would you like to do?\n\n1️⃣ *1* — View & manage issues\n2️⃣ *2* — Make a commit\n0️⃣ *0* — Back to repo list")
            else:
                # Go up one level
                parent = "/".join(current_path.split("/")[:-1])
                try:
                    parent_items = get_repo_contents(selected_repo, parent)
                    set_session(from_number, state="browsing_files", current_path=parent, dir_contents=parent_items)
                    lines = []
                    for i, item in enumerate(parent_items):
                        icon = "📁" if item["type"] == "dir" else "📄"
                        lines.append(f"{i + 1}. {icon} {item['name']}")
                    path_display = f"{selected_repo}/{parent}" if parent else f"{selected_repo}/"
                    send_message(from_number, f"📂 *{path_display}*\n\n" + "\n".join(lines) + "\n\nReply with the *number* to open\nReply *0* to go back")
                except Exception as e:
                    print(f"File browse error: {e}")
                    send_message(from_number, "❌ Could not go back. Please try again.")

        elif incoming_msg.isdigit():
            choice = int(incoming_msg)
            if 1 <= choice <= len(items):
                selected_item = items[choice - 1]
                if selected_item["type"] == "dir":
                    # Navigate into folder
                    try:
                        sub_items = get_repo_contents(selected_repo, selected_item["path"])
                        set_session(from_number, state="browsing_files", current_path=selected_item["path"], dir_contents=sub_items)
                        lines = []
                        for i, item in enumerate(sub_items):
                            icon = "📁" if item["type"] == "dir" else "📄"
                            lines.append(f"{i + 1}. {icon} {item['name']}")
                        send_message(from_number, f"📂 *{selected_repo}/{selected_item['path']}/*\n\n" + "\n".join(lines) + "\n\nReply with the *number* to open\nReply *0* to go back")
                    except Exception as e:
                        print(f"Folder open error: {e}")
                        send_message(from_number, "❌ Could not open folder. Please try again.")
                else:
                    # File selected — show action options
                    set_session(from_number, state="awaiting_file_action", selected_file=selected_item["path"])
                    send_message(
                        from_number,
                        f"📄 *{selected_item['name']}*\n\n"
                        "What do you want to add?\n\n"
                        "1️⃣ *1* — Add a blank line (whitespace)\n"
                        "2️⃣ *2* — Add a comment\n"
                        "0️⃣ *0* — Go back",
                    )
            else:
                send_message(from_number, f"⚠️ Please enter a number between 1 and {len(items)}, or *0* to go back.")
        else:
            send_message(from_number, "⚠️ Reply with a *number* to select, or *0* to go back.")

    # ── STATE: awaiting file action ───────────────────────────────────────────
    elif session["state"] == "awaiting_file_action":
        selected_repo = session.get("selected_repo")
        selected_file = session.get("selected_file")

        if incoming_msg == "0":
            # Back to browsing — reload current folder
            current_path = "/".join(selected_file.split("/")[:-1])
            try:
                items = get_repo_contents(selected_repo, current_path)
                set_session(from_number, state="browsing_files", current_path=current_path, dir_contents=items)
                lines = []
                for i, item in enumerate(items):
                    icon = "📁" if item["type"] == "dir" else "📄"
                    lines.append(f"{i + 1}. {icon} {item['name']}")
                path_display = f"{selected_repo}/{current_path}" if current_path else f"{selected_repo}/"
                send_message(from_number, f"📂 *{path_display}*\n\n" + "\n".join(lines) + "\n\nReply with the *number* to open\nReply *0* to go back")
            except Exception as e:
                print(f"Back error: {e}")
                send_message(from_number, "❌ Could not go back. Please try again.")

        elif incoming_msg == "1":
            # Add blank line — go straight to commit message
            set_session(from_number, state="awaiting_commit_message", file_action="space", comment_text="")
            send_message(from_number, "✏️ A blank line will be added at the end of the file.\n\nNow send your *commit message*:")

        elif incoming_msg == "2":
            # Add comment — ask for comment text
            set_session(from_number, state="awaiting_comment_text", file_action="comment")
            send_message(from_number, "💬 What should the comment say?\n\nSend the comment text (without the comment prefix):")

        else:
            send_message(from_number, "⚠️ Reply *1* to add a blank line, *2* to add a comment, or *0* to go back.")

    # ── STATE: awaiting comment text ──────────────────────────────────────────
    elif session["state"] == "awaiting_comment_text":
        set_session(from_number, state="awaiting_commit_message", comment_text=incoming_msg)
        send_message(from_number, f"✅ Comment saved.\n\nNow send your *commit message*:")

    # ── STATE: awaiting commit message ────────────────────────────────────────
    elif session["state"] == "awaiting_commit_message":
        selected_repo = session.get("selected_repo")
        selected_file = session.get("selected_file")
        file_action = session.get("file_action")
        comment_text = session.get("comment_text", "")
        commit_message = incoming_msg

        try:
            file_data = get_file_content(selected_repo, selected_file)
            original = file_data["content"]
            sha = file_data["sha"]
            filename = selected_file.split("/")[-1]

            if file_action == "space":
                new_content = original.rstrip("\n") + "\n\n"
            else:
                comment_line = _comment_line(filename, comment_text)
                new_content = original.rstrip("\n") + f"\n{comment_line}\n"

            commit_url = commit_file_change(selected_repo, selected_file, new_content, sha, commit_message)
            set_session(from_number, state="awaiting_repo_action")
            send_message(
                from_number,
                f"🚀 *Commit Successful!*\n\n"
                f"📄 File: `{selected_file}`\n"
                f"💬 Message: _{commit_message}_\n"
                f"🔗 {commit_url}\n\n"
                "Reply *1* to view issues, *2* to make another commit, or *0* to go back to repo list.",
            )
        except Exception as e:
            print(f"Commit error: {e}")
            send_message(from_number, "❌ Commit failed. Please try again.\n\nReply *1* for issues or *2* to try committing again.")
            set_session(from_number, state="awaiting_repo_action")

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