"""
New York Times Archive — Minimal CLI

Usage:
  python app.py archive --year 2025 --month 9

Behavior:
  - Performs the Archive request and prints the response JSON, pretty-formatted.
  - No filtering is applied; the output is the raw Archive payload.
"""

import argparse
import json
import os
import sys
import requests
from dotenv import load_dotenv
from nyt_openai import run_nyt_openai_pipeline, _trim_archive_payload
from realtime import get_realtime_finance

# Load environment variables early so CLI sees them
load_dotenv()

NYT_API_KEY = os.getenv("NYT_API_KEY")
NYT_ARCHIVE_URL_TMPL = "https://api.nytimes.com/svc/archive/v1/{year}/{month}.json"
NYT_ARTICLE_SEARCH_URL = "https://api.nytimes.com/svc/search/v2/articlesearch.json"  # unused; kept for reference only


def _safe_text(resp):
    try:
        return resp.text
    except Exception:
        return "<no text>"


def _remove_key_recursive(obj, key_to_remove):
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


def _print_archive_result(year: int, month: int, custom_search: str | None = None):
    if not NYT_API_KEY:
        print("NYT_API_KEY is not set. Export it or add to .env", file=sys.stderr)
        sys.exit(1)

    url = NYT_ARCHIVE_URL_TMPL.format(year=year, month=month)
    params = {"api-key": NYT_API_KEY}
    resp = requests.get(url, params=params)
    # Log only meta.hits using already-filtered items for visibility
    try:
        data = resp.json()
        # Apply same trimming rules used for OpenAI pipeline before counting
        data = _remove_key_recursive(data, "multimedia")
        data = _trim_archive_payload(data)
        response = (data.get("response") or {}) if isinstance(data, dict) else {}
        docs = response.get("docs", [])
        hits = len(docs) if isinstance(docs, list) else None
        if hits is not None:
            print(f"meta: {{\"hits\": {hits}}}")
        else:
            print("meta: {}")
        # Log total character length of the trimmed NYT items (docs array)
        try:
            payload_chars = len(json.dumps(docs, ensure_ascii=False))
            print(f"len_chars: {payload_chars}")
        except Exception:
            pass
        # Also log the trimmed NYT JSON payload
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception:
        print("meta: {}")

    # Run OpenAI pipeline and print the combined JSON result
    result = run_nyt_openai_pipeline(year=year, month=month, custom_search=custom_search)
    print(json.dumps(result, indent=2, ensure_ascii=False))


#def _print_realtime(query: str | None, hours: int, limit: int):
#    res = get_realtime_finance(existing_feed=[], query=query, hours=hours, limit=limit)
#   print(json.dumps(res, indent=2, ensure_ascii=False))


def main(argv=None):
    parser = argparse.ArgumentParser(description="NYT Archive minimal CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_arch = sub.add_parser("archive", help="Fetch archive and run OpenAI pipeline")
    p_arch.add_argument("--year", type=int, required=True)
    p_arch.add_argument("--month", type=int, required=True)
    p_arch.add_argument("--custom_search", type=str, default=None, help="Focus on topics matching this string")
    # no limit here; we print the raw payload

#    p_rt = sub.add_parser("realtime", help="Fetch last-24h finance news via web search")
#    p_rt.add_argument("--query", type=str, default=None, help="Focus string for realtime search")
#    p_rt.add_argument("--hours", type=int, default=24)
#    p_rt.add_argument("--limit", type=int, default=20)

    args = parser.parse_args(argv)

    if args.cmd == "archive":
        _print_archive_result(args.year, args.month, args.custom_search)
        return 0
#    if args.cmd == "realtime":
#        _print_realtime(args.query, args.hours, args.limit)
#        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
