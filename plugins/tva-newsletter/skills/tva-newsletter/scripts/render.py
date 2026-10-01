#!/usr/bin/env python3
"""Render a weekly MTVA/YTVA issue (issue.json) into Constant Contact custom-code HTML.

    python3 render.py WEEK/MTVA/issue.json            # after images.py: hosted URLs
    python3 render.py WEEK/MTVA/issue.json --preview  # local preview, file:// images

Writes out/email.html (or out/preview.html) next to issue.json, prints the
subject/preheader, and runs the Constant Contact checks. Exit code 1 if a check fails.
Stdlib only (Pillow optional, used to read local image sizes in preview mode).
"""
import argparse, datetime as dt, html, json, re, sys, urllib.parse, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROGRAMS = HERE.parent / "programs"
MAX_BYTES = 400 * 1024          # Constant Contact hard limit
GMAIL_CLIP = 102 * 1024         # Gmail clips bodies past ~102 KB ("[Message clipped]")


# ---------------------------------------------------------------- header data
def hebcal_header(friday: dt.date):
    """Parsha, special Shabbat, Hebrew date and Jerusalem candle lighting from Hebcal."""
    q = f"https://www.hebcal.com/shabbat?cfg=json&geonameid=281184&M=on&b=40&gy={friday.year}&gm={friday.month}&gd={friday.day}"
    items = json.load(urllib.request.urlopen(q, timeout=20))["items"]
    out = {"parsha": None, "special": None, "candles": None, "holidays": []}
    for it in items:
        d = it.get("date", "")[:10]
        if it["category"] == "candles" and d == friday.isoformat():
            hh, mm = it["date"][11:16].split(":")
            out["candles"] = f"{int(hh) % 12 or 12}:{mm} {'PM' if int(hh) >= 12 else 'AM'}"
        elif it["category"] == "parashat":
            out["parsha"] = it["title"].replace("Parashat ", "").replace("’", "'")
        elif it["category"] == "holiday" and d == (friday + dt.timedelta(days=1)).isoformat():
            out["holidays"].append(it["title"].replace("’", "'"))
            if it["title"].startswith("Shabbat "):
                out["special"] = it["title"]
    c = json.load(urllib.request.urlopen(
        f"https://www.hebcal.com/converter?cfg=json&date={friday.isoformat()}&g2h=1", timeout=20))
    out["hebrew_date"] = f"{c['hd']} {c['hm']} {c['hy']}"
    out["hebrew_year"] = str(c["hy"])
    return out


def ordinal(n):
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


# ---------------------------------------------------------------- text helpers
def inline(text):
    """Escape, then allow **bold**, *italic*, [text](url) and single newlines."""
    t = html.escape(text.strip(), quote=False)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+|mailto:[^)\s]+)\)",
               lambda m: f'<a href="{html.escape(m.group(2))}" style="color:inherit;text-decoration:underline;" target="_blank">{m.group(1)}</a>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])", r"<em>\1</em>", t)
    return t.replace("\n", "<br>")


def img_src(ref):
    return ref["src"] if isinstance(ref, dict) else ref


def img_dims(ref, base):
    if isinstance(ref, dict) and ref.get("w"):
        return ref["w"], ref["h"]
    src = img_src(ref)
    if not src.startswith("http"):
        try:
            from PIL import Image, ImageOps
            with Image.open(resolve_local(src, base)) as im:
                im = ImageOps.exif_transpose(im)
                return im.size
        except Exception:
            pass
    return 4, 3  # unknown: treat as landscape


def resolve_local(src, base):
    p = Path(src).expanduser()
    return p if p.is_absolute() else (base / p)


class Ctx:
    def __init__(self, prog, base, preview):
        self.p, self.c, self.base, self.preview = prog, prog["colors"], base, preview
        self.local_refs = []

    def url(self, ref):
        src = img_src(ref)
        if src.startswith("http"):
            return src
        self.local_refs.append(src)
        return resolve_local(src, self.base).resolve().as_uri() if self.preview else src

    def headshot(self, name_or_ref):
        if not name_or_ref:
            return None
        if isinstance(name_or_ref, dict):
            return name_or_ref
        return self.p.get("known_headshots", {}).get(name_or_ref, name_or_ref)


