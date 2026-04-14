import os
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_ID     = "llama-3.3-70b-versatile"


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
