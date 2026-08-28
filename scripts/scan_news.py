#!/usr/bin/env python3
"""
GameWave scanner: RSS -> verified images -> drafted Hugo posts.

Self-contained (Python stdlib only). Logs to $HOME/.gwi/run.log because
sys.stdout is unreliable on this Termux build; shell pipeline reads the log.
"""
import os
import re
import sys
import json
import time
import hashlib
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit, urlunsplit
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

HOME = os.path.expanduser("~")
ROOT = os.path.join(HOME, "gamewave-daily")
POSTS = os.path.join(ROOT, "content", "posts")
IMG = os.path.join(ROOT, "static", "images", "posts")
STATE = os.path.join(POSTS, ".scan_state.json")
LOG = os.path.join(HOME, ".gwi", "run.log")

os.makedirs(os.path.join(HOME, ".gwi"), exist_ok=True)

try:
    sys.stdout = open(LOG, "a", buffering=1)
except Exception:
    pass

UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36")

FEEDS = [
    ("IGN",        "https://www.ign.com/rss/articles/feed",
     ["ignimgs.com", "assets-prd.ignimgs.com", "oyster.ignimgs.com"]),
    ("PC Gamer",   "https://www.pcgamer.com/rss/razed-white-space-all.xml",
     ["futurecdn.net", "pcgamer.com", "gamesradar.com", "windowscentral.com"]),
    ("GameSpot",   "https://www.gamespot.com/feeds/news/",
     ["gamespot.com", "ares.spot.im", "spot.im"]),
    ("Polygon",    "https://www.polygon.com/rss/index.xml",
     ["polygon.com", "vox-cdn.com"]),
    ("Eurogamer",  "https://www.eurogamer.net/feed",
     ["eurogamer.net", "gematsu.com"]),
    ("Gematsu",    "https://www.gematsu.com/feed",
     ["gematsu.com"]),
    ("VGC",        "https://www.videogameschronicle.com/feed/",
     ["videogameschronicle.com", "wp.com"]),
    ("The Verge Games", "https://www.theverge.com/rss/games/index.xml",
     ["theverge.com", "vox-cdn.com"]),
]

BANNED = [
    "audio", "soundtrack", "sound design", "score by", "composed by",
    "review", "speedrun", "deal", "trailer", "update",
    "call of duty", "cod ", "fifa", "madden", "nba 2k", "ea fc",
    "halo", "gta+", "warzone", "f2p", "free-to-play", "genshin",
    "rpg", "souls", "mmo", "guild", "diablo",
]

CLASSIFIER = {
    "Leaks": ["leak", "datamined", "rumour", "rumor", "allegedly", "insider",
              "fans spot", "suggests", "unannounced", "cancelled"],
    "Reviews": ["impressions", "hands-on", "hands on", "verdict", "goty",
                "game of the year", "rated", "scored"],
    "Indie": ["indie", "early access", "steam next fest", "itch.io",
              "kickstarter", "small studio", "cozy", "roguelike"],
    "Esports": ["esports", "tournament", "championship", "major",
                "prize pool", "fnatic", "liquipedia", "valorant",
                "league of legends", "dota", "cs2", "counter-strike",
                "apex legends", "fortnite"],
    "Tech": ["technolog", "gpu", "cpu", "rtx", "dlss", "fsr", "driver",
             "laptop", "monitor", "steam deck", "handheld", "frame gen"],
    "Updates": ["patch", "hotfix", "season ", "live-service", "battle pass",
                "maintenance"],
}

ALLOWED_IMAGE_MAGIC = {
    b"\xff\xd8\xff": "jpg",
    b"\x89PNG\r\n\x1a\n": "png",
}
WEBP_MAGIC = b"RIFF"

MAX_BYTES = 2_500_000
PER_FEED_CAP = 2
MAX_TOTAL = 6
SLEEP = 0.33


def log(msg):
    stamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{stamp}] {msg}"
    print(line)
    try:
        os.write(1, (line + "\n").encode())
    except Exception:
        pass


