import os
import json
import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

import requests
from utils import text_file_template
from query_utils import generate_text

NYT_ARCHIVE_URL_TMPL = "https://api.nytimes.com/svc/archive/v1/{year}/{month}.json"

_ALLOWED_SECTIONS = {
    "Business",
    "Job Market",
    "Real Estate",
    "Technology",
}


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


def _clean_json_text(text: str) -> str:
    """Clean malformed JSON text."""
    # Remove any text before the first { and after the last }
    start = text.find('{')
    end = text.rfind('}') + 1
    if start == -1 or end == 0:
        return text
    
    json_part = text[start:end]
    
    # Fix common JSON issues
    cleaned = json_part
    
    # Remove duplicate keys (keep last occurrence)
    cleaned = re.sub(r'"topics":\s*\[.*?\](?=,\s*"topics":)', '', cleaned, flags=re.DOTALL)
    
    # Fix missing commas between objects in arrays
    cleaned = re.sub(r'}\s*{', '},{', cleaned)
    
    # Remove trailing commas in arrays and objects
    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
    
    # Fix duplicate keys by keeping the last occurrence
    lines = cleaned.split('\n')
    unique_lines = []
    seen_keys = set()
    
    for line in lines:
        if '"' in line and ':' in line:
            key_match = re.search(r'"([^"]+)"\s*:', line)
            if key_match:
                key = key_match.group(1)
                if key in seen_keys:
                    continue  # Skip duplicate key
                seen_keys.add(key)
        unique_lines.append(line)
    
    cleaned = '\n'.join(unique_lines)
    
    return cleaned


def _robust_parse_json(text: str) -> Any:
    """Parse JSON with robust error handling and cleaning."""
    print(f"Parsing JSON from text: {text[:200]}...")
    
    # Clean the text first
    cleaned_text = _clean_json_text(text)
    
    try:
        result = json.loads(cleaned_text)
        print(f"Successfully parsed JSON after cleaning")
        return result
    except json.JSONDecodeError as e:
        print(f"JSON parse error after cleaning: {e}")
        print(f"Cleaned text that failed to parse: {cleaned_text}")
        return {"error": f"JSON parse error: {str(e)}", "raw_text": text}
    except Exception as e:
        print(f"Unexpected error parsing JSON: {e}")
        return {"error": str(e), "raw_text": text}


def _clean_json_string(text: str) -> str:
    """Clean malformed JSON string."""
    # Remove any text before first { and after last }
    start = text.find('{')
    end = text.rfind('}') + 1
    if start == -1 or end == 0:
        return '{"daily_overviews": []}'
    
    json_part = text[start:end]
    
    # Fix common issues
    cleaned = json_part
    
    # Fix incomplete strings (like the broken overview)
    cleaned = re.sub(r'"overview":\s*"\s*$', '"overview": "No overview available",', cleaned)
    cleaned = re.sub(r'"overview":\s*"([^"]*)$', r'"overview": "\1"', cleaned)
    
    # Remove trailing commas
    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
    
    # Fix missing quotes
    cleaned = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', cleaned)
    
    # Ensure all strings are properly closed
    lines = cleaned.split('\n')
    fixed_lines = []
    for line in lines:
        if '"overview":' in line and line.count('"') % 2 != 0:
            # Fix unbalanced quotes in overview
            if not line.strip().endswith('"'):
                line = line + '"'
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def _clean_and_validate_json(text: str) -> dict:
    """Clean and validate JSON response from AI model."""
    # First, check if this is an error response from our own function
    if text.strip().startswith('{') and '"error"' in text:
        try:
            result = json.loads(text)
            if "error" in result:
                return result
        except:
            pass
    
    # Handle the malformed "RESPONSE:" format
    if text.strip().startswith('}') or "RESPONSE:" in text:
        print("Detected malformed RESPONSE format, attempting to extract JSON...")
        # Try to find the actual JSON part
        lines = text.split('\n')
        json_lines = []
        in_json = False
        
        for line in lines:
            if line.strip().startswith('{') or ('{' in line and '}' in line):
                in_json = True
            if in_json:
                json_lines.append(line)
            if line.strip().endswith('}') and in_json:
                break
        
        if json_lines:
            json_text = '\n'.join(json_lines)
            print(f"Extracted JSON text: {json_text[:200]}...")
            try:
                result = json.loads(json_text)
                print("Successfully parsed extracted JSON")
                return result
            except json.JSONDecodeError as e:
                print(f"Failed to parse extracted JSON: {e}")
    
    try:
        # First try to parse as-is
        result = json.loads(text)
        print("JSON parsed successfully without cleaning")
        return result
    except json.JSONDecodeError as e:
        print(f"JSON parsing failed: {e}")
        print(f"Raw text that failed to parse: {text[:500]}...")
        
        # Try to extract JSON from malformed text
        try:
            # Find the JSON object in the text
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != 0 and end > start:
                json_part = text[start:end]
                print(f"Attempting to extract JSON part: {json_part[:200]}...")
                return json.loads(json_part)
        except json.JSONDecodeError:
            print("Failed to extract JSON part")
        
        # If all else fails, return structure with raw_text for debugging
        return {
            "error": "JSON parsing failed",
            "raw_text": text[:1000]  # First 1000 characters for debugging
        }


