import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
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
CORS(app, resources={r"/api/*": {"origins": "*"}})

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


def process_message(user_id: str, text: str, gh_token: str = None, gh_username: str = None) -> list:
    """
    Core state machine. Returns a list of response strings.
    gh_token / gh_username override the .env credentials (used by web/extension users).
    """
    replies = []

    def reply(msg):
        replies.append(msg)

    # Shorthand kwargs passed to every github_helper call
    gh = {"token": gh_token, "username": gh_username}

    cmd = text.strip().lower()   # for command comparisons
    raw = text.strip()           # for user-typed content (titles, bodies, etc.)

    session = get_session(user_id)

    print(f"[{user_id}] Message: '{raw}' | State: {session['state']}")

    # ── STATE: idle / awaiting yes or no ────────────────────────────────────
    if session["state"] in ("idle", "asked_initial"):

        if cmd == "1":
            set_session(user_id, state="fetching_repos")
            try:
                repos = get_user_repos(**gh)
                if not repos:
                    reply("⚠️ No repositories found on your GitHub account.")
                    clear_session(user_id)
                    return replies

                set_session(user_id, state="awaiting_repo_choice", repos=repos)
                repo_list = "\n".join(f"{i + 1}. {name}" for i, name in enumerate(repos))
                reply(
                    f"📁 *Your GitHub Repositories:*\n\n{repo_list}\n\n"
                    "Reply with the *number* of the repo you want to work on.",
                )

            except Exception as e:
                print(f"GitHub error: {e}")
                reply("❌ Could not fetch repositories. Please check your GitHub token.")
                clear_session(user_id)

        elif cmd == "2":
            reply("✅ No problem! Have a productive day. See you tomorrow! 🚀")
            clear_session(user_id)

        else:
            set_session(user_id, state="asked_initial")
            reply(
                "👋 *Good morning, Developer!*\n\n"
                "Do you want to make any project modifications or commits today?\n\n"
                "Reply with:\n"
                "1️⃣ *1* — Yes, let's work!\n"
                "2️⃣ *2* — No, not today",
            )

    # ── STATE: awaiting repo selection ───────────────────────────────────────
    elif session["state"] == "awaiting_repo_choice":
        repos = session.get("repos", [])

        if cmd.isdigit():
            choice = int(cmd)
            if 1 <= choice <= len(repos):
                selected_repo = repos[choice - 1]
                set_session(user_id, state="awaiting_repo_action", selected_repo=selected_repo)
                reply(
                    f"📂 *{selected_repo}*\n\n"
                    "What would you like to do?\n\n"
                    "1️⃣ *1* — View & manage issues\n"
                    "2️⃣ *2* — Make a commit\n"
                    "0️⃣ *0* — Back to repo list",
                )
            else:
                reply(f"⚠️ Please enter a number between 1 and {len(repos)}.")
        else:
            reply("⚠️ Please reply with the *number* of the repo from the list.")

    # ── STATE: awaiting issue selection ──────────────────────────────────────
    elif session["state"] == "awaiting_issue_choice":
        issues = session.get("issues", [])
        repos = session.get("repos", [])

        if cmd == "0":
            set_session(user_id, state="awaiting_repo_choice")
            repo_list = "\n".join(f"{i + 1}. {name}" for i, name in enumerate(repos))
            reply(
                f"📁 *Your GitHub Repositories:*\n\n{repo_list}\n\n"
                "Reply with the *number* of the repo you want to work on.",
            )

        elif cmd == "n":
            set_session(user_id, state="awaiting_new_issue_title")
            reply("📝 *Create a New Issue*\n\nPlease send the *title* of the issue.")

        elif cmd.isdigit():
            choice = int(cmd)
            if 1 <= choice <= len(issues):
                issue = issues[choice - 1]
                selected_repo = session.get("selected_repo")

                reply(
                    f"🐛 *Issue #{issue['number']}*\n\n"
                    f"📌 {issue['title']}\n\n"
                    f"🔗 {issue['url']}\n\n"
                    "⏳ Analyzing with AI...",
                )

                try:
                    details = get_issue_details(selected_repo, issue["number"], **gh)
                    suggestion = analyze_issue(details["title"], details["body"])
                    reply(
                        f"🤖 *AI Analysis:*\n\n{suggestion}\n\n"
                        "Reply with another issue number or *0* to go back.",
                    )
                except Exception as e:
                    print(f"AI analysis error: {e}")
                    reply(
                        "⚠️ AI analysis unavailable right now.\n\n"
                        "Reply with another issue number or *0* to go back.",
                    )
            else:
                reply(f"⚠️ Please enter a number between 1 and {len(issues)}, or *0* to go back.")
        else:
            reply("⚠️ Reply with the issue *number*, *N* to create a new issue, or *0* to go back.")

    # ── STATE: awaiting new issue title ──────────────────────────────────────
    elif session["state"] == "awaiting_new_issue_title":
        set_session(user_id, state="awaiting_new_issue_body", new_issue_title=raw)
        reply(
            "📝 Got the title! Now send the *description* of the issue.\n\n"
            "Or reply *skip* to create the issue without a description.",
        )

    # ── STATE: awaiting new issue body ───────────────────────────────────────
    elif session["state"] == "awaiting_new_issue_body":
        selected_repo = session.get("selected_repo")
        title = session.get("new_issue_title", "")
        body = "" if cmd == "skip" else raw

        try:
            new_issue = create_issue(selected_repo, title, body, **gh)
            reply(
                f"✅ *Issue Created Successfully!*\n\n"
                f"📌 {title}\n"
                f"🔗 {new_issue['url']}",
            )
            issues = get_open_issues(selected_repo, **gh)
            set_session(user_id, state="awaiting_issue_choice", issues=issues, new_issue_title=None)
            issue_list = "\n".join(
                f"{i + 1}. #{issue['number']} — {issue['title']}"
                for i, issue in enumerate(issues)
            )
            reply(
                f"🐛 *Open Issues in {selected_repo}:*\n\n{issue_list}\n\n"
                "Reply with the *number* to view details & AI analysis\n"
                "Reply *N* to create a new issue\n"
                "Or reply *0* to go back to repo list",
            )
        except Exception as e:
            print(f"Create issue error: {e}")
            reply("❌ Failed to create the issue. Please try again.\nReply *0* to go back to the repo list.")
            set_session(user_id, state="awaiting_issue_choice")

    # ── STATE: repo action menu ───────────────────────────────────────────────
    elif session["state"] == "awaiting_repo_action":
        selected_repo = session.get("selected_repo")
        repos = session.get("repos", [])

        if cmd == "0":
            set_session(user_id, state="awaiting_repo_choice")
            repo_list = "\n".join(f"{i + 1}. {name}" for i, name in enumerate(repos))
            reply(f"📁 *Your GitHub Repositories:*\n\n{repo_list}\n\nReply with the *number* of the repo you want to work on.")

        elif cmd == "1":
            try:
                issues = get_open_issues(selected_repo, **gh)
                set_session(user_id, state="awaiting_issue_choice", issues=issues)
                if not issues:
                    reply(f"🎉 *{selected_repo}* has no open issues!\n\nReply *N* to create one or *0* to go back.")
                else:
                    issue_list = "\n".join(f"{i + 1}. #{iss['number']} — {iss['title']}" for i, iss in enumerate(issues))
                    reply(f"🐛 *Open Issues in {selected_repo}:*\n\n{issue_list}\n\nReply with the *number* to view details & AI analysis\nReply *N* to create a new issue\nOr reply *0* to go back to repo list")
            except Exception as e:
                print(f"Issues fetch error: {e}")
                reply("❌ Could not fetch issues. Please try again.")

        elif cmd == "2":
            try:
                items = get_repo_contents(selected_repo, "", **gh)
                set_session(user_id, state="browsing_files", current_path="", dir_contents=items)
                lines = [f"{i + 1}. {'📁' if item['type'] == 'dir' else '📄'} {item['name']}" for i, item in enumerate(items)]
                reply(f"📂 *{selected_repo}/*\n\n" + "\n".join(lines) + "\n\nReply with the *number* to open\nReply *0* to go back")
            except Exception as e:
                print(f"File browse error: {e}")
                reply("❌ Could not fetch repo contents. Please try again.")

        else:
            reply("⚠️ Reply *1* for issues, *2* to make a commit, or *0* to go back.")

    # ── STATE: browsing files ─────────────────────────────────────────────────
    elif session["state"] == "browsing_files":
        selected_repo = session.get("selected_repo")
        current_path = session.get("current_path", "")
        items = session.get("dir_contents", [])

        if cmd == "0":
            if current_path == "":
                set_session(user_id, state="awaiting_repo_action")
                reply(f"📂 *{selected_repo}*\n\nWhat would you like to do?\n\n1️⃣ *1* — View & manage issues\n2️⃣ *2* — Make a commit\n0️⃣ *0* — Back to repo list")
            else:
                parent = "/".join(current_path.split("/")[:-1])
                try:
                    parent_items = get_repo_contents(selected_repo, parent, **gh)
                    set_session(user_id, state="browsing_files", current_path=parent, dir_contents=parent_items)
                    lines = [f"{i + 1}. {'📁' if item['type'] == 'dir' else '📄'} {item['name']}" for i, item in enumerate(parent_items)]
                    path_display = f"{selected_repo}/{parent}" if parent else f"{selected_repo}/"
                    reply(f"📂 *{path_display}*\n\n" + "\n".join(lines) + "\n\nReply with the *number* to open\nReply *0* to go back")
                except Exception as e:
                    print(f"File browse error: {e}")
                    reply("❌ Could not go back. Please try again.")

        elif cmd.isdigit():
            choice = int(cmd)
            if 1 <= choice <= len(items):
                selected_item = items[choice - 1]
                if selected_item["type"] == "dir":
                    try:
                        sub_items = get_repo_contents(selected_repo, selected_item["path"], **gh)
                        set_session(user_id, state="browsing_files", current_path=selected_item["path"], dir_contents=sub_items)
                        lines = [f"{i + 1}. {'📁' if item['type'] == 'dir' else '📄'} {item['name']}" for i, item in enumerate(sub_items)]
                        reply(f"📂 *{selected_repo}/{selected_item['path']}/*\n\n" + "\n".join(lines) + "\n\nReply with the *number* to open\nReply *0* to go back")
                    except Exception as e:
                        print(f"Folder open error: {e}")
                        reply("❌ Could not open folder. Please try again.")
                else:
                    set_session(user_id, state="awaiting_file_action", selected_file=selected_item["path"])
                    reply(
                        f"📄 *{selected_item['name']}*\n\n"
                        "What do you want to add?\n\n"
                        "1️⃣ *1* — Add a blank line (whitespace)\n"
                        "2️⃣ *2* — Add a comment\n"
                        "0️⃣ *0* — Go back",
                    )
            else:
                reply(f"⚠️ Please enter a number between 1 and {len(items)}, or *0* to go back.")
        else:
            reply("⚠️ Reply with a *number* to select, or *0* to go back.")

    # ── STATE: awaiting file action ───────────────────────────────────────────
    elif session["state"] == "awaiting_file_action":
        selected_repo = session.get("selected_repo")
        selected_file = session.get("selected_file")

        if cmd == "0":
            current_path = "/".join(selected_file.split("/")[:-1])
            try:
                items = get_repo_contents(selected_repo, current_path, **gh)
                set_session(user_id, state="browsing_files", current_path=current_path, dir_contents=items)
                lines = [f"{i + 1}. {'📁' if item['type'] == 'dir' else '📄'} {item['name']}" for i, item in enumerate(items)]
                path_display = f"{selected_repo}/{current_path}" if current_path else f"{selected_repo}/"
                reply(f"📂 *{path_display}*\n\n" + "\n".join(lines) + "\n\nReply with the *number* to open\nReply *0* to go back")
            except Exception as e:
                print(f"Back error: {e}")
                reply("❌ Could not go back. Please try again.")

        elif cmd == "1":
            set_session(user_id, state="awaiting_commit_message", file_action="space", comment_text="")
            reply("✏️ A blank line will be added at the end of the file.\n\nNow send your *commit message*:")

        elif cmd == "2":
            set_session(user_id, state="awaiting_comment_text", file_action="comment")
            reply("💬 What should the comment say?\n\nSend the comment text (without the comment prefix):")

        else:
            reply("⚠️ Reply *1* to add a blank line, *2* to add a comment, or *0* to go back.")

    # ── STATE: awaiting comment text ──────────────────────────────────────────
    elif session["state"] == "awaiting_comment_text":
        set_session(user_id, state="awaiting_commit_message", comment_text=raw)
        reply("✅ Comment saved.\n\nNow send your *commit message*:")

    # ── STATE: awaiting commit message ────────────────────────────────────────
    elif session["state"] == "awaiting_commit_message":
        selected_repo = session.get("selected_repo")
        selected_file = session.get("selected_file")
        file_action = session.get("file_action")
        comment_text = session.get("comment_text", "")

        try:
            file_data = get_file_content(selected_repo, selected_file, **gh)
            original = file_data["content"]
            sha = file_data["sha"]
            filename = selected_file.split("/")[-1]

            if file_action == "space":
                new_content = original.rstrip("\n") + "\n\n"
            else:
                comment_line = _comment_line(filename, comment_text)
                new_content = original.rstrip("\n") + f"\n{comment_line}\n"

            commit_url = commit_file_change(selected_repo, selected_file, new_content, sha, raw, **gh)
            set_session(user_id, state="awaiting_repo_action")
            reply(
                f"🚀 *Commit Successful!*\n\n"
                f"📄 File: `{selected_file}`\n"
                f"💬 Message: _{raw}_\n"
                f"🔗 {commit_url}\n\n"
                "Reply *1* to view issues, *2* to make another commit, or *0* to go back to repo list.",
            )
        except Exception as e:
            print(f"Commit error: {e}")
            reply("❌ Commit failed. Please try again.\n\nReply *1* for issues or *2* to try committing again.")
            set_session(user_id, state="awaiting_repo_action")

    # ── Fallback ─────────────────────────────────────────────────────────────
    else:
        clear_session(user_id)
        set_session(user_id, state="asked_initial")
        reply(
            "👋 *Good morning, Developer!*\n\n"
            "Do you want to make any project modifications or commits today?\n\n"
            "Reply with:\n"
            "1️⃣ *1* — Yes, let's work!\n"
            "2️⃣ *2* — No, not today",
        )

    return replies


