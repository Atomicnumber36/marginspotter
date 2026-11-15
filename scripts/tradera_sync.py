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

def image_urls(item):
    """Prioritize detailed listing photos instead of tiny search thumbnails."""
    sources = [
        pick(item, "detailedImageLinks", "DetailedImageLinks", "imageLinks", "ImageLinks",
             "images", "Images", "imageUrls", "ImageUrls", "pictures", "Pictures"),
        pick(item, "primaryImageUrl", "PrimaryImageUrl", "imageUrl", "ImageUrl"),
        pick(item, "thumbnailLink", "ThumbnailLink", "thumbnailUrl", "ThumbnailUrl"),
    ]
    found = []
    for source in sources:
        for candidate in (source if isinstance(source, list) else [source]):
            if isinstance(candidate, dict):
                candidate = pick(candidate, "originalUrl", "OriginalUrl", "largeUrl", "LargeUrl",
                                 "imageUrl", "ImageUrl", "url", "Url", "link", "imageLink", "src",
                                 "thumbnailLink", "ThumbnailLink")
            if isinstance(candidate, str) and candidate.startswith("https://"):
                host = urllib.parse.urlparse(candidate).hostname or ""
                if (host == "tradera.com" or host.endswith(".tradera.com") or
                    host.endswith(".tradera.net")) and candidate not in found:
                    found.append(candidate)
    def quality(url):
        path = urllib.parse.urlparse(url).path.lower()
        if "/images/" in path or "/original/" in path or "/large/" in path:
            return 0
        if "/medium/" in path:
            return 1
        if "/thumbs/" in path or "/minithumb/" in path:
            return 3
        return 2
    # The API may provide multiple resolutions of the same photo.
    # Never display low-resolution thumbnail variants when a larger one exists.
    best = {}
    for url in found:
        parsed = urllib.parse.urlparse(url)
        basename = parsed.path.rsplit("/", 1)[-1]
        if basename not in best or quality(url) < quality(best[basename]):
            best[basename] = url
    return sorted(best.values(), key=quality)[:12]

def image_url(item):
    photos = image_urls(item)
    return photos[0] if photos else None

def flag(item, *names):
    value = pick(item, *names)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str) and value.lower() in ("true", "false"):
        return value.lower() == "true"
    return None

def amount(value):
    if isinstance(value, dict):
        value = pick(value, "amount", "value", "Amount", "Value")
    try:
        return float(value) if value is not None else None
    except (ValueError, TypeError):
        return None