def http_bytes(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Encoding": "identity",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("too large")
        return raw


def fetch_feed(url):
    return http_bytes(url).decode("utf-8", "replace")


def parse_items(xml_text):
    """Return list of item dicts from RSS 2.0 or Atom."""
    r = ET.fromstring(xml_text)
    items = []
    if r.tag.endswith("rss"):
        for it in r.findall("./channel/item"):
            desc = it.findtext("description") or ""
            items.append(_wrap(it, desc))
    else:  # atom
        ns = {"a": "urn:atom"}
        for e in r.findall("a:entry", ns):
            content = e.find("a:content", ns)
            summary = e.find("a:summary", ns)
            desc = ""
            if content is not None and content.text:
                desc = content.text
            elif summary is not None and summary.text:
                desc = summary.text
            items.append(_wrap(e, desc, atom=True))
    return items


def _wrap(el, desc, atom=False):
    if atom:
        title = el.findtext("{urn:atom}title") or ""
        link_el = el.find("{urn:atom}link")
        link = link_el.get("href") if link_el is not None else ""
        guid = el.findtext("{urn:atom}id") or link
        date = el.findtext("{urn:atom}published") or el.findtext("{urn:atom}updated")
    else:
        title = el.findtext("title") or ""
        link = el.findtext("link") or ""
        guid = el.findtext("guid") or link
        date = el.findtext("pubDate") or ""
    img = _image_from_el(el, desc)
    return {"title": title.strip(), "link": link.strip(),
            "guid": guid.strip(), "date": date.strip(),
            "desc": desc, "image": img}


def _image_from_el(el, desc):
    fields = [
        el.find("enclosure"),
        el.find("{http://search.yahoo.com/mrss/}content"),
        el.find("{http://search.yahoo.com/mrss/}thumbnail"),
    ]
    m = re.search(r'<img[^>]+src="([^"]+)"', desc)
    if m:
        fields.insert(0, type("F", (), {"get": lambda k: m.group(1)}))
    for f in fields:
        if f is not None:
            url = f.get("url") if hasattr(f, "get") else None
            if url:
                return url.strip()
    return None


def is_allowed(img_url, hosts):
    host = (urlsplit(img_url).netloc or "").lower()
    return any(h in host for h in hosts)


def verify_and_ext(blob):
    for magic, ext in ALLOWED_IMAGE_MAGIC.items():
        if blob.startswith(magic):
            return ext
    if blob[:4] == WEBP_MAGIC and blob[8:12] == b"WEBP":
        return "webp"
    return None


def parse_date(raw, now_utc):
    raw = (raw or "").strip()
    if not raw:
        return now_utc
    try:
        return parsedate_to_datetime(raw)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return now_utc


def clean_text(html):
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def first_sentences(text, max_chars=380):
    if not text:
        return None
    sents = re.split(r"(?<=[.!?])\s+", text)
    out = ""
    for s in sents:
        if len(out) + len(s) > max_chars:
            break
        out += s + " "
        if len(out) > 140:
            break
    out = out.strip()
    if len(out) > max_chars:
        out = out[:max_chars].rsplit(" ", 1)[0] + "..."
    return out if len(out) > 60 else None


def slugify(title):
    s = re.sub(r"[^0-9a-z]+", "-", title.lower()).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return s[:80].strip("-") or "item"


def classify(title, desc):
    blob = (title + " " + desc).lower()
    tags = []
    for tag, kws in CLASSIFIER.items():
        if any(k in blob for k in kws):
            tags.append(tag)
    if not tags:
        tags = ["News"]
    tags.sort()
    return tags


def banned(title):
    tl = title.lower()
    return any(b in tl for b in BANNED)


def load_state():
    if os.path.exists(STATE):
        try:
            with open(STATE) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_state(st):
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f)
    os.replace(tmp, STATE)


def ensure_writable():
    for p in (STATE, os.path.join(ROOT, "hugo.toml")):
        if os.path.exists(p):
            os.chmod(p, 0o644)