def _call_json_model(prompt: str, tabType: str) -> Any:
    """Call external model and parse JSON robustly."""
    print("Calling model...")
    
    # Check if we should use fallback (for development)
    use_fallback = os.getenv('USE_FALLBACK', 'false').lower() == 'true'
    if use_fallback:
        print("Using fallback mode (watsonx.ai disabled)")
        return _generate_fallback_response(tabType)
    
    text = generate_text(prompt, 3000, 200)
    print("finished model call")
    
    # Use the cleaning function
    return _clean_and_validate_json(text)

def _generate_fallback_response(tabType: str = "Daily") -> dict:
    """
    Generate a realistic fallback response with longer overviews.
    Supports Daily, Weekly and Monthly structures.
    """
    if tabType == "Weekly":
        # Weekly structure — array of weeks
        return {
            "weekly_overviews": [
                {
                    "week": "2024-W01",
                    "overview": (
                        "During the first week of 2024, financial markets experienced "
                        "moderate volatility as investors evaluated mixed economic "
                        "data from the US and Europe. The Federal Reserve hinted at "
                        "holding rates steady, boosting equities mid-week, while "
                        "energy prices rose due to colder weather forecasts. "
                        "Tech stocks remained resilient but banking shares lagged."
                    ),
                    "topics": [
                        {
                            "title": "Federal Reserve Holds Rates Steady",
                            "summary": (
                                "The Fed signaled a pause in interest rate hikes, "
                                "reassuring investors concerned about tightening financial conditions."
                            ),
                            "tags": ["Federal Reserve", "Interest Rates", "Economy"],
                            "url": "https://www.nytimes.com/2024/01/03/business/fed-holds-rates.html",
                            "relevance": "high"
                        },
                        {
                            "title": "Energy Prices Climb on Cold Weather",
                            "summary": (
                                "Crude oil and natural gas futures advanced as meteorologists forecast "
                                "an extended cold spell in North America and Europe."
                            ),
                            "tags": ["Energy", "Oil", "Natural Gas"],
                            "url": "https://www.nytimes.com/2024/01/04/business/energy-prices-winter.html",
                            "relevance": "medium"
                        }
                    ]
                },
                {
                    "week": "2024-W02",
                    "overview": (
                        "In the second week of January, corporate earnings season kicked off. "
                        "Several major banks posted solid profits but flagged weaker loan demand. "
                        "Markets were buoyed by strong retail sales data, although inflation "
                        "remained above target in key European economies. Investors continued "
                        "to rotate into defensive sectors."
                    ),
                    "topics": [
                        {
                            "title": "Big Banks Post Mixed Earnings",
                            "summary": (
                                "Major US banks reported profits above expectations but warned "
                                "that credit growth may slow in 2024."
                            ),
                            "tags": ["Banking", "Earnings", "Credit"],
                            "url": "https://www.nytimes.com/2024/01/09/business/banks-earnings.html",
                            "relevance": "high"
                        }
                    ]
                }
            ]
        }

    elif tabType == "Monthly":
        # Monthly structure — single object with month and topics
        return {
            "monthly_overview": {
                "month": "2024-01",
                "overview": (
                    "January 2024 was marked by a cautiously optimistic tone across global markets. "
                    "US equities closed the month higher after data showed easing inflation and "
                    "steady job growth. Europe’s energy crisis subsided, boosting manufacturing "
                    "activity, while Asian economies benefited from increased export demand. "
                    "However, geopolitical tensions and supply chain concerns continued to cast "
                    "a shadow over global trade forecasts."
                ),
                "topics": [
                    {
                        "title": "US Stocks Gain on Easing Inflation",
                        "summary": (
                            "Equities rallied as consumer price data suggested inflation pressures "
                            "were cooling faster than expected."
                        ),
                        "tags": ["Inflation", "Stocks", "US Economy"],
                        "url": "https://www.nytimes.com/2024/01/30/business/us-stocks-inflation.html",
                        "relevance": "high"
                    },
                    {
                        "title": "Europe’s Manufacturing Rebounds",
                        "summary": (
                            "Lower energy costs and improved supply chains fueled an uptick "
                            "in European manufacturing output."
                        ),
                        "tags": ["Europe", "Manufacturing", "Energy"],
                        "url": "https://www.nytimes.com/2024/01/25/business/europe-manufacturing-rebound.html",
                        "relevance": "medium"
                    }
                ]
            }
        }

    else:
        # Daily structure — array of days
        return {
            "daily_overviews": [
                {
                    "date": "2024-01-04",
                    "overview": (
                        "Markets opened the year with cautious optimism. The Dow Jones and S&P 500 "
                        "gained modestly as investors digested the latest US employment figures. "
                        "Bond yields eased after the Treasury auction attracted strong demand, "
                        "while tech giants saw continued inflows from institutional investors."
                    ),
                    "topics": [
                        {
                            "title": "Strong Demand at Treasury Auction",
                            "summary": (
                                "A robust auction of US Treasury notes signaled investor confidence "
                                "in long-term government debt."
                            ),
                            "tags": ["Bonds", "Treasury Auction", "Markets"],
                            "url": "https://www.nytimes.com/2024/01/04/business/treasury-auction.html",
                            "relevance": "medium"
                        }
                    ]
                },
                {
                    "date": "2024-01-05",
                    "overview": (
                        "The second trading day saw mixed performances as tech shares rose but "
                        "financials lagged. Analysts cited profit-taking in energy and industrials "
                        "after a strong December. Meanwhile, the dollar strengthened against major "
                        "currencies as investors looked for safe havens."
                    ),
                    "topics": [
                        {
                            "title": "Dollar Strengthens Amid Global Uncertainty",
                            "summary": (
                                "Currency markets responded to shifting risk sentiment, pushing "
                                "the dollar index to a two-week high."
                            ),
                            "tags": ["Dollar", "Currencies", "Global Markets"],
                            "url": "https://www.nytimes.com/2024/01/05/business/dollar-strengthens.html",
                            "relevance": "high"
                        }
                    ]
                }
            ]
        }



