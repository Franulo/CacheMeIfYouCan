import requests
import json

# Load API key & project ID from env vars for safety
API_KEY = "pwtAZmQCwiWHMVFVR48HnqIY238MJe515VPjrVq-t8B3"
PROJECT_ID = "be106dec-5fd0-4d0d-b958-5b980828e551"
URL = "https://eu-de.ml.cloud.ibm.com/ml/v1/text/generation?version=2023-05-29"
MODEL = "ibm/granite-3-3-8b-instruct"  # or "ibm/granite-13b-chat-v2"

def generate_linkedin_post(articles):
    """
    Given a list of articles (dicts with 'title' and 'summary'),
    ask watsonx.ai to generate a LinkedIn post.
    """

    # Step 1: Get IAM token
    token_resp = requests.post(
        "https://iam.cloud.ibm.com/identity/token",
        data={"apikey": API_KEY, "grant_type": "urn:ibm:params:oauth:grant-type:apikey"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token_resp.raise_for_status()
    iam_token = token_resp.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {iam_token}",
        "Content-Type": "application/json"
    }

    # Step 2: Build the input prompt
    article_text = "\n".join(
        [f"- {a['title']}: {a['summary']}" for a in articles]
    )

    prompt = f"""You are a social media assistant.
Write a professional LinkedIn post summarizing the following news articles,
focusing on their impact on the financial markets.
Make it engaging but concise, and highlight the key trends.

Articles:
{article_text}

LinkedIn Post:"""

    payload = {
        "input": prompt,
        "parameters": {
        "decoding_method": "greedy",      # can also try "sample" for more variety
        "max_new_tokens": 500,            # allow a lot more tokens!
        "min_new_tokens": 100             # force it to write more than just one line
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


def generate_podcast_outline(articles):
    """
    Given a list of articles (dicts with 'title' and 'summary'),
    ask watsonx.ai to generate a podcast discussion outline.
    """

    # Step 1: Get IAM token
    token_resp = requests.post(
        "https://iam.cloud.ibm.com/identity/token",
        data={"apikey": API_KEY, "grant_type": "urn:ibm:params:oauth:grant-type:apikey"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token_resp.raise_for_status()
    iam_token = token_resp.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {iam_token}",
        "Content-Type": "application/json"
    }

    # Step 2: Build the input prompt
    article_text = "\n".join(
        [f"- {a['title']}: {a['summary']}" for a in articles]
    )

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

    payload = {
        "input": prompt,
        "parameters": {
        "decoding_method": "greedy",      # can also try "sample" for more variety
        "max_new_tokens": 500,            # allow a lot more tokens!
        "min_new_tokens": 100             # force it to write more than just one line
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
