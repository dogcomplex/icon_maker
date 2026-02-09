import json

import requests


def main() -> int:
    try:
        import sys

        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass
    q = """
    query emojiV1($slug: Slug!, $lang: Language) {
      emoji_v1(slug: $slug, lang: $lang) {
        title
        code
        slug
        codepointsHex
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
    v = {"slug": "lotus", "lang": "EN"}
    r = requests.post(
        "https://emojipedia.org/api/graphql",
        headers={"User-Agent": "Mozilla/5.0", "content-type": "application/json"},
        data=json.dumps({"operationName": "emojiV1", "query": q, "variables": v}),
        timeout=30,
    )
    print("status:", r.status_code)
    print("ct:", r.headers.get("content-type"))
    data = r.json()
    print("top_keys:", list(data.keys()))
    if "data" in data and data["data"] and "emoji_v1" in data["data"]:
        ev = data["data"]["emoji_v1"]
        print("emoji:", ev.get("code"), ev.get("title"), ev.get("codepointsHex"))
        vps = ev.get("vendorsAndPlatforms") or []
        print("vendorsAndPlatforms:", len(vps))
        # Show first few vendors with an image source
        shown = 0
        for vp in vps:
            items = vp.get("items") or []
            sources = [it.get("image", {}).get("source") for it in items if it.get("image")]
            sources = [s for s in sources if s]
            if sources:
                print(" -", vp.get("title"), "items:", len(items), "sample_source:", sources[0])
                shown += 1
                if shown >= 8:
                    break
    else:
        print("body_preview:", r.text[:800])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

