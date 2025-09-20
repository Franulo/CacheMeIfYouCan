import requests
import json

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


def generate_text(prompt, max_tokens, min_tokens, decoding_method="greedy"):
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
    if not resp.ok:
        # Return structured error so callers can see details in logs
        try:
            err = resp.json()
        except Exception:
            err = {"raw": resp.text}
        return json.dumps({"error": err, "status_code": resp.status_code}, indent=2)
    result = resp.json()

    try:
        return result["results"][0]["generated_text"].strip()
    except Exception:
        return json.dumps(result, indent=2)
