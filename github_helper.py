import requests
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