#!/usr/bin/env python3
"""Paginate the Squarespace blog JSON feed and save all posts -> posts_raw.json."""
import json, urllib.request, time

BASE = "https://www.journeyofourdreams.com/blog"
HDR = {'User-Agent': 'JourneyOfOurDreams-GlobeBuilder/1.0 (codyjhsieh@gmail.com)'}

all_items, seen, offset = [], set(), None
for page in range(80):
    url = BASE + "?format=json-pretty" + (f"&offset={offset}" if offset else "")
    req = urllib.request.Request(url, headers=HDR)
    d = json.load(urllib.request.urlopen(req, timeout=30))
    for it in d.get('items', []):
        if it['id'] in seen:
            continue
        seen.add(it['id'])
        all_items.append({
            'title': it.get('title', ''),
            'url': it.get('fullUrl', ''),
            'publishOn': it.get('publishOn'),
            'tags': it.get('tags', []),
            'categories': it.get('categories', []),
            'excerpt': (it.get('excerpt') or '')[:200],
            'assetUrl': it.get('assetUrl', ''),
        })
    pg = d.get('pagination', {})
    print(f"page {page}: total {len(all_items)} nextPage={pg.get('nextPage')}")
    if not pg.get('nextPage'):
        break
    offset = pg.get('nextPageOffset')
    time.sleep(0.3)

json.dump(all_items, open('posts_raw.json', 'w'), ensure_ascii=False, indent=1)
print("SAVED", len(all_items))
