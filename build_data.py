#!/usr/bin/env python3
"""Cluster geocoded posts into map locations, validate against country tags,
and emit data/locations.json + data/meta.json."""
import json, re, os
from collections import defaultdict
from datetime import datetime, timezone

posts = json.load(open('posts_geo.json'))
geo = json.load(open('data/countries-50m.geojson'))

TAG2ISO = {
 'Argentina':'AR','Australia':'AU','Austria':'AT','Bahamas':'BS','Barbodos':'BB','Bonaire':'BQ',
 'Brazil':'BR','Britain':'GB','Brunei':'BN','Cambodia':'KH','Canada':'CA','Cayman':'KY','Chile':'CL',
 'China':'CN','China2':'CN','Columbia':'CO','Costa Rica':'CR','Croatia':'HR','Curacao':'CW','Czech':'CZ',
 'Dominican Republic':'DO','Dubai':'AE','Fiji':'FJ','France':'FR','French Polynesia':'PF','Germany':'DE',
 'Grenada':'GD','Guadeloupe':'GP','Guatemala':'GT','Hungary':'HU','India':'IN','Italy':'IT','Jamaica':'JM',
 'Japan':'JP','Kenya':'KE','Korea':'KR','Lao':'LA','Liechtenstein':'LI','Malaysia':'MY','Maldives':'MV',
 'Martinique':'MQ','Mexico':'MX','Morocco':'MA','Netherlands':'NL','New Zealand':'NZ','Norway':'NO',
 'Panama':'PA','Paraguay':'PY','Philippines':'PH','Portugal':'PT','Puerto Rico':'PR','Seychelles':'SC',
 'Singapore':'SG','Slovakia':'SK','Slovenia':'SI','SouthAfrica':'ZA','Spain':'ES','SriLanka':'LK',
 'Sweden':'SE','Switzerland':'CH','Taiwan':'TW','Tanzania':'TZ','Thailand':'TH','TurkAndCaicos':'TC',
 'USA':'US','Uruguay':'UY','Vietnam':'VN','iceland':'IS','Aruba':'AW','AntiguaBarbuda':'AG','StLucia':'LC',
 'St. Barts':'BL','Marigot':'MF','JostVanDyke':'VG','Antarctic':'AQ',
}

# ---- country reference points (centroid of largest ring) + names, from the border geojson
def ring_centroid(ring):
    a = cx = cy = 0.0
    for i in range(len(ring) - 1):
        x0, y0 = ring[i]; x1, y1 = ring[i+1]
        cr = x0*y1 - x1*y0
        a += cr; cx += (x0+x1)*cr; cy += (y0+y1)*cr
    if a == 0:
        xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
        return sum(xs)/len(xs), sum(ys)/len(ys)
    a *= 0.5
    return cx/(6*a), cy/(6*a)

def largest_ring(geom):
    polys = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
    best, ba = None, -1
    for poly in polys:
        ring = poly[0]
        # crude area via shoelace
        a = abs(sum(ring[i][0]*ring[i+1][1]-ring[i+1][0]*ring[i][1] for i in range(len(ring)-1)))/2
        if a > ba: ba, best = a, ring
    return best

CC_POINT, CC_NAME = {}, {}
for f in geo['features']:
    pr = f['properties']
    for k in ('ISO_A2_EH', 'ISO_A2'):
        cc = (pr.get(k) or '').upper()
        if cc and cc != '-99' and cc not in CC_POINT:
            ring = largest_ring(f['geometry'])
            lng, lat = ring_centroid(ring)
            CC_POINT[cc] = (round(lat, 4), round(lng, 4))
            CC_NAME[cc] = pr.get('ADMIN') or pr.get('NAME') or cc

def year_of(p):
    ts = p.get('publishOn')
    if ts:
        return str(datetime.fromtimestamp(ts/1000, tz=timezone.utc).year)
    for c in p.get('categories', []):
        m = re.search(r'(20\d\d)', c)
        if m: return m.group(1)
    return '—'

def date_str(p):
    ts = p.get('publishOn')
    return datetime.fromtimestamp(ts/1000, tz=timezone.utc).strftime('%b %d, %Y') if ts else ''

BASE = 'https://www.journeyofourdreams.com'

