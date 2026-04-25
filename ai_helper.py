import os
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_ID     = "llama-3.3-70b-versatile"


def generate_weekly_summary(activity: dict) -> str:
    """Generate a friendly weekly GitHub activity digest using Groq."""
    repos_text = ", ".join(activity["repos"]) if activity["repos"] else "none"
    data_text = (
        f"Repositories active: {repos_text}\n"
        f"Push events: {activity['pushes']}\n"
        f"Commits pushed: {activity['commits']}\n"
        f"Issues opened: {activity['issues_opened']}\n"
        f"Pull requests opened: {activity['prs_opened']}"
    )

    prompt = (
        "You are a friendly developer productivity assistant. "
        "Write a short, motivating weekly GitHub activity summary in 4-6 sentences. "
        "Highlight achievements, mention active repos, and encourage continued progress. "
        "Keep it conversational and upbeat.\n\n"
        f"This week's activity:\n{data_text}"
    )

    response = requests.post(
        GROQ_API_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 250,
            "temperature": 0.6,
        },
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def identify_fix_file(issue_title: str, issue_body: str, file_paths: list) -> str:
    """Ask AI which file most likely needs to be changed to fix this issue.
    Returns the file path string (validated against file_paths)."""
    files_text = "\n".join(f"- {p}" for p in file_paths)
    issue_text = issue_body.strip() if issue_body else "No description provided."

    prompt = (
        "You are a software engineering assistant. "
        "Given a GitHub issue and a list of repository files, identify the SINGLE file most likely "
        "to contain the bug or need modification to fix the issue. "
        "Reply with ONLY the exact file path from the list, nothing else.\n\n"
        f"Issue Title: {issue_title}\n\n"
        f"Issue Description:\n{issue_text}\n\n"
        f"Repository files:\n{files_text}"
    )

    response = requests.post(
        GROQ_API_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 60,
            "temperature": 0.1,
        },
    )
    response.raise_for_status()
    candidate = response.json()["choices"][0]["message"]["content"].strip().lstrip("- ").strip()

    # Exact match
    if candidate in file_paths:
        return candidate
    # Partial match (e.g. AI returned filename without path)
    for fp in file_paths:
        if fp.endswith(candidate) or candidate in fp:
            return fp
    # Fallback: first file
    return file_paths[0] if file_paths else ""


def ai_fix_code(filename: str, content: str, description: str) -> str:
    """Rewrite a file applying the described change. Returns only the new file content."""
    prompt = (
        "You are a software engineering assistant. "
        "A developer wants to modify a file. "
        "Apply the requested change and return ONLY the complete new file content. "
        "Do NOT include any explanation, markdown, or code fences — just the raw file text.\n\n"
        f"Filename: {filename}\n\n"
        f"Current content:\n{content}\n\n"
        f"Requested change: {description}"
    )

    response = requests.post(
        GROQ_API_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4096,
            "temperature": 0.2,
        },
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def generate_pr_description(repo_name: str, head: str, base: str, commits: list) -> str:
    """Generate a PR description from branch info and commit messages using Groq."""
    commits_text = "\n".join(f"- {c}" for c in commits) if commits else "- (no commits listed)"

    prompt = (
        "You are a helpful software engineering assistant. "
        "Write a concise GitHub pull request description (2-4 sentences) based on:\n\n"
        f"Repository: {repo_name}\n"
        f"Merging: {head} → {base}\n"
        f"Commits:\n{commits_text}\n\n"
        "Focus on what changes were made and why. Be professional and clear."
    )

    response = requests.post(
        GROQ_API_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200,
            "temperature": 0.4,
        },
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def analyze_issue(title: str, body: str) -> str:
    """Analyze a GitHub issue using Groq (Llama 3.3 70B) and return a fix suggestion."""
    issue_body = body.strip() if body else "No description provided."

    prompt = (
        "You are a helpful software engineering assistant. "
        "Analyze this GitHub issue and provide a concise, actionable fix suggestion in 3-5 sentences.\n\n"
        f"Issue Title: {title}\n\n"
        f"Issue Description:\n{issue_body}"
    )

    response = requests.post(
        GROQ_API_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 300,
            "temperature": 0.3,
        },
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()
