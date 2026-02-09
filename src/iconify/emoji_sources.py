from __future__ import annotations

import html as htmllib
import io
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import quote_plus, urljoin
from urllib.parse import unquote

import requests
from PIL import Image

from .core import IconSource


UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


@lru_cache(maxsize=1)
def fetch_unicode_emoji_metadata() -> dict[str, str]:
    """
    Returns mapping of friendly_name -> hex codepoint string (no 'U+').
    Also includes code->code mapping for direct usage.
    """
    unicode_url = "https://unicode.org/Public/emoji/latest/emoji-test.txt"
    try:
        response = requests.get(unicode_url, timeout=20, headers=UA)
        response.raise_for_status()
        emoji_data: dict[str, str] = {}
        for line in response.text.splitlines():
            if "; fully-qualified" in line:
                code = line.split(";")[0].strip().lower().replace(" ", "")
                # fragment: "# <emoji> <version> <name...>"
                after_hash = line.split("#", 1)[1].strip()
                parts = after_hash.split()
                name_words = parts[2:] if len(parts) >= 3 else []
                if name_words:
                    first = name_words[0].strip().lower()
                    underscored = "_".join(w.strip().lower() for w in name_words)
                    emoji_data[first] = code
                    emoji_data[underscored] = code
                else:
                    emoji_data[code] = code
                emoji_data[code] = code
        return emoji_data
    except Exception:
        fallback = {
            "fox": "1f98a",
            "lotus": "1fab7",
            "paw_prints": "1f43e",
            "dragon": "1f409",
            "wolf": "1f43a",
            "cat": "1f431",
            "dog": "1f436",
            "unicorn": "1f984",
            "phoenix": "1f985",
            "butterfly": "1f98b",
            "rose": "1f339",
        }
        return {**fallback, **{v: v for v in fallback.values()}}


def twemoji_svg_url(emoji_code: str) -> str:
    code = emoji_code.lower().replace("u+", "").replace("0x", "").replace(" ", "")
    return f"https://raw.githubusercontent.com/twitter/twemoji/master/assets/svg/{code}.svg"


def parse_emoji_argument(arg: str) -> str:
    """
    Accepts:
    - Friendly name ('fox')
    - Codepoint hex ('1f98a')
    - 'U+1F98A'
    - A literal emoji char (best-effort, single codepoint)
    Returns the hex code string used by Twemoji assets.
    """
    s = (arg or "").strip().lower()
    meta = fetch_unicode_emoji_metadata()
    if s in meta:
        return meta[s]
    s = s.replace("u+", "").replace("0x", "")
    if re.fullmatch(r"[0-9a-f]{4,6}(-[0-9a-f]{4,6})*", s):
        return s
    # best-effort: treat as emoji char
    if len(arg) >= 1:
        cp = "-".join(f"{ord(ch):x}" for ch in arg)
        return cp
    raise ValueError(f"Could not parse emoji: {arg}")


@dataclass(frozen=True)
class EmojipediaResult:
    title: str
    path: str  # e.g. "/fox" or "/fox/"

    @property
    def url(self) -> str:
        return urljoin("https://emojipedia.org", self.path)


def _fetch_html(url: str) -> str:
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    return r.text


