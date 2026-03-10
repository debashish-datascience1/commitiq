import requests
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")


def get_user_repos():
    """Fetch all repos for the configured GitHub user, sorted by last updated."""
    url = f"https://api.github.com/users/{GITHUB_USERNAME}/repos"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    params = {"per_page": 20, "sort": "updated"}

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    repos = response.json()
    return [repo["name"] for repo in repos]


def get_repo_url(repo_name):
    """Get the HTML URL for a specific repo."""
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json().get("html_url", "")