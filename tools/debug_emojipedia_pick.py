import io
import sys
from pathlib import Path

# Allow running from a source checkout without installing (src/ layout).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import requests
from PIL import Image

from iconify.emoji_sources import emojipedia_best_artwork_url, emojipedia_search
from iconify import emoji_sources as es


UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def img_size(url: str) -> tuple[int, int] | None:
    try:
        r = requests.get(url, headers=UA, timeout=30)
        r.raise_for_status()
        with Image.open(io.BytesIO(r.content)) as img:
            return img.size
    except Exception:
        return None


def probe(url: str) -> None:
    try:
        r = requests.get(url, headers=UA, timeout=30, allow_redirects=True)
        print("probe_status:", r.status_code, "ct:", r.headers.get("content-type"), "len:", r.headers.get("content-length"))
        print("probe_final_url:", r.url)
        print("probe_head_bytes:", r.content[:16])
    except Exception as e:
        print("probe_error:", repr(e))


def main() -> int:
    q = sys.argv[1] if len(sys.argv) > 1 else "lotus"
    alt = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    # Raw HTML href sniff
    search_url = f"https://emojipedia.org/search/?q={q}"
    html = requests.get(search_url, headers=UA, timeout=30).text
    import re

    hrefs = re.findall(r'href="([^"]+)"', html)
    lotusish = [h for h in hrefs if "lotus" in h.lower()][:40]
    print("search_url:", search_url)
    print("html_len:", len(html))
    print("href_count:", len(hrefs))
    print("href_lotusish:", lotusish[:20])

    # Inspect a likely page
    page_try = "https://emojipedia.org/lotus"
    page_html = requests.get(page_try, headers=UA, timeout=30).text
    img_urls = sorted(
        set(re.findall(r"https://[^\\\"\\s>]+\\.(?:png|webp|svg)", page_html, flags=re.I))
    )
    zobj = [u for u in img_urls if "zobj.net" in u]
    print("page_try:", page_try, "len:", len(page_html))
    print("page_img_urls:", len(img_urls), "zobj:", len(zobj))
    print("page_img_samples:", (zobj[:10] if zobj else img_urls[:10]))

    # Look for social preview meta tags which often contain a usable image URL
    metas = []
    for key in ["og:image", "twitter:image", "twitter:image:src"]:
        m = re.search(rf'property=\"{key}\" content=\"([^\"]+)\"', page_html)
        if not m:
            m = re.search(rf'name=\"{key}\" content=\"([^\"]+)\"', page_html)
        if m:
            metas.append((key, m.group(1)))
    print("meta_images:", metas)
    print("has_zobj_in_html:", ("zobj.net" in page_html))
    thumbs = sorted(set(re.findall(r"https://em-content\\.zobj\\.net/thumbs/[^\\s\\\"'>]+\\.(?:png|webp)", page_html, flags=re.I)))
    print("thumbs_urls:", len(thumbs))
    print("thumbs_samples:", thumbs[:10])

    payload = es._extract_next_f_payloads(page_html)
    p_urls = sorted(set(re.findall(r"https://[^\\s\\\"]+?\\.(?:png|webp|svg)", payload, flags=re.I)))
    p_zobj = [u for u in p_urls if "zobj.net" in u]
    print("payload_len:", len(payload))
    print("payload_urls:", len(p_urls), "payload_zobj:", len(p_zobj))
    print("payload_samples:", (p_zobj[:10] if p_zobj else p_urls[:10]))
    print("payload_has_zobj:", ("zobj" in payload.lower()))
    if "zobj" in payload.lower():
        idx = payload.lower().find("zobj")
        print("payload_zobj_context:", payload[max(0, idx - 120) : idx + 240])

    img_srv = sorted(set(re.findall(r"https://is\.zobj\.net/image-server/v1/images\?r=[^\"\\s]+", payload)))
    print("image_server_urls:", len(img_srv))
    print("image_server_samples:", img_srv[:10])
    for u in img_srv[:5]:
        print("img_srv_size", u, img_size(u))

    idx_is = payload.find("https://is.zobj.net/image-server/v1/images?r=")
    print("idx_is:", idx_is)
    if idx_is >= 0:
        snippet = payload[idx_is : idx_is + 200]
        print("is_snippet:", repr(snippet))
        m = re.search(r"https://is\.zobj\.net/image-server/v1/images\?r=[^\"\\s]+", snippet)
        print("snippet_regex_match:", (m.group(0) if m else None))

    # Pull any imageUrl JSON fields (these tend to be the real assets)
    import json
    raw_vals = re.findall(r'\"imageUrl\":\"(.*?)\"', payload)
    decoded = []
    for rv in raw_vals[:50]:
        try:
            decoded.append(json.loads(f'\"{rv}\"'))
        except Exception:
            decoded.append(rv)
    decoded = [d for d in decoded if isinstance(d, str)]
    print("imageUrl_fields:", len(raw_vals))
    print("imageUrl_samples:", decoded[:10])
    if decoded:
        print("probe_first_imageUrl:")
        probe(decoded[0])

    # (debug) we intentionally avoid deeper JS parsing here.

    results = emojipedia_search(q, limit=10)
    print("query:", q)
    print("results:", len(results))
    for i, r in enumerate(results[:10]):
        print(f"  {i}: {r.title} {r.url}")

    if not results:
        return 2
    pick = max(0, min(len(results) - 1, alt))
    page_url = results[pick].url
    print("picked_page:", page_url)
    art = emojipedia_best_artwork_url(page_url)
    print("picked_art:", art)
    if art:
        print("art_size:", img_size(art))
    else:
        # try meta preview directly for lotus debug
        meta_url = "https://em-content.zobj.net/social/emoji/lotus.png"
        print("meta_preview_size:", img_size(meta_url))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

