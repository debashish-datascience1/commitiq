import os
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_ID     = "llama-3.3-70b-versatile"


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
