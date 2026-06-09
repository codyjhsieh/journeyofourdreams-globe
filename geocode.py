#!/usr/bin/env python3
import json, re, time, urllib.request, urllib.parse, sys, os

POSTS = json.load(open('posts_raw.json'))
CACHE_F = 'geocache.json'
cache = json.load(open(CACHE_F)) if os.path.exists(CACHE_F) else {}

HDR = {'User-Agent': 'JourneyOfOurDreams-GlobeBuilder/1.0 (codyjhsieh@gmail.com)'}

# Real-country tags -> ISO2, for validation + fallback. Trip/region tags omitted on purpose.
TAG2ISO = {
 'Argentina':'ar','Australia':'au','Austria':'at','Bahamas':'bs','Barbodos':'bb','Bonaire':'bq',
 'Brazil':'br','Britain':'gb','Brunei':'bn','Cambodia':'kh','Canada':'ca','Cayman':'ky','Chile':'cl',
 'China':'cn','China2':'cn','Columbia':'co','Costa Rica':'cr','Croatia':'hr','Curacao':'cw','Czech':'cz',
 'Dominican Republic':'do','Dubai':'ae','Fiji':'fj','France':'fr','French Polynesia':'pf','Germany':'de',
 'Grenada':'gd','Guadeloupe':'gp','Guatemala':'gt','Hungary':'hu','India':'in','Italy':'it','Jamaica':'jm',
 'Japan':'jp','Kenya':'ke','Korea':'kr','Lao':'la','Liechtenstein':'li','Malaysia':'my','Maldives':'mv',
 'Martinique':'mq','Mexico':'mx','Morocco':'ma','Netherlands':'nl','New Zealand':'nz','Norway':'no',
 'Panama':'pa','Paraguay':'py','Philippines':'ph','Portugal':'pt','Puerto Rico':'pr','Seychelles':'sc',
 'Singapore':'sg','Slovakia':'sk','Slovenia':'si','SouthAfrica':'za','Spain':'es','SriLanka':'lk',
 'Sweden':'se','Switzerland':'ch','Taiwan':'tw','Tanzania':'tz','Thailand':'th','TurkAndCaicos':'tc',
 'USA':'us','Uruguay':'uy','Vietnam':'vn','iceland':'is','Aruba':'aw','AntiguaBarbuda':'ag','StLucia':'lc',
 'St. Barts':'bl','Marigot':'mf','JostVanDyke':'vg','Antarctic':'aq','Tahiti':'pf',
}

def clean_en(title):
    # cut at first CJK char; decode entities; trim
    t = re.sub(r'[　-鿿＀-￯].*$', '', title)
    t = t.replace('&amp;', '&').replace('&#39;', "'").replace('&quot;', '"')
    t = re.sub(r'\s+', ' ', t).strip(' -–—')
    return t

def strip_prefix(q):
    return re.sub(r'^(travel\s+to|back\s+to|to|arrive(?:\s+at)?|day\s+at|visiting|sailing\s+to|cruising\s+to|from)\s+',
                  '', q, flags=re.I).strip()

def country_tags(p):
    return [t for t in p['tags'] if t in TAG2ISO]

def slug_query(p):
    s = p['url'].rstrip('/').split('/')[-1]
    s = re.sub(r'-\d+$', '', s)            # trailing -1 / -2
    s = re.sub(r'\b(travel|to|the|amp|and|at|in|of|day|back|arrive)\b', ' ', s.replace('-', ' '))
    return re.sub(r'\s+', ' ', s).strip()

def nominatim(q, iso=None):
    key = f"{q}|{iso or ''}"
    if key in cache:
        return cache[key]
    params = {'q': q, 'format': 'jsonv2', 'limit': 1, 'addressdetails': 1}
    if iso:
        params['countrycodes'] = iso
    url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HDR)
            data = json.load(urllib.request.urlopen(req, timeout=30))
            res = data[0] if data else None
            cache[key] = res
            time.sleep(1.1)
            return res
        except Exception as e:
            sys.stderr.write(f"err {q}: {e}\n")
            time.sleep(3)
    cache[key] = None
    return None

out = []
for i, p in enumerate(POSTS):
    en = clean_en(p['title'])
    ctags = country_tags(p)
    iso_set = {TAG2ISO[t] for t in ctags}
    result = None
    method = None

    # try 1: full english title, constrained to tagged country if exactly one
    cand = strip_prefix(en) or en
    iso1 = list(iso_set)[0] if len(iso_set) == 1 else None
    if cand:
        result = nominatim(cand, iso1); method = 'title'
    # try 2: english title unconstrained (catches cross-border / wrong tag)
    if not result and cand:
        result = nominatim(cand); method = 'title-free'
    # try 3: slug constrained
    if not result:
        sq = slug_query(p)
        if sq and sq.lower() not in ('','travel'):
            result = nominatim(sq, iso1); method = 'slug'
    # try 4: country centroid
    if not result and ctags:
        result = nominatim(ctags[0]); method = 'country'

    rec = dict(p)
    rec['en'] = en
    rec['query'] = cand
    rec['country_tags'] = ctags
    if result:
        rec['lat'] = float(result['lat']); rec['lng'] = float(result['lon'])
        addr = result.get('address', {})
        rec['geo_country'] = addr.get('country', '')
        rec['geo_cc'] = (addr.get('country_code') or '').upper()
        rec['geo_name'] = result.get('display_name', '')
        rec['geo_type'] = result.get('type', '')
        rec['method'] = method
    else:
        rec['lat'] = rec['lng'] = None
        rec['method'] = 'FAIL'
    out.append(rec)
    if i % 10 == 0:
        json.dump(cache, open(CACHE_F, 'w'), ensure_ascii=False)
        sys.stderr.write(f"{i}/{len(POSTS)} {method} {en[:30]} -> {rec.get('geo_cc')}\n")

json.dump(cache, open(CACHE_F, 'w'), ensure_ascii=False)
json.dump(out, open('posts_geo.json', 'w'), ensure_ascii=False, indent=1)
fails = [p['en'] for p in out if p['method'] == 'FAIL']
sys.stderr.write(f"DONE. {len(out)} posts, {len(fails)} fails\n")
