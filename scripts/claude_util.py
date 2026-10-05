"""AI helper used by the blog writer, the MCA/CBIC finder and the summariser.

Works with either provider – whichever key is set as a GitHub secret:
  GEMINI_API_KEY     Google Gemini (free tier, no billing needed; uses Google Search grounding)
  ANTHROPIC_API_KEY  Anthropic Claude (paid; web search restricted to official domains)
If both are set, Gemini is used unless AI_PROVIDER=anthropic.
"""
import json, os, re, time

import requests

DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-5"   # override with repository variable CLAUDE_MODEL
GEMINI_FALLBACKS = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-flash-lite-latest",
                    "gemini-flash-latest"]  # free-tier models, tried in order


def provider():
    pref = (os.environ.get("AI_PROVIDER") or "").lower()
    if pref == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None


def has_key():
    return provider() is not None


def _parse_json(text):
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
    starts = [i for i in (text.find("["), text.find("{")) if i >= 0]
    end = max(text.rfind("]"), text.rfind("}"))
    if not starts or end < 0:
        raise ValueError("No JSON in model reply")
    return json.loads(text[min(starts):end + 1])


def _retry_delay(r, default):
    """Seconds Google asks us to wait (RetryInfo), else the default."""
    try:
        for d in r.json()["error"].get("details", []):
            if "retryDelay" in d:
                return min(90, int(float(d["retryDelay"].rstrip("s"))) + 2)
    except Exception:
        pass
    return default


def _quota_ids(r):
    """Names of the quotas Google says were exceeded, e.g. GenerateRequestsPerDayPerProjectPerModel-FreeTier."""
    try:
        return [v.get("quotaId", "") for d in r.json()["error"].get("details", []) for v in d.get("violations", [])]
    except Exception:
        return []


def _gemini(prompt, allowed_domains, max_tokens):
    if allowed_domains:
        prompt += ("\n\nUse Google Search. Rely only on pages from these official websites: "
                   + ", ".join(allowed_domains) + ". Ignore all other websites.")
    models = [m for m in [os.environ.get("GEMINI_MODEL")] if m] + GEMINI_FALLBACKS
    models = list(dict.fromkeys(models))
    errors = []
    i = 0
    while i < len(models):
        model = models[i]
        i += 1
        gen = {"maxOutputTokens": max_tokens, "temperature": 0.3}
        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "tools": [{"google_search": {}}], "generationConfig": gen}
        for attempt in range(3):
            try:
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    params={"key": os.environ["GEMINI_API_KEY"]}, json=body, timeout=240)
            except requests.RequestException as e:
                errors.append(f"{model}: {e.__class__.__name__}")
                time.sleep(10)
                continue
            if r.status_code == 429:
                quotas = _quota_ids(r)
                errors.append(f"{model}: 429 quota exceeded {quotas}")
                print(f"  Gemini {model}: rate limited (attempt {attempt + 1}) {quotas}", flush=True)
                if any("PerDay" in q for q in quotas) or attempt == 1:
                    break                      # daily quota used up (or still limited): try the next model
                time.sleep(_retry_delay(r, 20 * (attempt + 1)))
                continue
            if r.status_code in (400, 403, 404):  # model not available on this key: try the next one
                errors.append(f"{model}: {r.status_code} {r.text[:200]}")
                print(f"  Gemini {model}: not available ({r.status_code})", flush=True)
                for newer in re.findall(r"models/([a-z0-9.\-]+)", r.text):   # Google names the replacement model
                    if newer != model and newer not in models:
                        models.append(newer)
                break
            if r.status_code >= 500:
                errors.append(f"{model}: {r.status_code}")
                time.sleep(15)
                continue
            r.raise_for_status()
            cand = (r.json().get("candidates") or [{}])[0]
            text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
            time.sleep(7)                      # stay under the free-tier requests-per-minute limit
            if text.strip():
                return text
            errors.append(f"{model}: empty reply ({cand.get('finishReason')})")
            break
    for e in errors:
        print("  " + e[:300], flush=True)
    raise RuntimeError("Gemini unavailable: " + (errors[-1][:200] if errors else "no models"))


def _anthropic(prompt, allowed_domains, max_searches, max_tokens):
    import anthropic
    tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": max_searches,
              **({"allowed_domains": allowed_domains} if allowed_domains else {})}]
    resp = anthropic.Anthropic().messages.create(
        model=os.environ.get("CLAUDE_MODEL") or DEFAULT_CLAUDE_MODEL,
        max_tokens=max_tokens, tools=tools,
        messages=[{"role": "user", "content": prompt}])
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def ask_text(prompt, allowed_domains=None, max_searches=5, max_tokens=8000):
    """Ask the configured model (with web search) and return the plain-text reply."""
    p = provider()
    if p == "gemini":
        return _gemini(prompt, allowed_domains, max_tokens)
    if p == "anthropic":
        return _anthropic(prompt, allowed_domains, max_searches, max_tokens)
    raise RuntimeError("No AI key set (GEMINI_API_KEY or ANTHROPIC_API_KEY)")


def ask_json(prompt, allowed_domains=None, max_searches=5, max_tokens=8000):
    """Ask the configured model (with web search) and parse a JSON reply."""
    p = provider()
    if p == "gemini":
        return _parse_json(_gemini(prompt, allowed_domains, max_tokens))
    if p == "anthropic":
        return _parse_json(_anthropic(prompt, allowed_domains, max_searches, max_tokens))
    raise RuntimeError("No AI key set (GEMINI_API_KEY or ANTHROPIC_API_KEY)")