# ---- manual coordinate overrides for the handful of posts that have no usable
#      title/slug/tag for automatic geocoding but are clearly a real place.
OVERRIDES = {
    'swarovski-crystal-worlds-amp-ambras-castle-amp-': (47.2752, 11.6014, 'Austria', 'AT'),
    'mount-rigi-switzerland': (47.0577, 8.4852, 'Switzerland', 'CH'),
}
for p in posts:
    slug = p['url'].rstrip('/').split('/')[-1]
    if slug in OVERRIDES:
        lat, lng, cn, cc = OVERRIDES[slug]
        p['lat'], p['lng'], p['geo_country'], p['geo_cc'] = lat, lng, cn, cc
        p['method'] = 'manual'

# ---- validate / correct each post against its country tags
relocated = recovered = 0
for p in posts:
    expected = {TAG2ISO[t] for t in p.get('tags', []) if t in TAG2ISO}
    cc = (p.get('geo_cc') or '').upper()
    if p.get('lat') is None:
        # city geocoding failed entirely -> drop a pin at the tagged country's centroid
        if expected:
            tgt = sorted(expected, key=lambda c: 0 if c in CC_POINT else 1)[0]
            if tgt in CC_POINT:
                p['lat'], p['lng'] = CC_POINT[tgt]
                p['geo_cc'] = tgt
                p['geo_country'] = CC_NAME.get(tgt, '')
                p['method'] = 'country-centroid'
                recovered += 1
        continue
    if expected and cc not in expected:
        # geocoder landed in the wrong country -> use the tagged country's centroid
        tgt = sorted(expected, key=lambda c: 0 if c in CC_POINT else 1)[0]
        if tgt in CC_POINT:
            p['lat'], p['lng'] = CC_POINT[tgt]
            p['geo_cc'] = tgt
            p['geo_country'] = CC_NAME.get(tgt, p.get('geo_country', ''))
            p['method'] = 'country-centroid'
            relocated += 1
    elif not cc and expected:
        tgt = sorted(expected)[0]
        if tgt in CC_POINT:
            p['lat'], p['lng'] = CC_POINT[tgt]
            p['geo_cc'] = tgt
            p['geo_country'] = CC_NAME.get(tgt, '')

# ---- cluster by rounded coordinate (~1km) so posts in one city share a pin
clusters = defaultdict(list)
located = [p for p in posts if p.get('lat') is not None]
for p in located:
    clusters[(round(p['lat'], 2), round(p['lng'], 2))].append(p)

def place_name(p):
    en = p.get('en') or p['title']
    return re.sub(r'\s*\(\d+\)', '', en).strip()

locations = []
for (lat, lng), grp in clusters.items():
    grp = sorted(grp, key=lambda x: x.get('publishOn') or 0, reverse=True)
    newest = grp[0]
    country = newest.get('geo_country') or (newest['country_tags'][0] if newest['country_tags'] else '')
    if any(p.get('method') == 'country-centroid' for p in grp):
        # country-centroid catch-all (city-level geocoding unavailable) -> label by country
        name = CC_NAME.get((newest.get('geo_cc') or '').upper(), country)
    else:
        names = [place_name(p) for p in grp]
        name = min(names, key=len) if names else newest['en']
    locations.append({
        'name': name, 'country': country, 'cc': newest.get('geo_cc', ''),
        'lat': lat, 'lng': lng, 'year': year_of(newest),
        'posts': [{
            'title': p['en'] or p['title'],
            'url': (p['url'] if p['url'].startswith('http') else BASE + p['url']),
            'date': date_str(p), 'ts': p.get('publishOn') or 0,
            'thumb': p.get('assetUrl', ''), 'year': year_of(p),
        } for p in grp]
    })
locations.sort(key=lambda l: len(l['posts']), reverse=True)

visited_cc = sorted({p['geo_cc'] for p in located if p.get('geo_cc')})
years = sorted({l['year'] for l in locations if l['year'] != '—'})
meta = {
    'post_count': len(posts), 'located_count': len(located),
    'country_count': len(visited_cc), 'visited_cc': visited_cc,
    'years': years, 'generated': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
}

os.makedirs('data', exist_ok=True)
json.dump(locations, open('data/locations.json', 'w'), ensure_ascii=False)
json.dump(meta, open('data/meta.json', 'w'), ensure_ascii=False, indent=1)

print(f"posts={len(posts)} located={len(located)} fails={len(posts)-len(located)} relocated={relocated} recovered_fails={recovered}")
print(f"pins={len(locations)} countries={len(visited_cc)}")
print(f"years={years}")
print(f"visited_cc={visited_cc}")
fails = [p['en'] for p in posts if p.get('lat') is None]
if fails: print("FAILS:", fails)
