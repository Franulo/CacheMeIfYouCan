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
    print("Generating text...")
    """Generate text using watsonx.ai."""
    iam_token = get_iam_token()
    if not iam_token:
        print("Failed to get IAM token")
        return json.dumps({"error": "Failed to get IAM token"})
    
    print("Got IAM token")

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
    
    try:
        print("Sending request to watsonx.ai...")
        resp = requests.post(URL, headers=headers, json=payload, timeout=300)
        print(f"Response status: {resp.status_code}")
        
        # Check if response is successful
        if resp.status_code != 200:
            error_msg = f"API returned status {resp.status_code}: {resp.text}"
            print(error_msg)
            return json.dumps({"error": error_msg, "status_code": resp.status_code})
        
        result = resp.json()
        print("Successfully parsed response JSON")
        return result["results"][0]["generated_text"].strip()
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Request failed: {str(e)}"
        print(error_msg)
        return json.dumps({"error": error_msg, "type": "request_error"})
    except Exception as e:
        error_msg = f"Error processing response: {str(e)}"
        print(error_msg)
        if 'resp' in locals():  # Check if resp exists
            print(f"Response text: {resp.text}")
            return json.dumps({"error": error_msg, "response": resp.text})
        return json.dumps({"error": error_msg})
