#!/usr/bin/env python3
"""Read-only Tradera search -> static JSON. No credentials are printed or committed."""
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
WATCHLIST = ROOT / "config/tradera-watchlist.json"
OUTPUT = ROOT / "data/tradera-listings.json"
BASE = "https://api.tradera.com/v4/search"

def pick(obj, *names):
    if not isinstance(obj, dict):
        return None
    for name in names:
        if obj.get(name) is not None:
            return obj[name]
    return None

def normalize(item, query):
    if not isinstance(item, dict):
        return None
    item_id = pick(item, "id", "itemId", "Id")
    title = pick(item, "title", "shortDescription", "name")
    if not item_id or not title:
        return None
    price = pick(item, "currentBid", "price", "buyItNowPrice")
    if isinstance(price, dict):
        price = pick(price, "amount", "value")
    try:
        price = float(price) if price is not None else None
    except (ValueError, TypeError):
        price = None
    raw_url = pick(item, "itemUrl", "url", "link")
    url = raw_url if isinstance(raw_url, str) and raw_url.startswith("https://www.tradera.com/") else "https://www.tradera.com/item/" + str(item_id)
    return {"id": str(item_id), "query": query, "title": str(title), "url": url,
            "price": price, "currency": "SEK", "shipping": None,
            "pricingStatus": "unverified", "source": "Tradera"}

def main():
    app_id, app_key = os.getenv("TRADERA_APP_ID"), os.getenv("TRADERA_APP_KEY")
    if not app_id or not app_key:
        sys.exit("Missing TRADERA_APP_ID / TRADERA_APP_KEY; existing feed unchanged")
    queries = json.loads(WATCHLIST.read_text(encoding="utf-8")).get("queries", [])
    if not isinstance(queries, list) or not all(isinstance(q, str) and 0 < len(q) <= 120 for q in queries):
        sys.exit("Invalid watchlist")
    if not queries:
        print("No shared search queries configured; existing feed unchanged")
        return
    listings = {}
    for query in queries[:20]:
        url = BASE + "?" + urllib.parse.urlencode({"query": query})
        request = urllib.request.Request(url, headers={"X-App-Id": app_id, "X-App-Key": app_key, "Accept": "application/json", "User-Agent": "MarginSpotter/0.1"})
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                data = json.load(response)
        except urllib.error.HTTPError as error:
            sys.exit("Tradera search failed with HTTP " + str(error.code) + "; existing feed unchanged")
        candidates = data if isinstance(data, list) else pick(data, "items", "results", "searchResults", "itemList")
        if isinstance(candidates, dict):
            candidates = pick(candidates, "items", "results")
        if not isinstance(candidates, list):
            sys.exit("Unexpected Tradera search response; existing feed unchanged")
        for raw in candidates:
            listing = normalize(raw, query)
            if listing:
                listings[listing["id"]] = listing
    payload = {"updatedAt": dt.datetime.now(dt.timezone.utc).isoformat(), "status": "ok", "listings": list(listings.values())}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Normalized", len(listings), "read-only listings")

if __name__ == "__main__":
    main()
