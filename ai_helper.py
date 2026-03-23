import boto3
import json
import os
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

bedrock = boto3.client(
    service_name="bedrock-runtime",
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)


def analyze_issue(title: str, body: str) -> str:
    """Send a GitHub issue to Claude Haiku via Bedrock and return a fix suggestion."""
    issue_body = body.strip() if body else "No description provided."

    prompt = (
        f"You are a helpful software engineering assistant. "
        f"Analyze this GitHub issue and provide a concise, actionable fix suggestion in 3-5 sentences.\n\n"
        f"Issue Title: {title}\n\n"
        f"Issue Description:\n{issue_body}"
    )

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
    }

    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(payload),
        contentType="application/json",
        accept="application/json",
    )

    result = json.loads(response["body"].read())
    return result["content"][0]["text"].strip()