def _validate_and_clean_data(data, expected_key: str):
    """
    Validate and clean data coming from model_output depending on tabType.
    - daily_overviews → list of daily dicts
    - weekly_overviews → list of weekly dicts
    - monthly_overview → single dict
    """

    # Handle None
    if data is None:
        if expected_key == "monthly_overview":
            return {"overview": "", "topics": []}
        else:
            return []

    # Monthly → dict
    if expected_key == "monthly_overview":
        if isinstance(data, dict):
            return _clean_data_item(data, expected_key)
        elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            # If model returns a list with one dict, unwrap it
            return _clean_data_item(data[0], expected_key)
        else:
            return {"overview": "", "topics": []}

    # Daily / Weekly → list of dicts
    if isinstance(data, list):
        cleaned_list = []
        for item in data:
            cleaned_item = _clean_data_item(item, expected_key)
            if cleaned_item:
                cleaned_list.append(cleaned_item)
        return cleaned_list

    # Model sometimes returns a single dict instead of list
    if isinstance(data, dict):
        cleaned_item = _clean_data_item(data, expected_key)
        return [cleaned_item] if cleaned_item else []

    # Unknown type → return empty
    return [] if expected_key != "monthly_overview" else {"overview": "", "topics": []}



def _clean_data_item(item: dict, expected_key: str) -> dict:
    """
    Clean a single data item depending on tabType.
    For monthly_overview we expect a dict with keys overview + topics.
    For daily/weekly we expect each topic item to have the usual fields.
    """
    if not isinstance(item, dict):
        return None

    if expected_key == "monthly_overview":
        # Just make sure it has the minimal fields
        return {
            "overview": item.get("overview", "No overview available."),
            "topics": item.get("topics", [])
        }

    # Daily or weekly items
    cleaned = {
        "date": item.get("date", ""),
        "overview": item.get("overview", "No overview available."),
        "topics": []
    }
    for t in item.get("topics", []):
        if isinstance(t, dict):
            cleaned_topic = {
                "title": t.get("title", ""),
                "summary": t.get("summary", ""),
                "tags": t.get("tags", []),
                "url": t.get("url", ""),
                "relevance": t.get("relevance", "low")
            }
            cleaned["topics"].append(cleaned_topic)
    return cleaned



