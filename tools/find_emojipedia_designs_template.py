import re
import sys

import requests


UA = {"User-Agent": "Mozilla/5.0"}


def fetch(url: str) -> str:
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    return r.text


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass
    slug = sys.argv[1] if len(sys.argv) > 1 else "lotus"
    page_url = f"https://emojipedia.org/{slug}"
    html = fetch(page_url)

    scripts = re.findall(r'src="(/_next/static/chunks/[^"]+?\.js)"', html)
    # Dedup preserve order
    seen = set()
    scripts = [s for s in scripts if not (s in seen or seen.add(s))]
    print("page:", page_url)
    print("scripts:", len(scripts))
    needles = [
        "em-content.zobj.net/thumbs",
        "em-content.zobj.net/source",
        "em-content.zobj.net",
        "/thumbs/",
        "/source/",
        "thumbs",
        "source",
        "Emoji Designs",
        "#designs",
        "image-server",
    ]

    for s in scripts:
        url = "https://emojipedia.org" + s
        try:
            js = fetch(url)
        except Exception as e:
            print("ERR", s, repr(e))
            continue
        hits = [n for n in needles if n in js]
        if hits:
            print("chunk", s, "len", len(js), "hits", hits)
            n = hits[0]
            i = js.find(n)
            print(" context:", js[max(0, i - 120) : i + 240])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