# ---------------------------------------------------------------- design tokens
SANS = "Helvetica,Arial,sans-serif"
SERIF = "Georgia,'Times New Roman',serif"
INK = "#24273A"          # body text
NAVY = "#262E67"         # headings, donate band
MUTED = "#6B6F82"        # secondary text
RULE = "#E6E4EC"         # hairlines
PAGE = "#ECEEF3"         # outside the card
FOOT = "#F6F5F8"         # footer panel
GOLD = "#F7BA3E"
CARD_W, PAD = 600, 32
INNER = CARD_W - 2 * PAD  # 536


def avatar_square(x, ref):
    """Preview only: square-crop a headshot (local or remote) so the circle is not stretched."""
    try:
        from PIL import Image, ImageOps
        import hashlib, io
        src = img_src(ref)
        raw = urllib.request.urlopen(src, timeout=20).read() if src.startswith("http") else resolve_local(src, x.base).read_bytes()
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
        s = min(im.size)
        top = int((im.height - s) * 0.2)  # faces sit high in portraits
        im = im.crop(((im.width - s) // 2, top, (im.width - s) // 2 + s, top + s)).resize((240, 240), Image.LANCZOS)
        d = x.base / "out" / "_preview"
        d.mkdir(parents=True, exist_ok=True)
        f = d / f"avatar-{hashlib.sha1(raw).hexdigest()[:10]}.jpg"
        im.save(f, "JPEG", quality=85)
        return f.as_uri()
    except Exception as e:
        print(f"  ! could not crop headshot for preview: {e}", file=sys.stderr)
        return None


def row(inner, bg="#FFFFFF", pad=f"28px {PAD}px", align="left", cls="px"):
    return (f'<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0" bgcolor="{bg}" style="background-color:{bg};">'
            f'<tr><td class="{cls}" align="{align}" style="padding:{pad};">{inner}</td></tr></table>')


def rule():
    return row(f'<div style="height:1px;line-height:1px;font-size:0;background-color:{RULE};">&nbsp;</div>', pad=f"0 {PAD}px")


def eyebrow(x, text):
    return (f'<div style="font-family:{SANS};font-size:12px;font-weight:bold;letter-spacing:1.5px;text-transform:uppercase;'
            f'color:{x.c["accent_text"]};margin:0 0 8px 0;">{inline(text)}</div>')


def h2(text, size=26):
    return (f'<h2 dir="auto" style="margin:0 0 14px 0;font-family:{SERIF};font-size:{size}px;line-height:1.25;font-weight:bold;color:{NAVY};">'
            f'{inline(text)}</h2>')


def body_text(body, serif=True, size=None, color=INK, align="left"):
    if isinstance(body, list):
        body = "\n\n".join(body)
    fam, size = (SERIF, size or 17) if serif else (SANS, size or 15)
    paras = [p for p in re.split(r"\n\s*\n", body.strip()) if p.strip()]
    return "".join(f'<p dir="auto" style="margin:0 0 16px 0;font-family:{fam};font-size:{size}px;line-height:1.65;color:{color};text-align:{align};">{inline(p)}</p>'
                   for p in paras)


def image_tag(x, ref, width, alt, link=None, radius=8, extra="", cls=None):
    cls = cls or ("full" if width >= 400 else "scale")
    tag = (f'<img src="{html.escape(x.url(ref))}" width="{width}" alt="{html.escape(alt)}" border="0" class="{cls}" '
           f'style="display:block;width:{width}px;max-width:100%;height:auto;border:0;border-radius:{radius}px;{extra}">')
    if link:
        tag = f'<a href="{html.escape(link)}" target="_blank" style="text-decoration:none;">{tag}</a>'
    return tag


def button(x, label, url, bg=None, fg="#FFFFFF", center=False):
    bg = bg or x.c["accent_text"]
    align, m = ('align="center" ', "auto") if center else ("", "0")
    return (f'<table role="presentation" {align}border="0" cellpadding="0" cellspacing="0" style="margin:4px {m} 0 {m};"><tr>'
            f'<td bgcolor="{bg}" style="background-color:{bg};border-radius:999px;padding:12px 26px;">'
            f'<a href="{html.escape(url)}" target="_blank" style="font-family:{SANS};font-size:15px;font-weight:bold;color:{fg};text-decoration:none;">{html.escape(label)}</a>'
            f'</td></tr></table>')


def byline_row(x, byline, image, words=0):
    if not byline and not image:
        return ""
    parts = [p.strip() for p in re.split(r"[;,]", byline or "", maxsplit=1)]
    name, role = parts[0], (parts[1] if len(parts) > 1 else "")
    meta = role
    if words > 250:
        meta = f"{meta} · {max(1, round(words / 220))} min read" if meta else f"{max(1, round(words / 220))} min read"
    pic = ""
    shot = x.headshot(image)
    if shot:
        src = avatar_square(x, shot) if x.preview else None
        src = src or x.url(shot)
        pic = (f'<td width="64" valign="middle" style="padding:0 14px 0 0;"><img src="{html.escape(src)}" width="64" height="64" alt="{html.escape(name)}" '
               f'style="display:block;width:64px;height:64px;border-radius:50%;border:0;"></td>')
    text = (f'<div dir="auto" style="font-family:{SANS};font-size:15px;font-weight:bold;color:{INK};line-height:1.35;">{inline(name)}</div>'
            + (f'<div dir="auto" style="font-family:{SANS};font-size:13px;color:{MUTED};line-height:1.4;">{inline(meta)}</div>' if meta else ""))
    return (f'<table role="presentation" border="0" cellpadding="0" cellspacing="0" style="margin:0 0 20px 0;"><tr>{pic}'
            f'<td valign="middle">{text}</td></tr></table>')


def word_count(body):
    return len(re.findall(r"\w+", body if isinstance(body, str) else " ".join(body)))


# ---------------------------------------------------------------- blocks
def b_header(x, issue, hdr, toc):
    a = x.p["assets"]
    top = row(image_tag(x, a["header"], CARD_W, a.get("header_alt", x.p["name"]), radius=0), pad="0", cls="")
    meta = " · ".join(p for p in (hdr["date_text"], hdr.get("hebrew_date")) if p)
    left = (eyebrow(x, f"Shabbat Shalom from {x.p['short']}")
            + f'<h1 dir="auto" class="h1" style="margin:0 0 10px 0;font-family:{SERIF};font-size:32px;line-height:1.2;font-weight:bold;color:{NAVY};">{"<br>".join(html.escape(p) for p in issue["title"].split(" - "))}</h1>'
            + f'<div style="font-family:{SANS};font-size:15px;color:{MUTED};margin:0 0 14px 0;">{html.escape(meta)}</div>')
    if hdr.get("candles"):
        left += (f'<table role="presentation" border="0" cellpadding="0" cellspacing="0"><tr><td bgcolor="{x.c["tint"]}" '
                 f'style="background-color:{x.c["tint"]};border-radius:999px;padding:7px 14px;font-family:{SANS};font-size:13px;color:{INK};">'
                 f'Candle lighting in Jerusalem&nbsp;&nbsp;<strong>{html.escape(hdr["candles"])}</strong></td></tr></table>')
    badge = ""
    if a.get("date_badge"):
        badge = (f'<td class="hide-sm" width="104" valign="top" align="right" style="padding:4px 0 0 16px;">'
                 f'{image_tag(x, a["date_badge"], 104, "Together we will win", radius=8)}</td>')
    block = (f'<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0"><tr>'
             f'<td valign="top">{left}</td>{badge}</tr></table>')
    out = top + row(block, pad=f"20px {PAD}px 26px {PAD}px")
    if len(toc) > 1:
        dot = '<span style="color:#B9B7C6;">&nbsp;&middot;</span>'
        items = " ".join(f'<span style="white-space:nowrap;">{html.escape(t)}{dot if i < len(toc) - 1 else ""}</span>' for i, t in enumerate(toc))
        out += row(f'<div style="border-top:1px solid {RULE};border-bottom:1px solid {RULE};padding:12px 0;font-family:{SANS};font-size:13px;line-height:1.7;color:{MUTED};">'
                   f'<strong style="color:{INK};">In this issue:</strong>&nbsp; {items}</div>', pad=f"0 {PAD}px")
    return out


def b_article(x, s):
    inner = eyebrow(x, s["heading"]) + h2(s["title"]) if s.get("title") else h2(s["heading"])
    inner += byline_row(x, s.get("byline"), s.get("image"), word_count(s["body"]))
    inner += body_text(s["body"])
    return row(inner)


def youtube_id(url):
    m = re.search(r"(?:youtu\.be/|v=|shorts/|embed/)([\w-]{11})", url)
    return m.group(1) if m else None


def b_video(x, s):
    inner = eyebrow(x, s["heading"]) + h2(s["title"]) if s.get("title") else h2(s["heading"])
    inner += byline_row(x, s.get("byline"), s.get("image"))
    thumb = s.get("thumbnail")
    if not thumb:
        vid = youtube_id(s["url"])
        thumb = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else None
    if thumb:
        inner += f'<div style="margin:0 0 16px 0;">{image_tag(x, thumb, INNER, "Watch: " + (s.get("byline") or s["heading"]), link=s["url"], radius=10)}</div>'
    inner += button(x, s.get("link_text", "▶  Watch the video"), s["url"])
    if s.get("body"):
        inner += '<div style="height:16px;"></div>' + body_text(s["body"])
    return row(inner)


def media_thumb(item):
    if item.get("image"):
        return item["image"]
    vid = youtube_id(item["url"])
    if vid:
        return f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg"
    if "spotify.com" in item["url"]:
        try:
            q = "https://open.spotify.com/oembed?url=" + urllib.parse.quote(item["url"].split("?")[0], safe="")
            return json.load(urllib.request.urlopen(q, timeout=20))["thumbnail_url"]
        except Exception as e:
            print(f"  ! no Spotify thumbnail for {item['url']}: {e}", file=sys.stderr)
    return None


def b_media(x, s):
    inner = h2(s.get("heading") or x.p["section_titles"]["podcasts"])
    if s.get("intro"):
        inner += body_text(s["intro"], serif=False, color=MUTED)
    # one table per item keeps Outlook from merging rows
    inner += "".join(_media_item(x, it, i) for i, it in enumerate(s["items"]))
    return row(inner)


def _media_item(x, it, i):
    th = media_thumb(it)
    speaker, _, title = it["caption"].partition(":")
    if not title:
        speaker, title = "", it["caption"]
    u = it["url"]
    kind = "Watch on YouTube" if "youtu" in u else "Listen on Spotify" if "spotify" in u else "Open"
    pic = f'<td width="96" valign="top" style="padding:0 16px 0 0;">{image_tag(x, th, 96, it["caption"], link=u, radius=8)}</td>' if th else ""
    txt = ((f'<div dir="auto" style="font-family:{SANS};font-size:13px;font-weight:bold;color:{MUTED};margin:0 0 3px 0;text-align:left;">{inline(speaker.strip())}</div>' if speaker else "")
           + f'<div dir="auto" style="font-family:{SERIF};font-size:17px;line-height:1.35;font-weight:bold;margin:0 0 6px 0;text-align:left;">'
             f'<a href="{html.escape(u)}" target="_blank" style="color:{NAVY};text-decoration:none;">{inline(title.strip())}</a></div>'
           + f'<a href="{html.escape(u)}" target="_blank" style="font-family:{SANS};font-size:13px;font-weight:bold;color:{x.c["accent_text"]};text-decoration:none;">{kind} &rarr;</a>')
    top = f"border-top:1px solid {RULE};" if i else ""
    return (f'<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0" style="{top}"><tr>'
            f'{pic}<td valign="middle" style="padding:14px 0;">{txt}</td></tr></table>')


def b_announcement(x, s):
    inner = h2(s["heading"], size=22)
    if s.get("body"):
        inner += body_text(s["body"], serif=False)
    btn = s.get("button")
    if not btn and s.get("strip"):
        btn = {"label": re.sub(r"[{}]", "", s["strip"]["text"]), "url": s["strip"]["url"]}
    if s.get("image"):
        inner += f'<div style="margin:4px 0 {18 if btn else 0}px 0;">{image_tag(x, s["image"], INNER - 48, s.get("alt") or s["heading"].replace(chr(10), " "), link=s.get("url") or (btn or {}).get("url"))}</div>'
    if btn:
        inner += button(x, btn["label"], btn["url"])
    card = (f'<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0"><tr>'
            f'<td class="card" bgcolor="{x.c["tint"]}" style="background-color:{x.c["tint"]};border-radius:12px;padding:24px;">{inner}</td></tr></table>')
    return row(card, pad=f"24px {PAD}px")


def b_birthdays(x, s):
    a = x.p["assets"]
    title = s.get("heading") or x.p["section_titles"].get("birthdays") or "Happy Birthday!"
    text = h2(title, size=22)
    for it in s["items"]:
        text += f'<p dir="auto" style="margin:0 0 6px 0;font-family:{SANS};font-size:16px;line-height:1.5;color:{INK};">{inline(it)}</p>'
    text += f'<p dir="rtl" style="margin:8px 0 0 0;font-family:{SANS};font-size:16px;color:{x.c["accent_text"]};text-align:left;">{inline(s.get("closing", "!עד מאה ועשרים"))}</p>'
    pic = f'<td class="hide-sm" width="96" valign="middle" style="padding:0 20px 0 0;">{image_tag(x, a["birthday"], 96, "Happy Birthday", radius=10)}</td>'
    card = (f'<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0"><tr>'
            f'<td class="card" bgcolor="{x.c["tint"]}" style="background-color:{x.c["tint"]};border-radius:12px;padding:24px;">'
            f'<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0"><tr>{pic}<td valign="middle">{text}</td></tr></table>'
            f'</td></tr></table>')
    return row(card, pad=f"24px {PAD}px")


def b_mazal_tov(x, s):
    inner = h2(s.get("heading") or x.p["section_titles"]["mazal_tov"])
    for it in s["items"]:
        it = {"text": it} if isinstance(it, str) else it
        inner += (f'<div dir="auto" style="border-left:3px solid {x.c["accent"]};padding:2px 0 2px 14px;margin:0 0 14px 0;'
                  f'font-family:{SANS};font-size:16px;line-height:1.5;color:{INK};">{inline(it["text"])}</div>')
        if it.get("image"):
            inner += f'<div style="margin:0 0 16px 17px;">{image_tag(x, it["image"], int(it.get("image_width", 220)), it["text"][:60])}</div>'
    return row(inner)


def b_sponsors(x, s):
    inner = h2(s.get("heading") or x.p["section_titles"]["sponsors"])
    inner += "".join(f'<p dir="auto" style="margin:0 0 12px 0;font-family:{SANS};font-size:16px;line-height:1.5;color:{INK};">{inline(it)}</p>' for it in s["items"])
    if s.get("contact"):
        ct = s["contact"]
        inner += (f'<p style="margin:16px 0 0 0;font-family:{SANS};font-size:14px;color:{MUTED};">{html.escape(ct["text"])} '
                  f'<a href="mailto:{html.escape(ct["email"])}" style="color:{x.c["accent_text"]};font-weight:bold;">{html.escape(ct["name"])}</a></p>')
    return row(inner)


def b_photos(x, s):
    inner = h2(s.get("heading") or x.p["section_titles"]["photos"])
    half = (INNER - 10) // 2
    for n, album in enumerate(s["albums"]):
        cap = album.get("caption") or "Photo"
        if album.get("caption"):
            inner += (f'<div dir="auto" style="font-family:{SANS};font-size:16px;font-weight:bold;color:{INK};'
                      f'margin:{8 if n else 0}px 0 12px 0;">{inline(album["caption"])}</div>')
        pend = []

        def flush():
            nonlocal inner
            if len(pend) == 2:
                inner += ('<table role="presentation" class="pair" width="100%" border="0" cellpadding="0" cellspacing="0" style="margin:0 0 10px 0;"><tr>'
                          f'<td class="stack" width="{half}" valign="top" style="padding:0 5px 0 0;">{image_tag(x, pend[0], half, cap, cls="full")}</td>'
                          f'<td class="stack" width="{half}" valign="top" style="padding:0 0 0 5px;">{image_tag(x, pend[1], half, cap, cls="full")}</td>'
                          '</tr></table>')
            elif len(pend) == 1:
                inner += f'<div style="margin:0 0 10px 0;">{image_tag(x, pend[0], INNER, cap)}</div>'
            pend.clear()

        for p in album["photos"]:
            w, h = img_dims(p, x.base)
            if w >= h * 1.05:
                flush()
                inner += f'<div style="margin:0 0 10px 0;">{image_tag(x, p, INNER, cap)}</div>'
            else:
                pend.append(p)
                if len(pend) == 2:
                    flush()
        flush()
        inner += '<div style="height:14px;line-height:14px;font-size:0;">&nbsp;</div>'
    return row(inner)


def b_text(x, s):
    inner = h2(s["heading"]) if s.get("heading") else ""
    inner += byline_row(x, s.get("byline"), s.get("image"))
    return row(inner + body_text(s["body"], serif=s.get("serif", True)))


def b_footer(x):
    p = x.p
    d = p["donate"]
    lines = list(d["blurb"])
    band = ""
    if lines:
        band += f'<div style="font-family:{SERIF};font-size:22px;line-height:1.3;font-weight:bold;color:#FFFFFF;margin:0 0 8px 0;">{html.escape(lines[0])}</div>'
        band += "".join(f'<div style="font-family:{SANS};font-size:15px;line-height:1.5;color:#D5D8EE;">{html.escape(l)}</div>' for l in lines[1:])
        band += '<div style="height:18px;line-height:18px;font-size:0;">&nbsp;</div>'
    band += button(x, d["label"], d["url"], bg=GOLD, fg=NAVY, center=True)
    band = f'<table role="presentation" align="center" border="0" cellpadding="0" cellspacing="0"><tr><td align="center" style="text-align:center;">{band}</td></tr></table>'
    out = row(band, bg=NAVY, pad=f"32px {PAD}px", align="center")

    def label(t):
        return (f'<div style="font-family:{SANS};font-size:12px;font-weight:bold;letter-spacing:1.5px;text-transform:uppercase;'
                f'color:{x.c["accent_text"]};margin:0 0 12px 0;">{t}</div>')

    def person(s):
        name, role, org, email = s
        role, org = html.escape(role), html.escape(org)
        role_org = f"{role} {org}" if role.endswith(" of") else f"{role}<br>{org}"
        return (f'<p style="margin:0 0 14px 0;font-family:{SANS};font-size:12px;line-height:1.5;color:{MUTED};">'
                f'<strong style="color:{INK};font-size:13px;">{html.escape(name)}</strong><br>{role_org}<br>'
                f'<a href="mailto:{html.escape(email)}" style="color:{x.c["accent_text"]};text-decoration:none;">{html.escape(email)}</a></p>')
    half = (len(p["staff"]) + 1) // 2
    staff = (f'<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0"><tr>'
             f'<td class="stack" width="50%" valign="top" style="padding:0 10px 0 0;">{"".join(person(s) for s in p["staff"][:half])}</td>'
             f'<td class="stack" width="50%" valign="top">{"".join(person(s) for s in p["staff"][half:])}</td></tr></table>')
    ct = p["contact"]
    tel = lambda n: f'<a href="tel:{n}" style="color:{MUTED};text-decoration:none;">{n}</a>'
    contact = (f'<p style="margin:0;font-family:{SANS};font-size:12px;line-height:1.7;color:{MUTED};">'
               f'<strong style="color:{INK};font-size:13px;">{html.escape(ct["name"])}</strong><br>'
               f'Israel: {html.escape(ct["israel"])} · {" · ".join(tel(n) for n in ct["israel_phones"])}<br>'
               f'New York: {html.escape(ct["ny"])} · {tel(ct["ny_phone"])}<br>'
               f'<a href="mailto:{ct["email"]}" style="color:{x.c["accent_text"]};text-decoration:none;">{ct["email"]}</a> · '
               f'<a href="{ct["website_url"]}" target="_blank" style="color:{x.c["accent_text"]};text-decoration:none;">{ct["website"]}</a></p>')
    about = ("TVA is one of the many programs under the umbrella of Bnei Akiva, the pioneering Religious Zionist youth movement, "
             "which has more than 50 years of experience running programs for young men and women in their year in Israel. "
             "Bnei Akiva is your family in Israel. In addition to Israel programs, Bnei Akiva runs summer camps for thousands of young "
             "people, and year-round programs in dozens of communities in North America and across the world. On TVA, you will have "
             "the remarkable opportunity to connect with Bnei Akiva students from across the world - from the UK, Australia, South "
             "Africa, Germany, France, South America, and more!")
    logo = image_tag(x, p["assets"]["about_logo"], 64, "Bnei Akiva", radius=0)
    about_t = (f'<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0"><tr>'
               f'<td width="64" valign="top" style="padding:0 16px 0 0;">{logo}</td>'
               f'<td valign="top" style="font-family:{SANS};font-size:12px;line-height:1.6;color:{MUTED};">{about}</td></tr></table>')
    sep = f'<div style="height:1px;line-height:1px;font-size:0;background-color:{RULE};margin:22px 0;">&nbsp;</div>'
    social = ""
    if p.get("social"):
        social = sep + "".join(f'<a href="{u}" target="_blank" style="text-decoration:none;"><img src="{i}" width="28" height="28" alt="{n}" border="0" style="display:inline-block;width:28px;height:28px;margin:0 6px 0 0;"></a>' for n, u, i in p["social"])
    out += row(label("Our staff") + staff + sep + label("Contact us") + contact + sep + label("About Bnei Akiva") + about_t + social,
               bg=FOOT, pad=f"32px {PAD}px")
    return out


CARDS = {"announcement", "birthdays"}

BLOCKS = {"article": b_article, "video": b_video, "media": b_media, "podcasts": b_media,
          "announcement": b_announcement, "birthdays": b_birthdays, "mazal_tov": b_mazal_tov,
          "sponsors": b_sponsors, "photos": b_photos, "text": b_text}


def toc_label(x, s):
    t = s["type"]
    titles = x.p["section_titles"]
    if t in ("article", "video", "text"):
        return s.get("heading")
    return {"media": s.get("heading") or titles["podcasts"], "podcasts": s.get("heading") or titles["podcasts"],
            "photos": s.get("heading") or titles["photos"], "mazal_tov": s.get("heading") or titles["mazal_tov"],
            "birthdays": "Birthdays", "sponsors": "Sponsors",
            "announcement": "Announcements"}.get(t)


# ---------------------------------------------------------------- document
def build(issue, base, preview=False):
    prog = json.load(open(PROGRAMS / f"{issue['program'].lower()}.json"))
    x = Ctx(prog, base, preview)
    friday = dt.date.fromisoformat(issue["date"])
    hdr = {}
    try:
        hdr = hebcal_header(friday)
    except Exception as e:
        print(f"  ! Hebcal lookup failed ({e}); header fields must be given in issue.json", file=sys.stderr)
    parsha = issue.get("parsha") or (f"Parshat {hdr['parsha']}" if hdr.get("parsha") else None)
    if not issue.get("title"):
        if not parsha:
            sys.exit(f"No parsha this Shabbat ({', '.join(hdr.get('holidays', [])) or 'unknown'}): set \"title\" (and \"parsha\" for the subject) in issue.json")
        issue["title"] = f"{hdr['special']} - {parsha}" if hdr.get("special") else f"Shabbat {parsha}"
    day = ordinal(friday.day) if prog.get("date_ordinal") else str(friday.day)
    hdr["date_text"] = f"{friday.strftime('%B')} {day}, {friday.year}"
    hdr["date_line"] = issue.get("date_line") or " | ".join(p for p in (hdr["date_text"], hdr.get("hebrew_date")) if p)
    hdr["candles"] = issue.get("candles") or hdr.get("candles")
    fields = {"parsha": parsha or issue["title"], "date": friday.isoformat(), "hebrew_year": hdr.get("hebrew_year", "")}
    subject = issue.get("subject") or prog["subject"].format(**fields)
    preheader = issue.get("preheader") or f"{issue['title']} | {hdr['date_line']}"
    campaign_name = " ".join(prog["campaign_name"].format(**fields).split())

    sections = [s for s in issue["sections"] if not s.get("skip")]
    for s in sections:
        if s["type"] not in BLOCKS:
            sys.exit(f"Unknown section type {s['type']!r}; use one of {sorted(BLOCKS)}")
    toc = []
    for s in sections:
        lab = toc_label(x, s)
        if lab and lab not in toc:
            toc.append(lab)
    body = b_header(x, issue, hdr, toc)
    prev = None
    for s in sections:
        # hairline between plain sections; tinted cards carry their own separation
        if prev and prev not in CARDS and s["type"] not in CARDS:
            body += rule()
        body += BLOCKS[s["type"]](x, s)
        prev = s["type"]
    body += '<div style="height:12px;line-height:12px;font-size:0;">&nbsp;</div>' + b_footer(x)

    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="X-UA-Compatible" content="IE=edge"><meta name="color-scheme" content="light"><meta name="supported-color-schemes" content="light">
<title>{html.escape(subject)}</title>
<style>
body {{ margin:0; padding:0; -webkit-text-size-adjust:100%; -ms-text-size-adjust:100%; }}
table {{ border-collapse:collapse; }}
img {{ -ms-interpolation-mode:bicubic; }}
a[x-apple-data-detectors] {{ color:inherit !important; text-decoration:none !important; }}
@media only screen and (max-width:640px) {{
  .outer {{ padding:0 !important; }}
  .shell {{ width:100% !important; border-radius:0 !important; }}
  .px {{ padding-left:20px !important; padding-right:20px !important; }}
  .card {{ padding:20px !important; }}
  .h1 {{ font-size:27px !important; }}
  .stack {{ display:block !important; width:100% !important; padding:0 0 10px 0 !important; }}
  .full {{ width:100% !important; height:auto !important; }}
  .scale {{ max-width:100% !important; height:auto !important; }}
  .hide-sm {{ display:none !important; }}
}}
</style></head>
<body style="margin:0;padding:0;background-color:{PAGE};">
<div style="display:none;font-size:1px;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;color:transparent;">{html.escape(preheader)}</div>
<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0" bgcolor="{PAGE}" style="background-color:{PAGE};"><tr><td class="outer" align="center" style="padding:24px 12px;">
<table role="presentation" class="shell" width="{CARD_W}" border="0" cellpadding="0" cellspacing="0" bgcolor="#FFFFFF" style="width:{CARD_W}px;background-color:#FFFFFF;border-radius:12px;overflow:hidden;"><tr>
<td style="padding:0;">
{body}
</td></tr></table>
</td></tr></table>
[[trackingImage]]
</body></html>
"""
    # Constant Contact rejects these pairs anywhere in the source; neutralise any that came in with content.
    doc = doc.replace("${", "&#36;{").replace("[#", "&#91;#").replace("<@", "&lt;@")
    return doc, subject, preheader, campaign_name, x.local_refs


def check(doc, preview, local_refs):
    problems, warnings = [], []
    n = len(doc.encode("utf-8"))
    if n > MAX_BYTES:
        problems.append(f"{n/1024:.0f} KB is over Constant Contact's 400 KB limit")
    elif n > GMAIL_CLIP:
        warnings.append(f"{n/1024:.0f} KB: Gmail will clip this email (limit ~102 KB). Trim photos/sections.")
    for pair in ("[#", "${", "<@"):
        if pair in doc:
            problems.append(f"forbidden character pair {pair!r} present")
    b = doc.find("<body"), doc.find("[[trackingImage]]"), doc.find("</body>")
    if not (b[0] < b[1] < b[2]):
        problems.append("[[trackingImage]] is not inside <body>")
    if re.search(r"<img(?![^>]*\balt=)", doc):
        problems.append("an <img> has no alt text")
    if not preview and local_refs:
        problems.append(f"{len(local_refs)} image(s) still point at local files (run images.py first): {local_refs[:3]}")
    return n, problems, warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("issue", help="issue.json (or issue.hosted.json from images.py)")
    ap.add_argument("--preview", action="store_true", help="local preview using file:// images")
    a = ap.parse_args()
    path = Path(a.issue).resolve()
    issue = json.load(open(path))
    base = Path(issue.get("_base", path.parent))
    doc, subject, pre, cname, refs = build(issue, base, a.preview)
    out = path.parent / "out"
    out.mkdir(exist_ok=True)
    f = out / ("preview.html" if a.preview else "email.html")
    f.write_text(doc, encoding="utf-8")
    (out / "meta.json").write_text(json.dumps({"subject": subject, "preheader": pre, "campaign_name": cname, "program": issue["program"], "date": issue["date"]}, indent=2, ensure_ascii=False))
    n, problems, warnings = check(doc, a.preview, refs)
    print(f"wrote {f}  ({n/1024:.0f} KB)\nsubject:   {subject}\npreheader: {pre}")
    for w in warnings:
        print("WARN ", w)
    for p in problems:
        print("FAIL ", p)
    if not problems:
        print("checks: OK" + (" (preview: local images allowed)" if a.preview else ""))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