def run_nyt_openai_pipeline(
    year: int,
    month: int,
    model_name: Optional[str] = None,
    custom_search: Optional[str] = None,
    tabType: str = "Daily"
) -> Dict[str, Any]:
    """
    Fetch NYT Archive for (year, month), run a single prompt through IBM watsonx.ai
    and return consistent JSON structure for frontend consumption.
    Supports Daily, Weekly and Monthly.
    """
    print(f"Starting pipeline for {year}-{month}, search: '{custom_search}', tab: '{tabType}'")

    # Fetch NYT archive
    try:
        archive = _fetch_nyt_archive(year, month)
        if isinstance(archive, dict) and archive.get("error"):
            print(f"Archive fetch error: {archive.get('error')}")
            return {
                "month": f"{year:04d}-{month:02d}",
                "tabType": tabType,
                "data": {
                    "error": archive.get("error"),
                    "daily_overviews": []
                }
            }
        print(f"Successfully fetched {len(archive)} articles from NYT archive")
    except Exception as e:
        error_msg = f"Error fetching NYT archive: {str(e)}"
        print(error_msg)
        return {
            "month": f"{year:04d}-{month:02d}",
            "tabType": tabType,
            "data": {
                "error": error_msg,
                "daily_overviews": []
            }
        }

    month_str = f"{year:04d}-{month:02d}"
    context = {"custom_search": custom_search or ""}

    # Pick correct prompt
    prompt_file_map = {
        "Daily": os.path.join("prompts", "daily_prompt.txt"),
        "Weekly": os.path.join("prompts", "weekly_prompt.txt"),
        "Monthly": os.path.join("prompts", "monthly_prompt.txt"),
    }
    prompt_file = prompt_file_map.get(tabType, prompt_file_map["Daily"])

    # Model call
    try:
        prompt_text = text_file_template(prompt_file, context)
        model_input = _make_prompt(prompt_text, archive, custom_search)
        model_output = _call_json_model(model_input, tabType)
    except Exception as e:
        error_msg = f"Error in prompt generation or model call: {str(e)}"
        print(error_msg)
        return {
            "month": month_str,
            "tabType": tabType,
            "data": {
                "error": error_msg,
                "daily_overviews": []
            }
        }

    # Map tabType to expected keys
    key_map = {
        "Daily": "daily_overviews",
        "Weekly": "weekly_overviews",
        "Monthly": "monthly_overview",  # monthly is a single overview
    }
    expected_key = key_map.get(tabType, "daily_overviews")

    # Extract and validate
    data = {}
    if isinstance(model_output, dict):
        print(f"Model output is dict with keys: {list(model_output.keys())}")

        if "error" in model_output:
            # Model error
            error_data = {
                "error": model_output.get("error"),
                "raw_text": model_output.get("raw_text", "")[:500] if model_output.get("raw_text") else None,
                expected_key: []
            }
            data = error_data

        elif expected_key in model_output:
            # Found the correct key
            extracted_data = model_output[expected_key]
            print(f"Found expected key '{expected_key}', type: {type(extracted_data)}")

            cleaned_data = _validate_and_clean_data(extracted_data, expected_key)
            data = {expected_key: cleaned_data}

        else:
            # Unexpected format
            print(f"Expected key '{expected_key}' not found, using full model output")
            data = {expected_key: _validate_and_clean_data(model_output, expected_key)}
    else:
        # Non-dict model output
        cleaned_data = _validate_and_clean_data(model_output, expected_key)
        data = {expected_key: cleaned_data}

    # Ensure key exists
    if expected_key not in data:
        data[expected_key] = [] if tabType != "Monthly" else {}

    # Metadata
    data["_metadata"] = {
        "model_output_type": str(type(model_output)),
        "expected_key": expected_key,
        "processing_time": datetime.now().isoformat()
    }

    count_items = len(data.get(expected_key, [])) if isinstance(data.get(expected_key), list) else 1
    print(f"Pipeline completed successfully, returning {count_items} items")

    return {
        "month": month_str,
        "tabType": tabType,
        "data": data
    }