def listing_type(item):
    """Classify only from explicit Tradera API fields; never infer offers from price."""
    raw_type = pick(item, "itemType", "ItemType", "listingType", "ListingType", "auctionType", "AuctionType")
    type_text = str(raw_type).lower() if isinstance(raw_type, str) else ""
    type_code = int(raw_type) if isinstance(raw_type, (int, float)) and raw_type in (1, 3) else None
    buy = amount(pick(item, "buyItNowPrice", "BuyItNowPrice", "buyNowPrice", "BuyNowPrice"))
    bid = amount(pick(item, "maxBid", "MaxBid", "currentBid", "CurrentBid"))
    next_bid = amount(pick(item, "nextBid", "NextBid"))
    start_price = amount(pick(item, "openingBid", "OpeningBid", "startPrice", "StartPrice", "openingPrice", "OpeningPrice"))
    bid_count = amount(pick(item, "bidCount", "BidCount", "numberOfBids", "NumberOfBids", "totalBids", "TotalBids"))
    buy_flag = flag(item, "isBuyItNow", "IsBuyItNow", "buyItNow", "BuyItNow")
    auction_flag = flag(item, "isAuction", "IsAuction")
    offer_flag = flag(item, "acceptsOffers", "AcceptsOffers", "allowOffers", "AllowOffers", "isMakeOfferEnabled", "IsMakeOfferEnabled", "canMakeOffer", "CanMakeOffer", "isPriceSuggestionEnabled", "IsPriceSuggestionEnabled", "priceSuggestionEnabled", "PriceSuggestionEnabled", "allowPriceSuggestions", "AllowPriceSuggestions", "acceptPriceSuggestions", "AcceptPriceSuggestions", "canSuggestPrice", "CanSuggestPrice", "isNegotiable", "IsNegotiable")
    request_flag = flag(item, "canSendPurchaseRequest", "CanSendPurchaseRequest", "acceptsPurchaseRequests", "AcceptsPurchaseRequests", "canRequestPurchase", "CanRequestPurchase")
    ended_flag = flag(item, "isEnded", "IsEnded", "isClosed", "IsClosed", "hasEnded", "HasEnded")
    status = pick(item, "status", "Status", "itemStatus", "ItemStatus")
    if isinstance(status, dict):
        ended_flag = flag(status, "ended", "Ended") if ended_flag is None else ended_flag
    if isinstance(status, str) and status.lower() in ("ended", "closed", "expired", "finished", "sold"):
        ended_flag = True
    if type_code == 1 or "auction" in type_text or "auktion" in type_text:
        auction_flag = True
    if type_code == 3 or "buy" in type_text or "fixed" in type_text or "köp" in type_text:
        buy_flag = True
    # A suggested/negotiable price is a strong fixed-price signal only when
    # no explicit auction evidence is present. Never inspect seller-written titles.
    suggested = amount(pick(item, "suggestedPrice", "SuggestedPrice", "proposedPrice", "ProposedPrice", "offerPrice", "OfferPrice"))
    suggested_label = pick(item, "priceType", "PriceType", "priceLabel", "PriceLabel", "purchaseType", "PurchaseType")
    has_suggested_label = isinstance(suggested_label, str) and any(
        term in suggested_label.lower() for term in ("föreslå pris", "föreslaget pris", "foresla pris", "suggested price", "make offer"))
    auction_evidence = auction_flag is True or bid is not None or next_bid is not None or start_price is not None or (bid_count is not None and bid_count > 0)
    if suggested is not None or has_suggested_label:
        if offer_flag is None:
            offer_flag = True
        if not auction_evidence:
            buy_flag = True
    if type_code == 3:
        kind = "buy_now"
    elif type_code == 1:
        kind = "auction_buy_now" if buy is not None and buy > 0 else "auction"
    elif buy_flag is True and auction_flag is not True:
        kind = "buy_now"
    elif auction_flag is True and buy_flag is not True:
        kind = "auction"
    elif buy is not None and bid is None:
        kind = "buy_now"
    elif (bid is not None or next_bid is not None or start_price is not None or (bid_count is not None and bid_count > 0)) and buy is None:
        kind = "auction"
    elif buy is not None and (bid is not None or next_bid is not None or start_price is not None or (bid_count is not None and bid_count > 0)):
        kind = "auction_buy_now"
    else:
        kind = "unknown"
    if ended_flag is True:
        kind = "ended"
    return kind, offer_flag, request_flag, buy, bid, next_bid, start_price, bid_count

def condition_signals(description):
    """Conservative Swedish/Danish text signals; not a visual or AI inspection."""
    import re
    text = (description or "").lower()
    if not text:
        return {"grade": "unknown", "label": "Ikke vurderet", "confidence": "low", "signals": [], "source": "description"}
    patterns = [
        ("defect", r"\\b(?:defekt|trasig|fungerar inte|fungerer ikke|ej fungerande|reservdel|skadad|sprucken|broken|not working|does not work)\\b", "Mulig fejl eller skade"),
        ("untested", r"\\b(?:otestad|ej testad|inte testad|okänd funktion|utestet|ikke testet|untested)\\b", "Ikke funktionstestet"),
        ("wear", r"\\b(?:repor|repad|slitage|sliten|ridser|slid|gulnad|gulnet|buckla|bulor|skav|scratches)\\b", "Kosmetisk slid omtalt"),
        ("positive", r"\\b(?:fungerar fint|fungerar bra|fullt fungerande|fungerer perfekt|testad och fungerar|tested working)\\b", "Sælger oplyser, at varen fungerer"),
        ("complete", r"\\b(?:komplett|complete in box|\\bcib\\b|originalkartong|original box|original æske)\\b", "Komplethed eller original æske omtalt"),
    ]
    signals = [{"type": kind, "text": label} for kind, pattern, label in patterns if re.search(pattern, text)]
    kinds = {x["type"] for x in signals}
    if "defect" in kinds:
        grade, label = "risk", "Mulig defekt"
    elif "untested" in kinds:
        grade, label = "untested", "Utestet"
    elif "wear" in kinds:
        grade, label = "wear", "Slid omtalt"
    elif "positive" in kinds:
        grade, label = "claimed_working", "Fungerer ifølge sælger"
    else:
        grade, label = "unknown", "Stand ukendt"
    return {"grade": grade, "label": label, "confidence": "low", "signals": signals, "source": "description"}


def description_text(item):
    value = pick(item, "description", "Description", "itemDescription", "ItemDescription",
                 "longDescription", "LongDescription")
    if isinstance(value, str):
        import re
        return re.sub(r"<[^>]+>", " ", value).strip()[:4000]
    return ""


