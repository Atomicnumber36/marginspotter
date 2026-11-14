#!/usr/bin/env python3
"""Optional server-side AI condition screening. Never exposes API keys in the PWA."""
import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request

MODEL = os.getenv("OPENAI_CONDITION_MODEL", "gpt-4o-mini")
LIMIT = max(0, min(10, int(os.getenv("AI_CONDITION_LIMIT", "5"))))

def safe_image(url):
    if not isinstance(url, str) or not url.startswith("https://"):
        return None
    host = urllib.parse.urlparse(url).hostname or ""
    return url if host.endswith(".tradera.net") or host.endswith(".tradera.com") else None

def analyze(item, key):
    description = (item.get("description") or "")[:2500]
    photo = safe_image(item.get("imageUrl"))
    if not description and not photo:
        return None
    parts = [{"type": "text", "text": (
        "Assess this second-hand retro gaming listing. Distinguish seller claims from "
        "visually observable evidence. Do not assert functionality based on images. "
        "Do not invent missing accessories or defects. If insufficient evidence, say so. "
        "Return JSON with keys: label (short Danish condition label), summary (Danish, <=180 chars), "
        "risks (array of <=3 short Danish strings), confidence (low/medium/high), "
        "grade (unknown/good/worn/damaged/untested), evidence (seller_text/image/both). "
        "The confidence measures evidence quality, not whether seller claims are true. "
        "Title: " + str(item.get("title", ""))[:200] + "\\nSeller description: " + description
    )}]
    if photo:
        parts.append({"type": "image_url", "image_url": {"url": photo, "detail": "low"}})
    payload = {"model": MODEL, "temperature": 0, "response_format": {"type": "json_object"},
               "messages": [{"role": "user", "content": parts}], "max_tokens": 350}
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=35) as response:
        result = json.load(response)
    obj = json.loads(result["choices"][0]["message"]["content"])
    if not isinstance(obj, dict):
        return None
    grade = obj.get("grade") if obj.get("grade") in ("unknown", "good", "worn", "damaged", "untested") else "unknown"
    confidence = obj.get("confidence") if obj.get("confidence") in ("low", "medium", "high") else "low"
    risks = [str(x)[:120] for x in obj.get("risks", []) if isinstance(x, str)][:3] if isinstance(obj.get("risks"), list) else []
    return {"grade": grade, "label": str(obj.get("label") or "Stand ukendt")[:60],
            "summary": str(obj.get("summary") or "")[:250], "risks": risks,
            "confidence": confidence, "source": "ai",
            "evidence": obj.get("evidence") if obj.get("evidence") in ("seller_text", "image", "both") else "seller_text",
            "checkedAt": dt.datetime.now(dt.timezone.utc).isoformat()}

def apply_ai_condition(listings, previous):
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        print("AI condition disabled: configure OPENAI_API_KEY secret")
        return
    processed = 0
    for item in listings.values():
        old = previous.get(item["id"], {})
        old_ai = old.get("aiCondition")
        if isinstance(old_ai, dict) and old.get("description") == item.get("description") and old.get("imageUrl") == item.get("imageUrl"):
            checked = old_ai.get("checkedAt")
            try:
                if checked and (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(checked)).days < 7:
                    item["aiCondition"] = old_ai
                    continue
            except (ValueError, TypeError):
                pass
        if processed >= LIMIT:
            continue
        if not item.get("description") and not safe_image(item.get("imageUrl")):
            continue
        processed += 1
        try:
            result = analyze(item, key)
            if result:
                item["aiCondition"] = result
        except (urllib.error.URLError, ValueError, KeyError, TimeoutError) as error:
            print("AI condition unavailable for listing " + item["id"] + ": " + type(error).__name__)
    print("AI condition attempts:", processed)
