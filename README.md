# 🌍 Journey of Our Dreams — Interactive Travel Globe

An embeddable, dynamic **3D globe** that maps **every blog post** from
[journeyofourdreams.com](https://www.journeyofourdreams.com/blog) to its real-world
location on an accurate Earth, with highlighted country borders and clickable pins
that link straight to each post.

**Live preview (GitHub Pages):** https://codyjhsieh.github.io/journeyofourdreams-globe/

---

## What it does

- **Real 3D Earth** — NASA Blue Marble texture + topology bump, rendered with
  [globe.gl](https://github.com/vasturiano/globe.gl) (three.js / WebGL).
- **Accurate country borders** — [Natural Earth 50m](https://www.naturalearthdata.com/)
  admin-0 polygons. Every country the blog has visited is filled & outlined in gold.
- **Accurate pins** — each post is geocoded from its title via
  [OpenStreetMap Nominatim](https://nominatim.org/); posts in the same city are clustered
  into one pin. Pins are colored by travel year.
- **Clickable** — click a pin to open a side panel listing every post at that place
  (thumbnail, title, date) linking to the live blog post. Search any place or country.

## Files

| File | Purpose |
|------|---------|
| `embed.html` | The standalone, embeddable globe (this is what you iframe into Squarespace). |
| `index.html` | A mock Squarespace-style page that previews the embed + shows the snippet. |
| `data/locations.json` | Geocoded, clustered pins (generated). |
| `data/meta.json` | Counts, visited country ISO codes, year list (generated). |
| `data/countries-50m.geojson` | Natural Earth 50m country borders. |
| `scrape` pipeline | `geocode.py` → `build_data.py` regenerate the data. |

## Embed in Squarespace

1. Edit a page/post → **Add Block** → **Code**.
2. Paste, with the block set to **HTML**:

```html
<iframe
  src="https://codyjhsieh.github.io/journeyofourdreams-globe/embed.html"
  title="Journey of Our Dreams Travel Globe"
  style="width:100%;height:80vh;min-height:560px;border:0;border-radius:16px;overflow:hidden;"
  loading="lazy" allow="accelerometer; gyroscope">
</iframe>
```

3. Save. Replace the host with your own GitHub Pages URL.

## Regenerate the data

```bash
python3 scrape_feed.py   # paginate the Squarespace JSON feed -> posts_raw.json
python3 geocode.py       # geocode each post via Nominatim -> posts_geo.json (+ geocache.json)
python3 build_data.py    # cluster + emit data/locations.json, data/meta.json
```

Data scraped from the public Squarespace JSON feed (`/blog?format=json-pretty`), which the
site exposes for every post. Geocoding respects Nominatim's 1 req/sec policy and is cached.

---

*Borders © Natural Earth (public domain) · Geocoding © OpenStreetMap contributors (ODbL) · Globe © globe.gl (MIT)*