def normalize(item, query):
    if not isinstance(item, dict):
        return None
    item_id = pick(item, "id", "itemId", "Id")
    title = pick(item, "title", "shortDescription", "name")
    if not item_id or not title:
        return None
    kind, offer_flag, request_flag, buy, bid, next_bid, start_price, bid_count = listing_type(item)
    end_date = pick(item, "endDate", "EndDate", "endsAt", "EndsAt", "endTime", "EndTime")
    if not isinstance(end_date, str):
        end_date = None
    if end_date:
        try:
            if dt.datetime.fromisoformat(end_date.replace("Z", "+00:00")) < dt.datetime.now(dt.timezone.utc):
                kind = "ended"
        except (ValueError, TypeError):
            pass
    price = buy if kind == "buy_now" else (bid if bid is not None else (next_bid if next_bid is not None else (start_price if start_price is not None else buy)))
    raw_url = pick(item, "itemUrl", "url", "link")
    url = raw_url if isinstance(raw_url, str) and raw_url.startswith("https://www.tradera.com/") else "https://www.tradera.com/item/" + str(item_id)
    return {"id": str(item_id), "query": query, "title": str(title), "url": url,
            "price": price, "currency": "SEK", "shipping": None,
            "pricingStatus": "unverified", "source": "Tradera",
            "imageUrl": image_url(item), "imageUrls": image_urls(item), "description": description_text(item), "condition": condition_signals(description_text(item)), "listingType": kind, "offersAllowed": offer_flag, "purchaseRequestAllowed": request_flag, "buyNowPrice": buy, "currentBid": bid, "nextBid": next_bid, "startPrice": start_price, "bidCount": bid_count, "endDate": end_date}

