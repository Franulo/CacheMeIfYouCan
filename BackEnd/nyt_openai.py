import os
import json
from typing import Any, Dict

import requests
from utils import text_file_template
from query_utils import generate_text


NYT_ARCHIVE_URL_TMPL = "https://api.nytimes.com/svc/archive/v1/{year}/{month}.json"


def _remove_key_recursive(obj: Any, key_to_remove: str) -> Any:
    if isinstance(obj, dict):
        if key_to_remove in obj:
            obj.pop(key_to_remove, None)
        for k, v in list(obj.items()):
            obj[k] = _remove_key_recursive(v, key_to_remove)
        return obj
    if isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = _remove_key_recursive(obj[i], key_to_remove)
        return obj
    return obj


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


_ALLOWED_SECTIONS = {
    "Business",
    "Job Market",
    "Real Estate",
    "Technology",
}


def _trim_archive_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove heavy fields and filter out non-relevant sections."""
    if not isinstance(data, dict):
        return data
    response = data.get("response")
    if not isinstance(response, dict):
        return data
    docs = response.get("docs")
    if not isinstance(docs, list):
        return data

    trimmed_docs = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        section_name = doc.get("section_name")
        # Only allow specific sections; drop others or missing
        if not (isinstance(section_name, str) and section_name in _ALLOWED_SECTIONS):
            continue
        # Drop heavy/unneeded fields
        for k in (
            "byline",
            "type_of_material",
            "_id",
            "word_count",
            "keywords",
            "document_type",
            "uri",
            "snippet",
            "headline",
            "source",
            "lead_paragraph",
            # Remove desk/section labels before sending to model
            "news_desk",
            "subsection_name",
            # Remove print metadata
            "print_section",
            "print_page",
        ):
            if k in doc:
                doc.pop(k, None)
        # Trim headline subfields
        headline = doc.get("headline")
        if isinstance(headline, dict):
            for hk in ("kicker", "content_kicker", "print_headline", "name", "seo", "sub"):
                if hk in headline:
                    headline.pop(hk, None)
        trimmed_docs.append(doc)

    response["docs"] = trimmed_docs
    data["response"] = response
    return data


def _fetch_nyt_archive(year: int, month: int) -> Dict[str, Any]:
    api_key = os.getenv("NYT_API_KEY")
    if not api_key:
        return {"error": "Missing NYT_API_KEY environment variable", "status_code": 500}

    url = NYT_ARCHIVE_URL_TMPL.format(year=year, month=month)
    resp = requests.get(url, params={"api-key": api_key})
    if resp.status_code != 200:
        try:
            raw_text = resp.text
        except Exception:
            raw_text = "<no text>"
        return {"error": "Failed to fetch NYT Archive", "status_code": resp.status_code, "raw": raw_text}

    data = resp.json()
    # Strip multimedia to reduce payload size
    data = _remove_key_recursive(data, "multimedia")
    # Remove specified fields and filter out excluded sections
    data = _trim_archive_payload(data)
    return data


def _make_prompt(prompt_text: str, data: Dict[str, Any], custom_search: str | None) -> str:
    # custom_search is injected directly into prompt_text via {custom_search};
    # only append the DATA_JSON block here.
    return (
        f"{prompt_text}\n\n"
        f"DATA_JSON\n"
        f"{json.dumps(data, ensure_ascii=False)}\n"
    )


def _robust_parse_json(text: str) -> Any:
    text = text.strip()
    # Fast path
    try:
        return json.loads(text)
    except Exception:
        pass

    # Try to extract the largest JSON object segment
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = text[start : end + 1]
        try:
            return json.loads(snippet)
        except Exception:
            pass
    # As fallback, return raw text
    return {"raw_text": text}


def _call_json_model(prompt: str) -> Any:
    """Call external model (IBM watsonx.ai) and parse JSON robustly."""
    text = generate_text(prompt, 3000, 200)
    return _robust_parse_json(text)


def run_nyt_openai_pipeline(year: int, month: int, model_name: str | None = None, custom_search: str | None = None) -> Dict[str, Any]:
    """
    Fetch NYT Archive for (year, month), then run three prompts (daily, weekly, monthly)
    through IBM watsonx.ai and return a combined JSON with normalized keys.
    """
    archive = _fetch_nyt_archive(year, month)
    if isinstance(archive, dict) and archive.get("error"):
        return archive

    month_str = f"{year:04d}-{month:02d}"

    daily_prompt = text_file_template(os.path.join("prompts", "daily_prompt.txt"), {"custom_search": (custom_search or "")})
    weekly_prompt = text_file_template(os.path.join("prompts", "weekly_prompt.txt"), {"custom_search": (custom_search or "")})
    monthly_prompt = text_file_template(os.path.join("prompts", "monthly_prompt.txt"), {"custom_search": (custom_search or "")})

    daily_in = _make_prompt(daily_prompt, archive, custom_search)
    weekly_in = _make_prompt(weekly_prompt, archive, custom_search)
    monthly_in = _make_prompt(monthly_prompt, archive, custom_search)

    # Sequential calls to reduce load; adjust max/min tokens inside generate_text as needed
    daily_json = _call_json_model(daily_in)
    weekly_json = _call_json_model(weekly_in)
    monthly_json = _call_json_model(monthly_in)

    # Normalize to a single object with stable keys
    result: Dict[str, Any] = {"month": month_str}

    # Extract arrays/objects from model outputs if they include wrappers
    if isinstance(daily_json, dict) and "daily_overviews" in daily_json:
        result["daily_overviews"] = daily_json.get("daily_overviews")
    else:
        result["daily_overviews"] = daily_json

    if isinstance(weekly_json, dict) and "weekly_overviews" in weekly_json:
        result["weekly_overviews"] = weekly_json.get("weekly_overviews")
    else:
        result["weekly_overviews"] = weekly_json

    if isinstance(monthly_json, dict) and "monthly_overview" in monthly_json:
        result["monthly_overview"] = monthly_json.get("monthly_overview")
    else:
        result["monthly_overview"] = monthly_json

    return result