def today_dir():
    now = datetime.now(timezone.utc)
    return now.strftime("%Y/%m/%d")


def run():
    ensure_writable()
    ensure_img_dir()
    referrer_map = {name: (url, hosts) for name, url, hosts in FEEDS}
    state = load_state()
    now_utc = datetime.now(timezone.utc)
    counter = 0
    created = []

    for name, feed_url, hosts in FEEDS:
        if counter >= MAX_TOTAL:
            break
        try:
            xml_text = fetch_feed(feed_url)
        except Exception as e:
            log(f"{name}: fetch error {e}")
            continue
        try:
            items = parse_items(xml_text)
        except Exception as e:
            log(f"{name}: parse error {e}")
            continue
        log(f"{name}: {len(items)} items")
        seen = set(state.get(name, []))
        accepted = 0
        for it in items:
            if counter >= MAX_TOTAL or accepted >= PER_FEED_CAP:
                break
            guid = it["guid"] or it["link"]
            if not guid or guid in seen:
                continue
            if banned(it["title"]):
                continue
            img_url = it["image"]
            ext = None
            blob = None
            if img_url and is_allowed(img_url, hosts):
                try:
                    blob = http_bytes(img_url)
                    ext = verify_and_ext(blob)
                    if ext is None:
                        log(f"  skip bad image {img_url[:60]}")
                except Exception as e:
                    log(f"  image error {img_url[:60]} -> {e}")
            if not ext:
                seen.add(guid)
                seen = trim_seen(seen)
                state[name] = list(seen)
                continue
            date = parse_date(it["date"], now_utc)
            post = write_post(it, ext, blob, date, name)
            if post:
                seen.add(guid)
                seen = trim_seen(seen)
                state[name] = list(seen)
                accepted += 1
                counter += 1
                created.append(post)
                log(f"  + {post}")
            else:
                seen.add(guid)
                seen = trim_seen(seen)
                state[name] = list(seen)
            time.sleep(SLEEP)

    save_state(state)
    log(f"done: {len(created)} posts created")
    return len(created)


def trim_seen(seen, cap=300):
    if len(seen) > cap:
        return set(list(seen)[-cap:])
    return seen


def ensure_img_dir():
    sub = today_dir()
    os.makedirs(os.path.join(IMG, sub, "images"), exist_ok=True)


def write_post(it, ext, blob, date, source_site):
    slug = slugify(it["title"])
    path = os.path.join(POSTS, f"{slug}.md")
    n = 2
    while os.path.exists(path):
        path = os.path.join(POSTS, f"{slug}-{n}.md")
        n += 1
    fname = os.path.basename(path).replace(".md", "") + "." + ext
    sub = date.strftime("%Y/%m/%d")
    img_dir = os.path.join(IMG, sub, "images")
    os.makedirs(img_dir, exist_ok=True)
    img_path = os.path.join(img_dir, fname)
    with open(img_path, "wb") as f:
        f.write(blob)

    tags = classify(it["title"], it["desc"])
    lead = first_sentences(clean_text(it["desc"]))
    body = ""
    if lead:
        body += lead + "\n\n"
    body += f"[Read the full story at {source_site}]({it['link']})\n\n"
    body += "What do you think? Jump into the thread below and share your take."

    fm = []
    fm.append("---")
    fm.append(f"title: \"{esc(it['title'])}\"")
    fm.append(f"date: \"{date.isoformat()}\"")
    fm.append(f"tags: [{', '.join(f'\"{t}\"' for t in tags)}]")
    fm.append("draft: false")
    fm.append(f"feature: \"/images/posts/{sub}/images/{fname}\"")
    fm.append(f"source_url: \"{esc(it['link'])}\"")
    fm.append(f"source_site: \"{source_site}\"")
    fm.append("---")
    fm.append("")
    fm.append(body)
    fm.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(fm))
    return f"{fname} -> {os.path.basename(path)} [{', '.join(tags)}]"


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        log(f"FATAL: {e}")
        raise