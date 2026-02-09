import json
import re
import sys
from pathlib import Path

import requests

# Allow running from a source checkout without installing (src/ layout).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from iconify import emoji_sources as es  # noqa: E402


UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def _decode_json_string(s: str) -> str:
    try:
        return json.loads(f"\"{s}\"")
    except Exception:
        return s


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else "lotus"
    url = f"https://emojipedia.org/{slug}"
    html = requests.get(url, headers=UA, timeout=30).text
    # Make stdout tolerant of emoji chars on Windows consoles
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass
    payload = es._extract_next_f_payloads(html)

    print("url:", url)
    print("html_len:", len(html))
    api_hits = sorted(set(re.findall(r"/api/[A-Za-z0-9_/\\-]+", html)))
    print("api_hits:", api_hits[:30])
    print("has_designs_anchor:", ("#designs" in html.lower()))
    kinds = re.findall(r"__next_f\.push\(\[(\d+),", html)
    if kinds:
        from collections import Counter

        c = Counter(kinds)
        print("next_f_kinds:", dict(sorted(c.items(), key=lambda kv: int(kv[0]))))
    for needle in ["/thumbs/", "/source/", "/_next/image?url=", "image-server/v1/images?r="]:
        print(f"html_has_{needle}:", (needle in html))
        if needle in html:
            j = html.find(needle)
            print("html_context:", html[max(0, j - 120) : j + 300])

    # Extract image-server URLs from full HTML
    img_srv = sorted(set(re.findall(r"https://is\.zobj\.net/image-server/v1/images\?r=[A-Za-z0-9_\-]+", html)))
    print("html_image_server_urls:", len(img_srv))
    print("html_image_server_samples:", img_srv[:10])
    # Try extracting around the designs hash anchor region
    d_idx = html.lower().find("#designs")
    if d_idx >= 0:
        tail = html[d_idx : d_idx + 20000]
        img_srv_tail = sorted(set(re.findall(r"https://is\.zobj\.net/image-server/v1/images\?r=[A-Za-z0-9_\-]+", tail)))
        print("tail_image_server_urls:", len(img_srv_tail))
        print("tail_image_server_samples:", img_srv_tail[:10])
    print("payload_len:", len(payload))
    print("has_designs_word:", ("design" in payload.lower()))
    print("has_imageUrl:", ("imageUrl" in payload))
    for vendor in ["Apple", "Google", "Microsoft", "Samsung", "WhatsApp", "Twitter", "Facebook", "JoyPixels", "OpenMoji"]:
        idx_v = payload.find(vendor)
        print(f"vendor {vendor} idx:", idx_v if idx_v >= 0 else None)
        if idx_v >= 0:
            print("vendor_context:", payload[max(0, idx_v - 120) : idx_v + 240])
    idx_img = payload.find("imageUrl")
    print("idx_imageUrl:", idx_img)
    if idx_img >= 0:
        print("imageUrl_context:", payload[max(0, idx_img - 120) : idx_img + 260])
        ctx = payload[max(0, idx_img - 120) : idx_img + 260]
        pat = r"\"name\":\"(.*?)\".*?\"imageUrl\":\"(https://is\\.zobj\\.net[^\"]+)\""
        mtest = re.search(pat, ctx, flags=re.DOTALL)
        print("regex_test_on_ctx:", bool(mtest))
        if mtest:
            print("regex_ctx_name:", mtest.group(1))
        # Find where this URL ends in the full payload
        idx_http = payload.find("https://is.zobj.net", idx_img)
        if idx_http >= 0:
            idx_endq = payload.find('"', idx_http)
            print("idx_http:", idx_http, "idx_end_quote:", idx_endq, "url_len:", (idx_endq - idx_http if idx_endq > idx_http else None))
            if idx_endq > idx_http:
                print("url_repr:", repr(payload[idx_http:idx_endq]))
                seg = payload[idx_img : idx_endq + 2]
                print("seg_repr:", repr(seg))
                print("seg_findall:", re.findall(r"\"imageUrl\":\"(https://is\\.zobj\\.net[^\"]+)\"", seg))

    # Show any designs-ish context
    idx = payload.lower().find("design")
    if idx >= 0:
        print("design_context:", payload[max(0, idx - 200) : idx + 400])

    # Extract name+imageUrl pairs
    print("count_literal_imageUrl:", payload.count('"imageUrl":"https://is.zobj.net/'))
    pairs = []
    for m in re.finditer(
        r"\"name\":\"(.*?)\".*?\"imageUrl\":\"(https://is\\.zobj\\.net/image-server/v1/images\\?r[^\"]+)\"",
        payload,
        flags=re.DOTALL,
    ):
        name = _decode_json_string(m.group(1))
        img = _decode_json_string(m.group(2))
        pairs.append((name, img))

    print("name+imageUrl pairs:", len(pairs))
    for name, img in pairs[:30]:
        print("-", name, img[:90] + ("..." if len(img) > 90 else ""))

    # Unique imageUrl list
    raw_vals = re.findall(r"\"imageUrl\":\"(https://is\\.zobj\\.net[^\"]+)\"", payload)
    print("raw_vals_simple:", len(raw_vals))
    urls = sorted(set(_decode_json_string(v) for v in raw_vals))
    print("unique imageUrl:", len(urls))
    print("sample urls:", [u[:80] for u in urls[:10]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

