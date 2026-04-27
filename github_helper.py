import requests
import base64
import os
from dotenv import load_dotenv

load_dotenv()

_DEFAULT_TOKEN    = os.getenv("GITHUB_TOKEN")
_DEFAULT_USERNAME = os.getenv("GITHUB_USERNAME")


def _headers(token=None):
    t = token or _DEFAULT_TOKEN
    return {
        "Authorization": f"token {t}",
        "Accept": "application/vnd.github.v3+json",
    }


def get_user_repos(token=None, username=None):
    """Fetch all repos sorted by last updated."""
    username = username or _DEFAULT_USERNAME
    url = f"https://api.github.com/users/{username}/repos"
    response = requests.get(url, headers=_headers(token), params={"per_page": 20, "sort": "updated"})
    response.raise_for_status()
    return [repo["name"] for repo in response.json()]


def get_repo_url(repo_name, token=None, username=None):
    """Get the HTML URL for a specific repo."""
    username = username or _DEFAULT_USERNAME
    url = f"https://api.github.com/repos/{username}/{repo_name}"
    response = requests.get(url, headers=_headers(token))
    response.raise_for_status()
    return response.json().get("html_url", "")


def get_issue_details(repo_name, issue_number, token=None, username=None):
    """Fetch full details (title + body) of a single issue."""
    username = username or _DEFAULT_USERNAME
    url = f"https://api.github.com/repos/{username}/{repo_name}/issues/{issue_number}"
    response = requests.get(url, headers=_headers(token))
    response.raise_for_status()
    data = response.json()
    return {
        "number": data["number"],
        "title": data["title"],
        "body": data.get("body") or "",
        "url": data["html_url"],
    }


def create_issue(repo_name, title, body="", token=None, username=None):
    """Create a new issue in a repo."""
    username = username or _DEFAULT_USERNAME
    url = f"https://api.github.com/repos/{username}/{repo_name}/issues"
    response = requests.post(url, headers=_headers(token), json={"title": title, "body": body})
    response.raise_for_status()
    data = response.json()
    return {"number": data["number"], "url": data["html_url"]}


def get_repo_contents(repo_name, path="", token=None, username=None):
    """List files and folders at a given path in the repo."""
    username = username or _DEFAULT_USERNAME
    url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{path}"
    response = requests.get(url, headers=_headers(token))
    response.raise_for_status()
    items = [
        {"name": item["name"], "type": item["type"], "path": item["path"]}
        for item in response.json()
    ]
    items.sort(key=lambda x: (0 if x["type"] == "dir" else 1, x["name"]))
    return items


def get_file_content(repo_name, path, token=None, username=None):
    """Fetch decoded content and SHA of a file."""
    username = username or _DEFAULT_USERNAME
    url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{path}"
    response = requests.get(url, headers=_headers(token))
    response.raise_for_status()
    data = response.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return {"content": content, "sha": data["sha"]}


def get_repo_default_branch(repo_name, token=None, username=None):
    """Get the default branch name (main/master) of a repo."""
    username = username or _DEFAULT_USERNAME
    url = f"https://api.github.com/repos/{username}/{repo_name}"
    response = requests.get(url, headers=_headers(token))
    response.raise_for_status()
    return response.json().get("default_branch", "main")


def commit_file_change(repo_name, path, new_content, sha, commit_message, token=None, username=None):
    """Update a file in the repo with a new commit."""
    username = username or _DEFAULT_USERNAME
    branch = get_repo_default_branch(repo_name, token=token, username=username)
    url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{path}"
    encoded = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")
    payload = {
        "message": commit_message,
        "content": encoded,
        "sha": sha,
        "branch": branch,
    }
    response = requests.put(url, headers=_headers(token), json=payload)
    response.raise_for_status()
    return response.json()["commit"]["html_url"]


def get_branches(repo_name, token=None, username=None):
    """List all branches in a repo."""
    username = username or _DEFAULT_USERNAME
    url = f"https://api.github.com/repos/{username}/{repo_name}/branches"
    response = requests.get(url, headers=_headers(token), params={"per_page": 30})
    response.raise_for_status()
    return [b["name"] for b in response.json()]


