"""Диагностика: что Википедия отвечает на запросы моделей (поиск + инфобокс вводной секции)."""
import json
import sys
import time

import httpx

API = "https://en.wikipedia.org/w/api.php"
UA = {"User-Agent": "IPapaPriceBot/1.0 (https://github.com/dkaratsapov-web/ipapa)"}
QUERIES = sys.argv[1:] or [
    "MacBook Air 13 M5", "MacBook Air 15 M4", "MacBook Air M5", "MacBook Pro 14 M5", "MacBook Pro 13 M1",
    "MacBook Neo", "MacBook 13 Neo", "iPhone Air", "iPhone 17 Pro Max", "iPhone 17e", "iPad 11 A16",
    "iPad (A16)", "iPad Air M3", "iPad Pro M5", "iPad mini A17 Pro", "Apple Watch Ultra 2", "Apple Watch Ultra 3",
    "Apple Watch SE", "Apple Watch SE 3", "Apple Watch Series 11", "Apple Watch Series 12", "AirPods Max",
    "AirPods 4", "AirPods Pro 3", "AirPods 3", "Apple TV 4K", "Pixel 10", "Pixel 10 Pro", "iMac M4", "Mac mini M4",
]


def get(client, params):
    time.sleep(1)
    return client.get(API, params={**params, "format": "json"}).json()


def main():
    out = {}
    with httpx.Client(headers=UA, timeout=30, follow_redirects=True) as client:
        for q in QUERIES:
            hits = [h["title"] for h in get(client, {"action": "query", "list": "search", "srsearch": q,
                                                     "srlimit": 8})["query"]["search"]]
            pages = {}
            for title in hits[:3]:
                page = get(client, {"action": "parse", "page": title, "prop": "wikitext", "section": 0,
                                    "redirects": 1}).get("parse", {})
                text = page.get("wikitext", {})
                pages[title] = {"real": page.get("title"), "wikitext": text.get("*", "") if isinstance(text, dict) else text}
            out[q] = {"hits": hits, "pages": pages}
            print(q, "->", hits, flush=True)
    json.dump(out, open("wiki_probe.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
