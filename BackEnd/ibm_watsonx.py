import requests
import json
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# IBM Cloud details
API_KEY = "pwtAZmQCwiWHMVFVR48HnqIY238MJe515VPjrVq-t8B3"
PROJECT_ID = "be106dec-5fd0-4d0d-b958-5b980828e551"
URL = "https://eu-de.ml.cloud.ibm.com/ml/v1/text/generation?version=2023-05-29"
MODEL = "ibm/granite-3-3-8b-instruct"  # or "ibm/granite-13b-chat-v2"

def get_iam_token():
    """Fetch IAM token from IBM Cloud."""
    token_resp = requests.post(
        "https://iam.cloud.ibm.com/identity/token",
        data={"apikey": API_KEY, "grant_type": "urn:ibm:params:oauth:grant-type:apikey"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token_resp.raise_for_status()
    return token_resp.json()["access_token"]

def generate_text(prompt, max_tokens=500, min_tokens=100, decoding_method="greedy"):
    """Generate text using watsonx.ai."""
    iam_token = get_iam_token()
    headers = {
        "Authorization": f"Bearer {iam_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "input": prompt,
        "parameters": {
            "decoding_method": decoding_method,
            "max_new_tokens": max_tokens,
            "min_new_tokens": min_tokens
        },
        "model_id": MODEL,
        "project_id": PROJECT_ID
    }

    resp = requests.post(URL, headers=headers, json=payload)
    resp.raise_for_status()
    result = resp.json()

    try:
        return result["results"][0]["generated_text"].strip()
    except Exception:
        return json.dumps(result, indent=2)

def generate_linkedin_post(articles):
    """Generate a professional LinkedIn post from article list."""
    article_text = "\n".join([f"- {a['title']}: {a['summary']}" for a in articles])
    prompt = f"""You are a social media assistant.
Write a professional LinkedIn post summarizing the following news articles,
focusing on their impact on the financial markets.
Make it engaging but concise, and highlight the key trends.

Articles:
{article_text}

LinkedIn Post:"""
    return generate_text(prompt)

def generate_podcast_outline(articles):
    """Generate a podcast episode outline from article list."""
    article_text = "\n".join([f"- {a['title']}: {a['summary']}" for a in articles])
    prompt = f"""You are a podcast producer.
Create an outline for a podcast episode discussing the following news articles.
The outline should include:
1. A catchy episode title
2. A short intro script
3. 3–5 key discussion topics
4. Possible questions for each topic to engage the hosts and audience

Articles:
{article_text}

Podcast Outline:"""
    return generate_text(prompt)

def generate_pdf(title, text, filename="output.pdf"):
    """Save generated text to a PDF using ReportLab."""
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(filename)
    story = []

    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 12))
    for line in text.split("\n"):
        story.append(Paragraph(line, styles["Normal"]))
        story.append(Spacer(1, 6))

    doc.build(story)
    return filename

