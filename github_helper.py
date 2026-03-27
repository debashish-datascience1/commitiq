import requests
import base64
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


def get_user_repos():
    """Fetch all repos sorted by last updated."""
    url = f"https://api.github.com/users/{GITHUB_USERNAME}/repos"
    params = {"per_page": 20, "sort": "updated"}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return [repo["name"] for repo in response.json()]


def get_repo_url(repo_name):
    """Get the HTML URL for a specific repo."""
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json().get("html_url", "")


def get_issue_details(repo_name, issue_number):
    """Fetch full details (title + body) of a single issue."""
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/issues/{issue_number}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    return {
        "number": data["number"],
        "title": data["title"],
        "body": data.get("body") or "",
        "url": data["html_url"],
    }


def create_issue(repo_name, title, body=""):
    """Create a new issue in a repo."""
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/issues"
    payload = {"title": title, "body": body}
    response = requests.post(url, headers=HEADERS, json=payload)
    response.raise_for_status()
    data = response.json()
    return {"number": data["number"], "url": data["html_url"]}


def get_repo_contents(repo_name, path=""):
    """List files and folders at a given path in the repo."""
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/contents/{path}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    items = []
    for item in response.json():
        items.append({"name": item["name"], "type": item["type"], "path": item["path"]})
    # Folders first, then files
    items.sort(key=lambda x: (0 if x["type"] == "dir" else 1, x["name"]))
    return items


def get_file_content(repo_name, path):
    """Fetch decoded content and SHA of a file."""
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/contents/{path}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return {"content": content, "sha": data["sha"]}


def get_repo_default_branch(repo_name):
    """Get the default branch name (main/master) of a repo."""
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json().get("default_branch", "main")


def commit_file_change(repo_name, path, new_content, sha, commit_message):
    """Update a file in the repo with a new commit."""
    branch = get_repo_default_branch(repo_name)
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/contents/{path}"
    encoded = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")
    payload = {
        "message": commit_message,
        "content": encoded,
        "sha": sha,
        "branch": branch,
    }
    response = requests.put(url, headers=HEADERS, json=payload)
    response.raise_for_status()
    return response.json()["commit"]["html_url"]


def get_open_issues(repo_name):
    """Fetch all open issues for a repo (excludes pull requests)."""
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/issues"
    params = {"state": "open", "per_page": 20}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()

    issues = []
    for item in response.json():
        # GitHub API returns PRs as issues too — filter them out
        if "pull_request" not in item:
            issues.append({
                "number": item["number"],
                "title": item["title"],
                "url": item["html_url"],
            })
    return issues