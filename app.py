import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from twilio.rest import Client
from dotenv import load_dotenv

from github_helper import (
    get_user_repos, get_open_issues, get_issue_details,
    create_issue, get_repo_contents, get_file_content, commit_file_change,
    get_branches, create_branch, get_branch_commits, create_pull_request,
)
from ai_helper import analyze_issue, generate_pr_description, ai_fix_code, identify_fix_file
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
                    "2️⃣ *2* — Browse files & commit\n"
                    "3️⃣ *3* — Manage branches\n"
                    "4️⃣ *4* — Create a pull request\n"
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

        elif cmd == "a":
            selected_issue = session.get("selected_issue")
            if not selected_issue:
                reply("⚠️ Please select an issue number first, then reply *A* to apply a fix.")
            else:
                selected_repo = session.get("selected_repo")
                reply("⏳ AI is scanning your repo and generating a fix — this may take a moment...")

                try:
                    # Collect files: root + one level of subdirectories
                    root_items = get_repo_contents(selected_repo, "", **gh)
                    file_paths = []
                    for item in root_items:
                        if item["type"] == "file":
                            file_paths.append(item["path"])
                        elif item["type"] == "dir":
                            try:
                                sub = get_repo_contents(selected_repo, item["path"], **gh)
                                file_paths.extend(i["path"] for i in sub if i["type"] == "file")
                            except Exception:
                                pass

                    if not file_paths:
                        reply("⚠️ No files found in this repository.")
                    else:
                        target_file = identify_fix_file(
                            selected_issue["title"], selected_issue["body"], file_paths
                        )
                        file_data = get_file_content(selected_repo, target_file, **gh)
                        original = file_data["content"]
                        sha = file_data["sha"]
                        filename = target_file.split("/")[-1]

                        if len(original) > 8000:
                            reply(
                                f"⚠️ Target file `{target_file}` is too large for AI fix.\n\n"
                                "Reply with another issue number or *0* to go back."
                            )
                        else:
                            fix_desc = (
                                f"Fix this issue: {selected_issue['title']}\n\n"
                                f"Issue details: {selected_issue['body']}"
                            )
                            new_content = ai_fix_code(filename, original, fix_desc)
                            set_session(
                                user_id,
                                state="awaiting_issue_fix_commit",
                                ai_fixed_content=new_content,
                                file_sha=sha,
                                selected_file=target_file,
                            )
                            reply(
                                f"✅ *AI Fix Ready!*\n\n"
                                f"📌 Issue: _{selected_issue['title']}_\n"
                                f"📄 File: `{target_file}`\n\n"
                                "Send your *commit message* to apply the fix, or reply *0* to cancel.",
                            )

                except Exception as e:
                    print(f"Issue fix error: {e}")
                    reply(
                        "❌ Could not generate a fix automatically.\n\n"
                        "Reply with another issue number or *0* to go back.",
                    )

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
                    set_session(user_id, selected_issue=details)
                    reply(
                        f"🤖 *AI Analysis:*\n\n{suggestion}\n\n"
                        "Reply *A* to auto-apply this fix\n"
                        "Reply with another issue number to view\n"
                        "Or reply *0* to go back.",
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
            reply("⚠️ Reply with the issue *number*, *A* to apply a fix, *N* to create, or *0* to go back.")

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

        elif cmd == "3":
            try:
                branches = get_branches(selected_repo, **gh)
                set_session(user_id, state="awaiting_branch_action", branches=branches)
                branch_list = "\n".join(f"{i + 1}. 🌿 {b}" for i, b in enumerate(branches))
                reply(
                    f"🌿 *Branches in {selected_repo}:*\n\n{branch_list}\n\n"
                    "Reply *2* to create a new branch or *0* to go back."
                )
            except Exception as e:
                print(f"Branch fetch error: {e}")
                reply("❌ Could not fetch branches. Please try again.")

        elif cmd == "4":
            try:
                branches = get_branches(selected_repo, **gh)
                if len(branches) < 2:
                    reply("⚠️ You need at least *2 branches* to create a pull request.\n\nReply *3* to create a branch first.")
                else:
                    set_session(user_id, state="awaiting_pr_head_branch", branches=branches)
                    branch_list = "\n".join(f"{i + 1}. 🌿 {b}" for i, b in enumerate(branches))
                    reply(f"📤 *Select the head branch* (the branch with your changes):\n\n{branch_list}\n\nReply *0* to go back.")
            except Exception as e:
                print(f"Branch fetch error: {e}")
                reply("❌ Could not fetch branches. Please try again.")

        else:
            reply("⚠️ Reply *1* for issues, *2* to browse files, *3* for branches, *4* to create a PR, or *0* to go back.")

    # ── STATE: browsing files ─────────────────────────────────────────────────
    elif session["state"] == "browsing_files":
        selected_repo = session.get("selected_repo")
        current_path = session.get("current_path", "")
        items = session.get("dir_contents", [])

        if cmd == "0":
            if current_path == "":
                set_session(user_id, state="awaiting_repo_action")
                reply(f"📂 *{selected_repo}*\n\nWhat would you like to do?\n\n1️⃣ *1* — View & manage issues\n2️⃣ *2* — Browse files & commit\n3️⃣ *3* — Manage branches\n4️⃣ *4* — Create a pull request\n0️⃣ *0* — Back to repo list")
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
                        "What do you want to do?\n\n"
                        "1️⃣ *1* — Add a blank line\n"
                        "2️⃣ *2* — Add a comment\n"
                        "3️⃣ *3* — AI Auto-Fix (describe your change)\n"
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

        elif cmd == "3":
            set_session(user_id, state="awaiting_ai_fix_description")
            reply(
                "🤖 *AI Auto-Fix*\n\n"
                "Describe the change you want to make to this file:\n\n"
                "_Examples:_\n"
                "• `add error handling to the login function`\n"
                "• `rename variable x to user_count`\n"
                "• `add a docstring to each function`",
            )

        else:
            reply("⚠️ Reply *1* to add a blank line, *2* to add a comment, *3* for AI Auto-Fix, or *0* to go back.")

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

    # ── STATE: awaiting issue fix commit message ──────────────────────────────
    elif session["state"] == "awaiting_issue_fix_commit":
        selected_repo = session.get("selected_repo")
        selected_file = session.get("selected_file")
        new_content = session.get("ai_fixed_content", "")
        sha = session.get("file_sha", "")

        if cmd == "0":
            issues = session.get("issues", [])
            set_session(user_id, state="awaiting_issue_choice")
            issue_list = "\n".join(f"{i + 1}. #{iss['number']} — {iss['title']}" for i, iss in enumerate(issues))
            reply(
                f"❌ Fix cancelled.\n\n🐛 *Open Issues:*\n\n{issue_list}\n\n"
                "Reply with the *number* to view, *N* to create, or *0* to go back.",
            )
        else:
            try:
                commit_url = commit_file_change(selected_repo, selected_file, new_content, sha, raw, **gh)
                set_session(user_id, state="awaiting_repo_action")
                reply(
                    f"🚀 *Issue Fix Committed!*\n\n"
                    f"📄 File: `{selected_file}`\n"
                    f"💬 Message: _{raw}_\n"
                    f"🔗 {commit_url}\n\n"
                    "Reply *1* to view issues, *2* to browse files, or *0* to go back.",
                )
            except Exception as e:
                print(f"Issue fix commit error: {e}")
                reply("❌ Commit failed. Please try again.\n\nReply *0* to go back.")
                set_session(user_id, state="awaiting_repo_action")

    # ── STATE: awaiting AI fix description ───────────────────────────────────
    elif session["state"] == "awaiting_ai_fix_description":
        selected_repo = session.get("selected_repo")
        selected_file = session.get("selected_file")
        filename = selected_file.split("/")[-1]

        reply("⏳ AI is analyzing and applying your fix...")

        try:
            file_data = get_file_content(selected_repo, selected_file, **gh)
            original = file_data["content"]
            sha = file_data["sha"]

            # Limit to ~8000 chars to stay within token budget
            if len(original) > 8000:
                reply("⚠️ File is too large for AI Auto-Fix (limit: ~8000 characters).\n\nReply *0* to go back.")
                set_session(user_id, state="awaiting_file_action")
            else:
                new_content = ai_fix_code(filename, original, raw)
                set_session(user_id, state="awaiting_ai_fix_commit", ai_fixed_content=new_content, file_sha=sha)
                line_count = len(new_content.splitlines())
                reply(
                    f"✅ *AI Fix Ready!*\n\n"
                    f"📄 `{selected_file}` — {line_count} lines\n\n"
                    "Send your *commit message* to apply the fix, or reply *0* to cancel.",
                )
        except Exception as e:
            print(f"AI fix error: {e}")
            reply("❌ AI could not generate a fix. Try a clearer description and try again.\n\nReply *0* to go back.")
            set_session(user_id, state="awaiting_file_action")

    # ── STATE: awaiting AI fix commit message ─────────────────────────────────
    elif session["state"] == "awaiting_ai_fix_commit":
        selected_repo = session.get("selected_repo")
        selected_file = session.get("selected_file")
        new_content = session.get("ai_fixed_content", "")
        sha = session.get("file_sha", "")

        if cmd == "0":
            set_session(user_id, state="awaiting_file_action")
            reply(
                "❌ AI fix cancelled.\n\n"
                "1️⃣ *1* — Add a blank line\n"
                "2️⃣ *2* — Add a comment\n"
                "3️⃣ *3* — AI Auto-Fix\n"
                "0️⃣ *0* — Go back",
            )
        else:
            try:
                commit_url = commit_file_change(selected_repo, selected_file, new_content, sha, raw, **gh)
                set_session(user_id, state="awaiting_repo_action")
                reply(
                    f"🚀 *AI Fix Committed!*\n\n"
                    f"📄 File: `{selected_file}`\n"
                    f"💬 Message: _{raw}_\n"
                    f"🔗 {commit_url}\n\n"
                    "Reply *1* to view issues, *2* to commit another file, or *0* to go back.",
                )
            except Exception as e:
                print(f"AI fix commit error: {e}")
                reply("❌ Commit failed. Please try again.\n\nReply *0* to go back.")
                set_session(user_id, state="awaiting_repo_action")

    # ── STATE: branch action menu ─────────────────────────────────────────────
    elif session["state"] == "awaiting_branch_action":
        selected_repo = session.get("selected_repo")
        branches = session.get("branches", [])

        if cmd == "0":
            set_session(user_id, state="awaiting_repo_action")
            reply(
                f"📂 *{selected_repo}*\n\n"
                "What would you like to do?\n\n"
                "1️⃣ *1* — View & manage issues\n"
                "2️⃣ *2* — Browse files & commit\n"
                "3️⃣ *3* — Manage branches\n"
                "4️⃣ *4* — Create a pull request\n"
                "0️⃣ *0* — Back to repo list",
            )

        elif cmd == "1":
            try:
                branches = get_branches(selected_repo, **gh)
                set_session(user_id, branches=branches)
                branch_list = "\n".join(f"{i + 1}. 🌿 {b}" for i, b in enumerate(branches))
                reply(f"🌿 *Branches in {selected_repo}:*\n\n{branch_list}\n\nReply *2* to create a new branch or *0* to go back.")
            except Exception as e:
                print(f"Branch fetch error: {e}")
                reply("❌ Could not fetch branches. Please try again.")

        elif cmd == "2":
            set_session(user_id, state="awaiting_new_branch_name")
            reply("🌿 *Create a New Branch*\n\nWhat should the branch be named?\n_(e.g. `feature/dark-mode`, `fix/login-bug`)_")

        else:
            reply("⚠️ Reply *1* to list branches, *2* to create a new branch, or *0* to go back.")

    # ── STATE: awaiting new branch name ──────────────────────────────────────
    elif session["state"] == "awaiting_new_branch_name":
        selected_repo = session.get("selected_repo")
        branch_name = raw.strip().replace(" ", "-")

        try:
            default_branch = get_repo_default_branch(selected_repo, **gh)
            create_branch(selected_repo, branch_name, default_branch, **gh)
            branches = get_branches(selected_repo, **gh)
            set_session(user_id, state="awaiting_branch_action", branches=branches)
            reply(
                f"✅ *Branch Created!*\n\n"
                f"🌿 `{branch_name}` (from `{default_branch}`)\n\n"
                "Reply *1* to list all branches, *2* to create another, or *0* to go back.",
            )
        except Exception as e:
            print(f"Branch create error: {e}")
            reply("❌ Could not create the branch. Check the name and try again.\n\nReply *2* to retry or *0* to go back.")
            set_session(user_id, state="awaiting_branch_action")

    # ── STATE: select head branch for PR ─────────────────────────────────────
    elif session["state"] == "awaiting_pr_head_branch":
        branches = session.get("branches", [])
        selected_repo = session.get("selected_repo")

        if cmd == "0":
            set_session(user_id, state="awaiting_repo_action")
            reply(
                f"📂 *{selected_repo}*\n\n"
                "What would you like to do?\n\n"
                "1️⃣ *1* — View & manage issues\n"
                "2️⃣ *2* — Browse files & commit\n"
                "3️⃣ *3* — Manage branches\n"
                "4️⃣ *4* — Create a pull request\n"
                "0️⃣ *0* — Back to repo list",
            )

        elif cmd.isdigit():
            choice = int(cmd)
            if 1 <= choice <= len(branches):
                head_branch = branches[choice - 1]
                base_candidates = [b for b in branches if b != head_branch]
                set_session(user_id, state="awaiting_pr_base_branch", pr_head=head_branch, pr_base_candidates=base_candidates)
                branch_list = "\n".join(f"{i + 1}. 🌿 {b}" for i, b in enumerate(base_candidates))
                reply(
                    f"✅ Head branch: `{head_branch}`\n\n"
                    f"📥 *Select the base branch* (where to merge into):\n\n{branch_list}\n\n"
                    "Reply *0* to go back."
                )
            else:
                reply(f"⚠️ Please enter a number between 1 and {len(branches)}.")

        else:
            reply("⚠️ Reply with the *number* of the branch or *0* to go back.")

    # ── STATE: select base branch for PR ─────────────────────────────────────
    elif session["state"] == "awaiting_pr_base_branch":
        base_candidates = session.get("pr_base_candidates", [])
        pr_head = session.get("pr_head")

        if cmd == "0":
            branches = session.get("branches", [])
            branch_list = "\n".join(f"{i + 1}. 🌿 {b}" for i, b in enumerate(branches))
            set_session(user_id, state="awaiting_pr_head_branch")
            reply(f"📤 *Select the head branch* (your changes):\n\n{branch_list}\n\nReply *0* to go back.")

        elif cmd.isdigit():
            choice = int(cmd)
            if 1 <= choice <= len(base_candidates):
                base_branch = base_candidates[choice - 1]
                set_session(user_id, state="awaiting_pr_title", pr_base=base_branch)
                reply(f"✅ Merging `{pr_head}` → `{base_branch}`\n\n📝 What should the *PR title* be?")
            else:
                reply(f"⚠️ Please enter a number between 1 and {len(base_candidates)}.")

        else:
            reply("⚠️ Reply with the *number* of the base branch or *0* to go back.")

    # ── STATE: awaiting PR title → create PR with AI description ─────────────
    elif session["state"] == "awaiting_pr_title":
        selected_repo = session.get("selected_repo")
        pr_head = session.get("pr_head")
        pr_base = session.get("pr_base")

        reply("⏳ Generating PR description with AI...")

        try:
            commits = get_branch_commits(selected_repo, pr_head, pr_base, **gh)
            description = generate_pr_description(selected_repo, pr_head, pr_base, commits)
        except Exception as e:
            print(f"PR description generation error: {e}")
            description = ""

        try:
            pr = create_pull_request(selected_repo, raw, description, pr_head, pr_base, **gh)
            set_session(user_id, state="awaiting_repo_action")
            reply(
                f"🎉 *Pull Request Created!*\n\n"
                f"📌 {raw}\n"
                f"🌿 `{pr_head}` → `{pr_base}`\n"
                f"🔗 {pr['url']}\n\n"
                "Reply *1* for issues, *2* to commit, or *0* to go back to repo list.",
            )
        except Exception as e:
            print(f"PR create error: {e}")
            reply(
                "❌ Could not create the pull request.\n"
                "Make sure there are commits between the two branches.\n\n"
                "Reply *0* to go back.",
            )
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
