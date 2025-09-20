import requests
import json

API_KEY = "pwtAZmQCwiWHMVFVR48HnqIY238MJe515VPjrVq-t8B3"
URL = "https://eu-de.ml.cloud.ibm.com/ml/v1/text/generation?version=2023-05-29"
PROJECT_ID = "be106dec-5fd0-4d0d-b958-5b980828e551"

# Get IAM token
token_resp = requests.post(
    "https://iam.cloud.ibm.com/identity/token",
    data={"apikey": API_KEY, "grant_type": "urn:ibm:params:oauth:grant-type:apikey"},
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)
iam_token = token_resp.json()["access_token"]

headers = {
    "Authorization": f"Bearer {iam_token}",
    "Content-Type": "application/json"
}

payload = {
    "input": """ Write a long poem about the vanity of human wishes.""",
    "parameters": {
        "decoding_method": "greedy",
        "max_new_tokens": 50,
    },
    "model_id": "ibm/granite-13b-instruct-v2",  # Large model, adjust if needed
    "project_id": PROJECT_ID      # From watsonx.ai Studio project
}

resp = requests.post(URL, headers=headers, json=payload)
print(json.dumps(resp.json(), indent=2))
