import re
import sys

import requests


UA = {"User-Agent": "Mozilla/5.0"}


def fetch(url: str) -> str:
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    return r.text


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else "lotus"
    page_url = f"https://emojipedia.org/{slug}"
    html = fetch(page_url)
    scripts = re.findall(r'src="(/_next/static/chunks/[^"]+?\.js)"', html)
    seen = set()
    scripts = [s for s in scripts if not (s in seen or seen.add(s))]
    print("scripts:", len(scripts))

    target = "42570:"
    for s in scripts:
        url = "https://emojipedia.org" + s
        try:
            js = fetch(url)
        except Exception:
            continue
        if target in js:
            print("FOUND in", s, "len", len(js))
            i = js.find(target)
            print(js[max(0, i - 200) : i + 800])
            return 0
    print("not found")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