def enrich(listings, headers):
    """Read-only detail lookup for uncertain items, with a 12-hour local cache."""
    previous = {}
    if OUTPUT.exists():
        try:
            previous = {str(x["id"]): x for x in json.loads(OUTPUT.read_text(encoding="utf-8")).get("listings", [])}
        except (ValueError, KeyError, TypeError):
            pass
    now = dt.datetime.now(dt.timezone.utc)
    pending = []
    keys = ("imageUrl", "imageUrls", "description", "condition", "listingType", "offersAllowed", "purchaseRequestAllowed", "buyNowPrice", "currentBid", "nextBid", "startPrice", "bidCount", "endDate")
    for item in listings.values():
        old = previous.get(item["id"], {})
        checked = old.get("detailCheckedAt")
        recent = False
        if checked:
            try:
                recent = (now - dt.datetime.fromisoformat(checked.replace("Z", "+00:00"))).total_seconds() < 12 * 3600
            except (ValueError, TypeError):
                pass
        # A recent detail check must not suppress a retry when the gallery is incomplete.
        # Search results commonly include only the cover image.
        if recent and len(old.get("imageUrls") or []) >= 2:
            for key in keys:
                if item.get(key) is None or (key == "imageUrls" and not item.get(key)) or (key == "description" and not item.get(key)) or (key == "listingType" and item[key] == "unknown"):
                    if old.get(key) is not None:
                        item[key] = old[key]
            item["detailCheckedAt"] = checked
        elif (len(item.get("imageUrls") or []) < 2 or item.get("offersAllowed") is None
              or not item.get("description") or item["listingType"] == "unknown"):
            pending.append(item)
    # Prioritize incomplete galleries: search results often contain only a cover photo.
    pending.sort(key=lambda item: (len(item.get("imageUrls") or []) >= 2, bool(item.get("description"))))
    for item in pending[:40]:
        request = urllib.request.Request(
            "https://api.tradera.com/v4/items/" + urllib.parse.quote(item["id"], safe=""),
            headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                detail = json.load(response)
            if not isinstance(detail, dict):
                continue
            detail = pick(detail, "item", "Item") or detail
            if not isinstance(detail, dict):
                continue
            enriched = normalize({**detail, "id": item["id"], "title": item["title"], "itemUrl": item["url"]}, item["query"])
            if enriched:
                for key in keys:
                    if enriched.get(key) is not None and (key != "listingType" or enriched[key] != "unknown"):
                        item[key] = enriched[key]
                if enriched.get("price") is not None:
                    item["price"] = enriched["price"]
                if enriched.get("imageUrls"):
                    item["imageUrls"] = enriched["imageUrls"]
                    item["imageUrl"] = enriched["imageUrls"][0]
                if item.get("description"):
                    item["condition"] = condition_signals(item["description"])
                item["detailCheckedAt"] = now.isoformat()
        except (urllib.error.URLError, ValueError, TimeoutError):
            continue


def translate_descriptions(listings, previous):
    """Offline translation with Argos Translate. Preserve seller originals."""
    pending = []
    for item in listings.values():
        original = item.get("description") or ""
        old = previous.get(item["id"], {})
        if not original:
            continue
        if old.get("description") == original and old.get("descriptionDa"):
            item["descriptionDa"] = old["descriptionDa"]
        else:
            pending.append(item)
    if not pending:
        return
    try:
        from argostranslate import translate
        languages = {lang.code: lang for lang in translate.get_installed_languages()}
        danish = languages.get("da")
        if danish is None:
            raise RuntimeError("Danish translation model unavailable")
        for item in pending:
            original = item["description"]
            # Tradera descriptions are predominantly Swedish; prefer Swedish
            # unless a simple English-language signal is present.
            english_markers = ("the ", "this ", "with ", "condition", "shipping", "working", "game is ")
            source = "en" if sum(marker in (" " + original.lower() + " ") for marker in english_markers) >= 2 else "sv"
            language = languages.get(source)
            if language is None:
                continue
            try:
                translated = language.get_translation(danish).translate(original)
                if isinstance(translated, str) and translated.strip():
                    item["descriptionDa"] = translated.strip()
            except (ValueError, RuntimeError, AttributeError):
                continue
    except (ImportError, RuntimeError) as error:
        print("Offline translation unavailable:", str(error))
    print("Danish descriptions:", sum(bool(x.get("descriptionDa")) for x in listings.values()))

def main():
    app_id, app_key = os.getenv("TRADERA_APP_ID"), os.getenv("TRADERA_APP_KEY")
    if not app_id or not app_key:
        sys.exit("Missing TRADERA_APP_ID / TRADERA_APP_KEY; existing feed unchanged")
    manual_query = os.getenv("TRADERA_TEST_QUERY", "").strip()
    watchlist = json.loads(WATCHLIST.read_text(encoding="utf-8"))
    configured = watchlist.get("queries", []) if isinstance(watchlist, dict) else None
    queries = [manual_query] if manual_query else configured
    if not isinstance(queries, list) or not all(isinstance(q, str) and 0 < len(q) <= 120 for q in queries):
        sys.exit("Invalid watchlist")
    if not queries:
        print("No configured watchlist queries; existing feed unchanged")
        return
    listings = {}
    # Fetch more than the first result page: newly listed bargains can otherwise
    # be missed when a popular search produces many results.
    for query in queries[:20]:
        for page in range(1, 4):
            url = BASE + "?" + urllib.parse.urlencode({"query": query, "pageNumber": page})
            request = urllib.request.Request(url, headers={"X-App-Id": app_id, "X-App-Key": app_key, "Accept": "application/json", "User-Agent": "MarginSpotter/0.1"})
            try:
                with urllib.request.urlopen(request, timeout=25) as response:
                    data = json.load(response)
            except urllib.error.HTTPError as error:
                # A later page failing should not erase listings already found.
                if page > 1:
                    print("Additional Tradera page failed:", query, page, error.code)
                    break
                sys.exit("Tradera search failed with HTTP " + str(error.code) + "; existing feed unchanged")
            if isinstance(data, dict) and data.get("errors"):
                if page > 1:
                    print("Additional Tradera page returned errors:", query, page)
                    break
                sys.exit("Tradera search returned API errors; existing feed unchanged: " + json.dumps(data["errors"], ensure_ascii=False)[:500])
            candidates = data if isinstance(data, list) else pick(data, "items", "results", "searchResults", "itemList")
            if isinstance(candidates, dict):
                candidates = pick(candidates, "items", "results")
            if not isinstance(candidates, list):
                if page > 1:
                    break
                sys.exit("Unexpected Tradera search response; existing feed unchanged")
            if not candidates:
                break
            for raw in candidates:
                listing = normalize(raw, query)
                if listing:
                    listings[listing["id"]] = listing
    enrich(listings, {"X-App-Id": app_id, "X-App-Key": app_key, "Accept": "application/json", "User-Agent": "MarginSpotter/0.1"})
    try:
        previous = {str(x["id"]): x for x in json.loads(OUTPUT.read_text(encoding="utf-8")).get("listings", [])} if OUTPUT.exists() else {}
    except (ValueError, KeyError, TypeError):
        previous = {}
    translate_descriptions(listings, previous)
    payload = {"updatedAt": dt.datetime.now(dt.timezone.utc).isoformat(), "status": "ok", "listings": list(listings.values())}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Normalized", len(listings), "read-only listings")

if __name__ == "__main__":
    main()