def _emojipedia_graphql(operation_name: str, query: str, variables: dict) -> dict:
    """
    Call Emojipedia's GraphQL endpoint.

    Notes:
    - Endpoint requires operationName.
    - Some clients send extra headers (x-query-hash, x-client). These appear optional for basic usage.
    """
    r = requests.post(
        "https://emojipedia.org/api/graphql",
        headers={**UA, "content-type": "application/json"},
        data=json.dumps({"operationName": operation_name, "query": query, "variables": variables}),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def emojipedia_extract_emoji_code_from_page_html(html: str) -> Optional[str]:
    """
    Best-effort: extract the emoji character from og:title or <title> and return its codepoint(s)
    as lowercase hex joined with '-' (Twemoji style).
    Example: '🪷 Lotus' -> '1fab7'
    """
    # Prefer og:title, then title tag
    m = re.search(r'property="og:title" content="([^"]+)"', html)
    if not m:
        m = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    text = htmllib.unescape(m.group(1)).strip()

    # Pick the first non-ascii glyph(s) that look like emoji.
    # This is heuristic but works for most Emojipedia titles which start with the emoji.
    chars = [ch for ch in text if ord(ch) > 127]
    if not chars:
        return None
    # Many emoji are a single glyph; keep first 4 codepoints max to avoid garbage.
    emoji_chars = chars[:4]
    return "-".join(f"{ord(ch):x}" for ch in emoji_chars)


@dataclass(frozen=True)
class EmojipediaDesign:
    vendor_title: str
    item_title: str
    source_path: str  # e.g. "source/apple/419/lotus_1fab7.png"

    @property
    def source_url(self) -> str:
        return urljoin("https://em-content.zobj.net/", self.source_path.lstrip("/"))


def emojipedia_list_designs(emoji_slug: str, *, lang: str = "EN") -> list[EmojipediaDesign]:
    """
    List vendor designs for a given emoji slug (e.g. 'lotus').
    Uses Emojipedia's GraphQL API to retrieve the same data shown under #designs.
    """
    q = """
    query emojiV1($slug: Slug!, $lang: Language) {
      emoji_v1(slug: $slug, lang: $lang) {
        vendorsAndPlatforms {
          slug
          title
          items {
            date
            slug
            title
            image {
              source
              description
              useOriginalImage
            }
          }
        }
      }
    }
    """
    data = _emojipedia_graphql("emojiV1", q, {"slug": emoji_slug, "lang": lang})
    ev = (data.get("data") or {}).get("emoji_v1") or {}
    vps = ev.get("vendorsAndPlatforms") or []

    designs: list[EmojipediaDesign] = []
    for vp in vps:
        vendor_title = vp.get("title") or vp.get("slug") or "Vendor"
        items = vp.get("items") or []
        for it in items:
            img = it.get("image") or {}
            src = img.get("source")
            if not src:
                continue
            designs.append(
                EmojipediaDesign(
                    vendor_title=str(vendor_title),
                    item_title=str(it.get("title") or it.get("slug") or ""),
                    source_path=str(src),
                )
            )
    return designs


def _extract_next_f_payloads(html: str) -> str:
    """
    Emojipedia uses Next.js app router (RSC) which embeds payload chunks in:
      self.__next_f.push([1,"..."])
    We concatenate all chunk strings for simple regex scraping.
    """
    # Correctly match literal dots in "self.__next_f"
    # Emojipedia may push multiple payload types; collect all string chunks.
    chunks = re.findall(r'self\.__next_f\.push\(\[\d+,"(.*?)"\]\)', html, flags=re.DOTALL)
    if not chunks:
        chunks = re.findall(r'__next_f\.push\(\[\d+,"(.*?)"\]\)', html, flags=re.DOTALL)

    out: list[str] = []
    for ch in chunks:
        # Best-effort unescape as a JSON string (handles \n, \", \u003c, etc.)
        try:
            out.append(json.loads(f"\"{ch}\""))
        except Exception:
            out.append(ch.replace("\\n", "\n").replace("\\\"", "\"").replace("\\/", "/"))
    return "".join(out)


def _slug_title(path: str) -> str:
    slug = path.strip("/").split("/", 1)[0]
    return slug.replace("-", " ").title()


def _html_search_results(html: str, query: str, limit: int) -> list[EmojipediaResult]:
    hrefs = re.findall(r'href="([^"]+)"', html)
    candidates: list[EmojipediaResult] = []
    seen: set[str] = set()
    q = (query or "").strip().lower().replace(" ", "-")
    category_slugs = {
        "smileys",
        "people",
        "nature",
        "food-drink",
        "activity",
        "travel-places",
        "objects",
        "symbols",
        "flags",
    }
    for h in hrefs:
        if not h.startswith("/"):
            continue
        # normalize (drop querystring/fragment)
        h = h.split("?", 1)[0].split("#", 1)[0]
        if h in ("/", ""):
            continue
        if h.startswith(("/search", "/stickers", "/emoji", "/faq", "/emojis", "/categories", "/blog", "/about", "/unicode")):
            continue
        if not re.fullmatch(r"/[a-z0-9\-]+/?", h):
            continue
        if h in seen:
            continue
        seen.add(h)
        candidates.append(EmojipediaResult(title=_slug_title(h), path=h))

    def score(r: EmojipediaResult) -> int:
        slug = r.path.strip("/").lower()
        if slug in category_slugs:
            return -1000
        if not q:
            return 0
        if slug == q:
            return 1000
        if slug.startswith(q):
            return 900
        if q in slug:
            return 800
        return 0

    candidates.sort(key=score, reverse=True)
    return candidates[:limit]


def emojipedia_search(query: str, limit: int = 10) -> list[EmojipediaResult]:
    """
    Heuristic search: scrape RSC payload for emoji-page hrefs and nearby titles.
    Falls back to scanning for /<slug>/ patterns.
    """
    url = f"https://emojipedia.org/search/?q={quote_plus(query)}"
    html = _fetch_html(url)
    # First: HTML hrefs (stable and fast)
    html_results = _html_search_results(html, query=query, limit=limit)
    if html_results:
        return html_results

    payload = _extract_next_f_payloads(html)

    # Strategy 1: href + aria-label/title near it
    results: list[EmojipediaResult] = []
    seen: set[str] = set()

    # Commonly the payload includes fragments like: href:"/fox/" ... title:"Fox" ...
    for m in re.finditer(r'href:\"(/[^\"\\s]+/?)(?:\\\"|\" )', payload):
        path = m.group(1)
        if path.startswith(("/search/", "/emoji/", "/faq/", "/emojis/", "/categories/", "/blog/")):
            continue
        if not re.fullmatch(r"/[a-z0-9\\-]+/?", path):
            continue
        if path in seen:
            continue
        seen.add(path)
        # try to find a nearby label
        window = payload[m.start() : m.start() + 400]
        title_m = re.search(r'(?:title|aria-label):\"([^\"]{1,80})\"', window)
        title = htmllib.unescape(title_m.group(1)) if title_m else _slug_title(path)
        results.append(EmojipediaResult(title=title, path=path))
        if len(results) >= limit:
            break

    if results:
        return results

    # Strategy 2: brute force paths in payload
    for path in re.findall(r"(/[a-z0-9\\-]+/?)", payload):
        if path.startswith(("/search/", "/emoji/", "/faq/", "/emojis/", "/categories/", "/blog/")):
            continue
        if path in seen:
            continue
        seen.add(path)
        results.append(EmojipediaResult(title=_slug_title(path), path=path))
        if len(results) >= limit:
            break
    return results


def _score_image_size_from_bytes(data: bytes) -> int:
    try:
        with Image.open(io.BytesIO(data)) as img:
            w, h = img.size
            return int(w * h)
    except Exception:
        return 0


def emojipedia_best_artwork_url(emoji_page_url: str, max_candidates: int = 25) -> Optional[str]:
    """
    Extract candidate image URLs from emoji page payload and pick the largest raster by probing sizes.
    Prefers SVG if available.
    """
    html = _fetch_html(emoji_page_url)
    payload = _extract_next_f_payloads(html)

    # Meta tags are stable and often include a decent-size preview (social card).
    meta_urls: list[str] = []
    for key in ("og:image", "twitter:image", "twitter:image:src"):
        m = re.search(rf'property="{re.escape(key)}" content="([^"]+)"', html)
        if not m:
            m = re.search(rf'name="{re.escape(key)}" content="([^"]+)"', html)
        if m:
            meta_urls.append(m.group(1))

    # Try to find any direct source assets in HTML as well.
    html_asset_urls = sorted(
        set(re.findall(r"https://em-content\\.zobj\\.net/[^\\s\\\"'>]+\\.(?:png|webp|svg)", html, flags=re.I))
    )

    # Next.js often wraps external images as /_next/image?url=<encoded>&w=<width>
    next_image_urls: list[str] = []
    for m in re.finditer(r"/_next/image\\?url=([^&\\\"]+)", payload):
        raw = m.group(1)
        decoded = unquote(raw)
        if decoded.startswith("http://") or decoded.startswith("https://"):
            next_image_urls.append(decoded)
        elif decoded.startswith("/"):
            next_image_urls.append(urljoin("https://emojipedia.org", decoded))

    svg_urls = sorted(set(re.findall(r"https://[^\\s\\\"]+?\\.svg", payload)))
    svg_urls = sorted(set(svg_urls + [u for u in html_asset_urls if u.lower().endswith(".svg")]))
    # Prefer SVGs from known hosts (vector renders well)
    for u in svg_urls:
        if "zobj.net" in u or "emojipedia" in u:
            return u
    if svg_urls:
        return svg_urls[0]

    img_urls = sorted(set(re.findall(r"https://[^\\s\\\"]+?\\.(?:png|webp)", payload, flags=re.IGNORECASE)))
    img_urls = sorted(set(img_urls + next_image_urls + html_asset_urls + meta_urls))

    # Extract imageUrl JSON fields (often used for actual assets, even when direct URLs aren't in HTML)
    try:
        raw_vals = re.findall(r'\"imageUrl\":\"(.*?)\"', payload)
        decoded_vals: list[str] = []
        for rv in raw_vals:
            try:
                decoded_vals.append(json.loads(f"\"{rv}\""))
            except Exception:
                decoded_vals.append(rv)
        img_urls = sorted(set(img_urls + [u for u in decoded_vals if isinstance(u, str) and u.startswith("http")]))
    except Exception:
        pass
    # Prefer Emojipedia "source" artwork hosts
    preferred = [u for u in img_urls if "zobj.net" in u]
    others = [u for u in img_urls if u not in preferred]
    def url_score(u: str) -> int:
        # Prefer explicit size folders like /1024/ /512/ etc.
        m = re.search(r"/(2048|1024|512|256|128|64|32)/", u)
        if m:
            s = int(m.group(1))
            return s * s
        # Prefer "source" over "social" previews
        if "/source/" in u:
            return 500_000
        if "/social/" in u:
            return 50_000
        # Prefer zobj assets in general
        if "zobj.net" in u:
            return 10_000
        return 0

    candidates = sorted((preferred + others), key=url_score, reverse=True)[:max_candidates]

    best_url: Optional[str] = None
    best_score = 0
    for u in candidates:
        try:
            data = requests.get(u, headers=UA, timeout=20).content
            score = _score_image_size_from_bytes(data)
            if score > best_score:
                best_score = score
                best_url = u
        except Exception:
            continue
    return best_url


def emojipedia_pick_source(
    query: str,
    alt: int = 0,
    *,
    art: str = "auto",
    design: int = 0,
) -> Optional[IconSource]:
    """
    Convenience: search, take first result, pick best artwork.
    (CLI wizard will typically show choices; this is for non-interactive use.)
    """
    results = emojipedia_search(query, limit=5)
    if not results:
        return None
    idx = 0 if alt is None else int(alt)
    idx = max(0, min(len(results) - 1, idx))

    page_url = results[idx].url
    emoji_slug = results[idx].path.strip("/").split("/", 1)[0]

    if art == "design":
        try:
            designs = emojipedia_list_designs(emoji_slug)
        except Exception:
            designs = []
        if not designs:
            return None
        d_idx = max(0, min(len(designs) - 1, int(design)))
        d = designs[d_idx]
        label = f"Emojipedia(design:{d.vendor_title}):{results[idx].title}"
        return IconSource(kind="url", value=d.source_url, label=label)
    if art == "social":
        best_art_url = emojipedia_best_artwork_url(page_url)
        return IconSource(kind="url", value=best_art_url, label=f"Emojipedia(social):{results[idx].title}") if best_art_url else None

    if art == "twemoji":
        page_html = _fetch_html(page_url)
        code = emojipedia_extract_emoji_code_from_page_html(page_html)
        if not code:
            return None
        return IconSource(kind="url", value=twemoji_svg_url(code), label=f"Emojipedia->Twemoji:{results[idx].title}")

    # auto:
    best_art_url = emojipedia_best_artwork_url(page_url)
    if best_art_url:
        # If it's a wide social banner, it tends to produce tiny icons; prefer Twemoji instead.
        if "/social/" in best_art_url:
            page_html = _fetch_html(page_url)
            code = emojipedia_extract_emoji_code_from_page_html(page_html)
            if code:
                return IconSource(kind="url", value=twemoji_svg_url(code), label=f"Emojipedia->Twemoji:{results[idx].title}")
        return IconSource(kind="url", value=best_art_url, label=f"Emojipedia:{results[idx].title}")

    # Fallback: try extracting emoji codepoint and use Twemoji
    page_html = _fetch_html(page_url)
    code = emojipedia_extract_emoji_code_from_page_html(page_html)
    if not code:
        return None
    return IconSource(kind="url", value=twemoji_svg_url(code), label=f"Emojipedia->Twemoji:{results[idx].title}")

