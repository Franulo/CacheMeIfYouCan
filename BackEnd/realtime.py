import os
import json
from typing import Any, Dict, List, Optional

from openai import OpenAI
import openai as openai_pkg
import requests as httpx
from utils import text_file_template


def _ensure_openai_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        alt = os.getenv("OPENAI_API_KEY_ANYPREP")
        if alt:
            os.environ["OPENAI_API_KEY"] = alt


def _collect_source_urls(obj: Any) -> List[str]:
    urls: List[str] = []
    try:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "sources" and isinstance(v, list):
                    for s in v:
                        if isinstance(s, dict) and isinstance(s.get("url"), str):
                            urls.append(s["url"]) 
                urls.extend(_collect_source_urls(v))
        elif isinstance(obj, list):
            for it in obj:
                urls.extend(_collect_source_urls(it))
    except Exception:
        pass
    # De-duplicate while preserving order
    seen = set()
    deduped = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            deduped.append(u)
    return deduped


def get_realtime_finance(existing_feed: Optional[List[Dict[str, Any]]] = None,
                         query: Optional[str] = None,
                         hours: int = 24,
                         limit: int = 20) -> Dict[str, Any]:
    """
    Use OpenAI web_search with the oai-finance feed to return finance news from the last
    `hours` hours. Returns a JSON with a compact summary, items, and the complete list of
    consulted sources (including oai-finance if used).

    Parameters:
      - existing_feed: optional pre-fetched items to consider for deduplication/context
      - query: optional focus term (e.g., "AI chips and US tech stocks")
      - hours: time window (default 24)
      - limit: suggested number of items (best-effort)
    """
    _ensure_openai_key()
    client = OpenAI()

    user_focus = (query or "latest market, macro, companies, policy developments")
    existing_blob = "\n".join(
        [json.dumps(x, ensure_ascii=False) for x in (existing_feed or [])][:200]
    )

    tmpl_path = os.path.join("prompts", "realtime.txt")
    prompt = text_file_template(tmpl_path, {"current_feed": existing_blob, "custom_search": user_focus})

    # Guard: ensure installed SDK supports Responses API with web_search. If not, use HTTP fallback.
    use_http_fallback = not hasattr(client, "responses")

    try:
        if not use_http_fallback:
            resp = client.responses.create(
                model="gpt-4.1-mini",
                tools=[
                    {
                        "type": "web_search",
                        # Prefer finance-focused real-time feed
                    }
                ],
                tool_choice="auto",
                include=["web_search_call.action.sources"],
                input=prompt,
                # Ask the model to respond with a pure JSON object
                response_format={"type": "json_object"},
            )
        else:
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY_ANYPREP")
            if not api_key:
                return {"error": "Missing OPENAI_API_KEY"}
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "gpt-4.1-mini",
                "tools": [
                    {"type": "web_search"}
                ],
                "tool_choice": "auto",
                "include": ["web_search_call.action.sources"],
                "input": prompt,
                # Omit explicit JSON format; rely on prompt to return strict JSON
            }
            r = httpx.post("https://api.openai.com/v1/responses", headers=headers, json=payload)
            if not r.ok:
                try:
                    err = r.json()
                except Exception:
                    err = {"raw": r.text}
                return {"error": err, "status_code": r.status_code}
            resp = r.json()
    except Exception as e:
        return {"error": f"OpenAI request failed: {e}"}

    # Extract model text (expected JSON) and sources
    try:
        if not use_http_fallback:
            output_text = resp.output_text
        else:
            # Extract text from raw REST response
            output_text = ""
            try:
                out = resp.get("output", [])
                for part in out:
                    if isinstance(part, dict):
                        content = part.get("content") or []
                        for c in content:
                            if isinstance(c, dict) and c.get("type") in ("output_text", "text"):
                                t = c.get("text")
                                if isinstance(t, str):
                                    output_text += t
                if not output_text:
                    output_text = resp.get("output_text", "{}")
            except Exception:
                output_text = resp.get("output_text", "{}")
    except Exception:
        output_text = "{}"

    # Best-effort extraction of sources from the response object
    try:
        if not use_http_fallback:
            resp_dict = resp.model_dump() if hasattr(resp, "model_dump") else json.loads(resp.model_dump_json())
        else:
            resp_dict = resp if isinstance(resp, dict) else {}
    except Exception:
        resp_dict = {}
    sources = _collect_source_urls(resp_dict)

    # Parse JSON content from the model
    try:
        data = json.loads(output_text)
        if isinstance(data, dict):
            data["sources"] = sources or data.get("sources", [])
            return data
        return {"raw_text": output_text, "sources": sources}
    except Exception:
        return {"raw_text": output_text, "sources": sources}


if __name__ == "__main__":
    result = get_realtime_finance(query="US CPI and big tech earnings", hours=24, limit=15)
    print(json.dumps(result, indent=2, ensure_ascii=False))


