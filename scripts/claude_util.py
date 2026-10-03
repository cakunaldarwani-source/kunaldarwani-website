"""AI helper used by the blog writer, the MCA/CBIC finder and the summariser.

Works with either provider – whichever key is set as a GitHub secret:
  GEMINI_API_KEY     Google Gemini (free tier, no billing needed; uses Google Search grounding)
  ANTHROPIC_API_KEY  Anthropic Claude (paid; web search restricted to official domains)
If both are set, Gemini is used unless AI_PROVIDER=anthropic.
"""
import json, os, re

import requests

DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-5"   # override with repository variable CLAUDE_MODEL
DEFAULT_GEMINI_MODEL = "gemini-flash-latest"  # override with repository variable GEMINI_MODEL


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


def _gemini(prompt, allowed_domains, max_tokens):
    model = os.environ.get("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
    if allowed_domains:
        prompt += ("\n\nUse Google Search. Rely only on pages from these official websites: "
                   + ", ".join(allowed_domains) + ". Ignore all other websites.")
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.3},
    }
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        params={"key": os.environ["GEMINI_API_KEY"]}, json=body, timeout=180)
    r.raise_for_status()
    parts = r.json()["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts)


def _anthropic(prompt, allowed_domains, max_searches, max_tokens):
    import anthropic
    tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": max_searches,
              **({"allowed_domains": allowed_domains} if allowed_domains else {})}]
    resp = anthropic.Anthropic().messages.create(
        model=os.environ.get("CLAUDE_MODEL") or DEFAULT_CLAUDE_MODEL,
        max_tokens=max_tokens, tools=tools,
        messages=[{"role": "user", "content": prompt}])
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def ask_json(prompt, allowed_domains=None, max_searches=5, max_tokens=8000):
    """Ask the configured model (with web search) and parse a JSON reply."""
    p = provider()
    if p == "gemini":
        return _parse_json(_gemini(prompt, allowed_domains, max_tokens))
    if p == "anthropic":
        return _parse_json(_anthropic(prompt, allowed_domains, max_searches, max_tokens))
    raise RuntimeError("No AI key set (GEMINI_API_KEY or ANTHROPIC_API_KEY)")
