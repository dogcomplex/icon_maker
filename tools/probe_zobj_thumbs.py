import itertools

import requests


UA = {"User-Agent": "Mozilla/5.0"}


def head(url: str):
    try:
        r = requests.head(url, headers=UA, timeout=10, allow_redirects=True)
        return r.status_code, r.headers.get("content-type"), r.headers.get("content-length"), r.url
    except Exception:
        return None, None, None, None


def main() -> int:
    base = "https://em-content.zobj.net"
    vendors = [
        "apple",
        "google",
        "microsoft",
        "samsung",
        "whatsapp",
        "twitter",
        "facebook",
        "joypixels",
        "openmoji",
    ]
    sizes = ["60", "72", "90", "120", "160", "240", "320", "512", "1024"]
    slugs = ["lotus"]
    cps = ["1fab7", "1f33c"]
    names = []
    for slug, cp in itertools.product(slugs, cps):
        names += [f"{slug}.png", f"{slug}.webp", f"{cp}.png", f"{cp}.webp", f"{slug}_{cp}.png", f"{slug}_{cp}.webp"]

    patterns = [
        "{base}/thumbs/{size}/{vendor}/{name}",
        "{base}/thumbs/{size}/{vendor}/emoji/{name}",
        "{base}/thumbs/{size}/{vendor}/emoji/{vendor}/{name}",
        "{base}/thumbs/{size}/{vendor}/source/{name}",
        "{base}/source/{vendor}/{size}/{name}",
        "{base}/source/{vendor}/{name}",
        "{base}/source/{vendor}/emoji/{name}",
        "{base}/source/{vendor}/emoji/{vendor}/{name}",
    ]

    hits = []
    for vendor, size in itertools.product(vendors, sizes):
        for pat in patterns:
            for name in names:
                url = pat.format(base=base, vendor=vendor, size=size, name=name)
                code, ct, cl, final = head(url)
                if code == 200 and ct and "image" in ct:
                    hits.append((vendor, size, ct, cl, url, final))
                    print("HIT", vendor, size, ct, cl, url)
    print("total hits:", len(hits))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