def create_branch(repo_name, new_branch, from_branch, token=None, username=None):
    """Create a new branch from an existing branch."""
    username = username or _DEFAULT_USERNAME
    ref_url = f"https://api.github.com/repos/{username}/{repo_name}/git/ref/heads/{from_branch}"
    ref_resp = requests.get(ref_url, headers=_headers(token))
    ref_resp.raise_for_status()
    sha = ref_resp.json()["object"]["sha"]

    url = f"https://api.github.com/repos/{username}/{repo_name}/git/refs"
    response = requests.post(url, headers=_headers(token), json={
        "ref": f"refs/heads/{new_branch}",
        "sha": sha,
    })
    response.raise_for_status()
    return new_branch


def get_branch_commits(repo_name, head, base, token=None, username=None):
    """Return up to 10 commit messages on head that are not in base."""
    username = username or _DEFAULT_USERNAME
    url = f"https://api.github.com/repos/{username}/{repo_name}/compare/{base}...{head}"
    response = requests.get(url, headers=_headers(token))
    response.raise_for_status()
    commits = [c["commit"]["message"].split("\n")[0] for c in response.json().get("commits", [])]
    return commits[:10]


def create_pull_request(repo_name, title, body, head, base, token=None, username=None):
    """Open a pull request."""
    username = username or _DEFAULT_USERNAME
    url = f"https://api.github.com/repos/{username}/{repo_name}/pulls"
    response = requests.post(url, headers=_headers(token), json={
        "title": title,
        "body": body,
        "head": head,
        "base": base,
    })
    response.raise_for_status()
    data = response.json()
    return {"number": data["number"], "url": data["html_url"]}


def get_weekly_activity(token=None, username=None):
    """Fetch user's public events from the past 7 days and return a summary dict."""
    from datetime import datetime, timedelta, timezone
    username = username or _DEFAULT_USERNAME
    url = f"https://api.github.com/users/{username}/events"
    response = requests.get(url, headers=_headers(token), params={"per_page": 100})
    response.raise_for_status()

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    pushes = issues_opened = prs_opened = commits = 0
    repos = set()

    for event in response.json():
        created = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
        if created < cutoff:
            break
        repo = event["repo"]["name"].split("/")[-1]
        repos.add(repo)
        if event["type"] == "PushEvent":
            pushes += 1
            commits += event["payload"].get("size", 0)
        elif event["type"] == "IssuesEvent" and event["payload"].get("action") == "opened":
            issues_opened += 1
        elif event["type"] == "PullRequestEvent" and event["payload"].get("action") == "opened":
            prs_opened += 1

    return {
        "repos": sorted(repos),
        "pushes": pushes,
        "commits": commits,
        "issues_opened": issues_opened,
        "prs_opened": prs_opened,
    }


def close_issue(repo_name, issue_number, token=None, username=None):
    """Close an issue by number."""
    username = username or _DEFAULT_USERNAME
    url = f"https://api.github.com/repos/{username}/{repo_name}/issues/{issue_number}"
    response = requests.patch(url, headers=_headers(token), json={"state": "closed"})
    response.raise_for_status()
    return response.json()["html_url"]


def get_open_prs(repo_name, token=None, username=None):
    """List all open pull requests for a repo."""
    username = username or _DEFAULT_USERNAME
    url = f"https://api.github.com/repos/{username}/{repo_name}/pulls"
    response = requests.get(url, headers=_headers(token), params={"state": "open", "per_page": 20})
    response.raise_for_status()
    return [
        {
            "number": pr["number"],
            "title": pr["title"],
            "head": pr["head"]["ref"],
            "base": pr["base"]["ref"],
            "url": pr["html_url"],
        }
        for pr in response.json()
    ]


def get_open_issues(repo_name, token=None, username=None):
    """Fetch all open issues for a repo (excludes pull requests)."""
    username = username or _DEFAULT_USERNAME
    url = f"https://api.github.com/repos/{username}/{repo_name}/issues"
    response = requests.get(url, headers=_headers(token), params={"state": "open", "per_page": 20})
    response.raise_for_status()
    issues = []
    for item in response.json():
        if "pull_request" not in item:
            issues.append({
                "number": item["number"],
                "title": item["title"],
                "url": item["html_url"],
            })
    return issues