# ── Twilio WhatsApp webhook ───────────────────────────────────────────────────

@app.route("/webhook", methods=["POST"])
def webhook():
    from_number = request.form.get("From")
    incoming_msg = request.form.get("Body", "")
    responses = process_message(from_number, incoming_msg)
    for msg in responses:
        send_message(from_number, msg)
    return "", 204


# ── Web UI routes ─────────────────────────────────────────────────────────────

@app.route("/chat")
def chat():
    return render_template("chat.html")


@app.route("/api/message", methods=["POST"])
def api_message():
    data = request.get_json()
    session_id  = data.get("session_id", "web-user")
    text        = data.get("message", "")
    gh_token    = data.get("gh_token") or None
    gh_username = data.get("gh_username") or None
    if not text:
        return jsonify({"responses": []}), 400
    responses = process_message(session_id, text, gh_token=gh_token, gh_username=gh_username)
    return jsonify({"responses": responses})


# ── Test reminder ─────────────────────────────────────────────────────────────

@app.route("/test-reminder")
def test_reminder():
    from scheduler import send_daily_reminder
    send_daily_reminder()
    return "Reminder sent!", 200


if __name__ == "__main__":
    start_scheduler()
    port = int(os.getenv("PORT", 5001))
    app.run(debug=False, port=port)
