import re
from typing import Any, Optional

import requests


UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def sniff(html: str) -> dict[str, Any]:
    return {
        "len": len(html),
        "has___NEXT_DATA__": "__NEXT_DATA__" in html,
        "has___next_f": "__next_f" in html,
        "next_static_count": html.count("/_next/"),
    }


def extract_hrefs(html: str, limit: int = 60) -> list[str]:
    hrefs = re.findall(r'href="([^"]+)"', html)
    out: list[str] = []
    seen: set[str] = set()
    for h in hrefs:
        if h in seen:
            continue
        seen.add(h)
        out.append(h)
        if len(out) >= limit:
            break
    return out


def extract_candidate_emoji_pages(html: str, limit: int = 30) -> list[str]:
    """
    Heuristic: emoji pages are often like /fox/ or /red-heart/ etc.
    We exclude obvious non-emoji routes.
    """
    hrefs = extract_hrefs(html, limit=5000)
    candidates: list[str] = []
    seen: set[str] = set()
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-/_")
    for h in hrefs:
        if not (h.startswith("/") and h.endswith("/")):
            continue
        if h.startswith(("/search/", "/keyboard/", "/emojis/", "/categories/", "/blog/", "/about/", "/unicode/")):
            continue
        if h in ("/",):
            continue
        if any((c.lower() not in allowed) for c in h):
            continue
        if h in seen:
            continue
        seen.add(h)
        candidates.append(h)
        if len(candidates) >= limit:
            break
    return candidates


def fetch(url: str) -> str:
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    return r.text


def summarize(url: str) -> None:
    html = fetch(url)
    print("URL:", url)
    print("sniff:", sniff(html))
    print("candidates:", extract_candidate_emoji_pages(html))
    # show where app data might be embedded
    for marker in ["__NEXT_DATA__", "__next_f", "buildId", "pageProps"]:
        idx = html.find(marker)
        print(f"marker {marker} idx:", idx if idx >= 0 else None)
        if idx >= 0:
            print("context:", html[max(0, idx - 120) : idx + 240].replace("\n", "")[:360])
    print()


def main() -> None:
    summarize("https://emojipedia.org/search/?q=fox")
    summarize("https://emojipedia.org/fox/")


if __name__ == "__main__":
    main()

