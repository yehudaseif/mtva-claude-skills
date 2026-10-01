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
FONT = "Helvetica,Arial,sans-serif"
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


def paragraphs(body, color, size=14, align="left"):
    if isinstance(body, list):
        body = "\n\n".join(body)
    paras = [p for p in re.split(r"\n\s*\n", body.strip()) if p.strip()]
    return "".join(
        f'<p dir="auto" style="margin:0 0 14px 0;font-family:{FONT};font-size:{size}px;line-height:1.35;color:{color};text-align:{align};">{inline(p)}</p>'
        for p in paras)


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


# ---------------------------------------------------------------- blocks
def row(inner, bg="#FFFFFF", pad="10px 20px", align="left"):
    return (f'<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0" bgcolor="{bg}" style="background-color:{bg};">'
            f'<tr><td align="{align}" style="padding:{pad};">{inner}</td></tr></table>')


def divider(x):
    return row(f'<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0"><tr><td height="2" style="height:2px;line-height:2px;font-size:0;background-color:{x.c["frame"]};">&nbsp;</td></tr></table>',
               pad="10px 20px")


def section_bar(x, heading, byline=None):
    inner = f'<div style="font-family:{FONT};font-size:24px;font-weight:bold;color:#FFFFFF;line-height:1.2;">{inline(heading)}</div>'
    if byline:
        inner += f'<div style="font-family:{FONT};font-size:16px;font-weight:bold;color:#FFFFFF;line-height:1.3;">{inline(byline)}</div>'
    return row(inner, bg=x.c["section_bar"], pad="10px 20px")


def feature_bar(x, heading, bg=None):
    inner = f'<div style="font-family:{FONT};font-size:22px;font-weight:bold;color:#FFFFFF;line-height:1.3;text-align:center;">{inline(heading)}</div>'
    return row(inner, bg=bg or x.c["feature_bar"], pad="10px 20px", align="center")


def image_tag(x, ref, width, alt, link=None, extra=""):
    cls = "full" if width >= 500 else "scale"
    tag = (f'<img src="{html.escape(x.url(ref))}" width="{width}" alt="{html.escape(alt)}" border="0" class="{cls}" '
           f'style="display:block;width:{width}px;max-width:100%;height:auto;border:0;{extra}">')
    if link:
        tag = f'<a href="{html.escape(link)}" target="_blank" style="text-decoration:none;">{tag}</a>'
    return tag


def b_header(x, issue, hdr):
    c, a = x.c, x.p["assets"]
    top = row(image_tag(x, a["header"], 600, a.get("header_alt", x.p["name"])), bg=c["frame"], pad="0")
    lines = [issue["title"], hdr["date_line"]]
    if hdr.get("candles"):
        lines.append(f"Hadlakat Neirot in Yerushalayim: {hdr['candles']}")
    text = "".join(
        f'<div style="font-family:{FONT};font-size:{23 if i == 0 else 19}px;font-weight:bold;color:#FFFFFF;line-height:1.15;">{html.escape(l)}</div>'
        for i, l in enumerate(lines))
    badge = image_tag(x, a["date_badge"], a.get("date_badge_width", 130), "Together we will win")
    band = (f'<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0"><tr>'
            f'<td class="stack" align="center" valign="middle" style="padding:0 10px 0 0;text-align:center;">{text}</td>'
            f'<td class="stack" width="{a.get("date_badge_width", 130)}" align="right" valign="middle" style="padding:0;">{badge}</td>'
            f'</tr></table>')
    gap = '<div style="height:16px;line-height:16px;font-size:0;">&nbsp;</div>'
    return top + gap + row(band, bg=c["date_band"], pad="12px 20px") + gap


def b_article(x, s):
    out = section_bar(x, s["heading"], s.get("byline"))
    shot = x.headshot(s.get("image"))
    inner = ""
    if s.get("title"):
        inner += f'<p dir="auto" style="margin:0 0 12px 0;font-family:{FONT};font-size:16px;font-weight:bold;color:{x.c["text"]};text-align:center;">{inline(s["title"])}</p>'
    if shot:
        side = s.get("image_side", "right")
        w = int(s.get("image_width", 160))
        pad = "0 0 10px 15px" if side == "right" else "0 15px 10px 0"
        inner = (f'<table role="presentation" align="{side}" border="0" cellpadding="0" cellspacing="0" class="float-img" style="float:{side};">'
                 f'<tr><td style="padding:{pad};">{image_tag(x, shot, w, s.get("byline") or s["heading"])}</td></tr></table>') + inner
    inner += paragraphs(s["body"], x.c["text"])
    return out + row(inner, pad="12px 20px 2px 20px") + divider(x)


def youtube_id(url):
    m = re.search(r"(?:youtu\.be/|v=|shorts/|embed/)([\w-]{11})", url)
    return m.group(1) if m else None


def b_video(x, s):
    out = section_bar(x, s["heading"], s.get("byline"))
    thumb = s.get("thumbnail")
    if not thumb:
        vid = youtube_id(s["url"])
        thumb = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else None
    inner = ""
    if thumb:
        inner += f'<div style="text-align:center;">{image_tag(x, thumb, 520, "Watch: " + (s.get("byline") or s["heading"]), link=s["url"], extra="margin:0 auto;")}</div>'
    label = s.get("link_text", "▶ Click to watch")
    inner += (f'<p style="margin:10px 0 4px 0;font-family:{FONT};font-size:14px;font-weight:bold;text-align:center;">'
              f'<a href="{html.escape(s["url"])}" target="_blank" style="color:{x.c["text"]};">{html.escape(label)}</a></p>')
    if s.get("body"):
        inner += paragraphs(s["body"], x.c["text"])
    return out + row(inner, pad="12px 20px 6px 20px") + divider(x)


def media_thumb(item):
    if item.get("image"):
        return item["image"]
    vid = youtube_id(item["url"])
    if vid:
        return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
    if "spotify.com" in item["url"]:
        try:
            q = "https://open.spotify.com/oembed?url=" + urllib.parse.quote(item["url"].split("?")[0], safe="")
            return json.load(urllib.request.urlopen(q, timeout=20))["thumbnail_url"]
        except Exception as e:
            print(f"  ! no Spotify thumbnail for {item['url']}: {e}", file=sys.stderr)
    return None


def b_media(x, s):
    out = feature_bar(x, s.get("heading") or x.p["section_titles"]["podcasts"])
    inner = paragraphs(s["intro"], x.c["text"], align="center") if s.get("intro") else ""
    items = s["items"]
    cells = []
    for it in items:
        th = media_thumb(it)
        pic = image_tag(x, th, 240, it["caption"], link=it["url"], extra="margin:0 auto;") if th else ""
        cap = (f'<p dir="auto" style="margin:8px 0 0 0;font-family:{FONT};font-size:13px;font-weight:bold;color:{x.c["text"]};text-align:center;">'
               f'<a href="{html.escape(it["url"])}" target="_blank" style="color:{x.c["text"]};text-decoration:none;">{inline(it["caption"])}</a></p>')
        cells.append(f'<div style="text-align:center;">{pic}</div>{cap}')
    rows = ""
    for i in range(0, len(cells), 2):
        pair = cells[i:i + 2]
        if len(pair) == 1:
            rows += f'<tr><td colspan="2" align="center" valign="top" style="padding:10px 0;"><table role="presentation" width="270" align="center" border="0" cellpadding="0" cellspacing="0"><tr><td>{pair[0]}</td></tr></table></td></tr>'
        else:
            rows += "<tr>" + "".join(f'<td class="stack" width="50%" align="center" valign="top" style="padding:10px 5px;">{c}</td>' for c in pair) + "</tr>"
    inner += f'<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">{rows}</table>'
    return out + row(inner, pad="12px 20px") + divider(x)


def b_announcement(x, s):
    out = feature_bar(x, s["heading"])
    if s.get("strip"):
        st = s["strip"]
        t = html.escape(st["text"], quote=False)
        link = f'<a href="{html.escape(st["url"])}" target="_blank" style="color:#FFFFFF;font-weight:bold;text-decoration:underline;">'
        t = re.sub(r"\{(.+?)\}", lambda m: f"{link}{m.group(1)}</a>", t) if "{" in t else f"{link}{t}</a>"
        out += row(f'<div style="font-family:{FONT};font-size:16px;font-weight:bold;color:{x.c["text"]};text-align:center;">{t}</div>',
                   bg=x.c["link_strip"], pad="8px 20px", align="center")
    inner = ""
    if s.get("body"):
        inner += paragraphs(s["body"], x.c["text"], align=s.get("align", "center"))
    if s.get("image"):
        inner += f'<div style="text-align:center;">{image_tag(x, s["image"], 560, s.get("alt") or s["heading"].replace(chr(10), " "), link=s.get("url"), extra="margin:0 auto;")}</div>'
    return out + row(inner, pad="12px 20px") + divider(x)


def b_birthdays(x, s):
    a, title = x.p["assets"], s.get("heading", x.p["section_titles"].get("birthdays"))
    text = ""
    if title:
        text += f'<div style="font-family:{FONT};font-size:24px;font-weight:bold;color:#FFFFFF;text-align:center;margin-bottom:6px;">{inline(title)}</div>'
    for it in s["items"]:
        text += f'<p dir="auto" style="margin:0 0 6px 0;font-family:{FONT};font-size:15px;color:#FFFFFF;text-align:center;line-height:1.3;">{inline(it)}</p>'
    text += f'<p dir="rtl" style="margin:6px 0 0 0;font-family:{FONT};font-size:16px;color:#FFFFFF;text-align:center;">{inline(s.get("closing", "!עד מאה ועשרים"))}</p>'
    pic = image_tag(x, a["birthday"], a.get("birthday_width", 136), "Happy Birthday")
    inner = (f'<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0"><tr>'
             f'<td class="stack" width="{a.get("birthday_width", 136)}" valign="middle" style="padding:0 15px 0 0;">{pic}</td>'
             f'<td class="stack" valign="middle">{text}</td></tr></table>')
    return row(inner, bg=x.c["birthday_bg"], pad="15px 20px") + divider(x)


def b_mazal_tov(x, s):
    out = feature_bar(x, s.get("heading") or x.p["section_titles"]["mazal_tov"])
    inner = ""
    for it in s["items"]:
        it = {"text": it} if isinstance(it, str) else it
        inner += f'<p dir="auto" style="margin:0 0 12px 0;font-family:{FONT};font-size:15px;color:{x.c["text"]};line-height:1.35;">{inline(it["text"])}</p>'
        if it.get("image"):
            inner += f'<div style="text-align:center;margin:0 0 12px 0;">{image_tag(x, it["image"], int(it.get("image_width", 200)), it["text"][:60], extra="margin:0 auto;")}</div>'
    return out + row(inner, pad="12px 20px") + divider(x)


def b_sponsors(x, s):
    out = feature_bar(x, s.get("heading") or x.p["section_titles"]["sponsors"], bg=x.c["sponsors_bar"])
    inner = "".join(
        f'<p dir="auto" style="margin:0 0 14px 0;font-family:{FONT};font-size:16px;color:{x.c["text"]};text-align:center;line-height:1.3;">{inline(it)}</p>'
        for it in s["items"])
    if s.get("contact"):
        ct = s["contact"]
        inner += (f'<p style="margin:6px 0 0 0;font-family:{FONT};font-size:14px;font-style:italic;color:{x.c["text"]};text-align:center;">{html.escape(ct["text"])} '
                  f'<a href="mailto:{html.escape(ct["email"])}" style="color:{x.c["footer_heading"]};">{html.escape(ct["name"])}</a></p>')
    return out + row(inner, pad="14px 20px") + divider(x)


def b_photos(x, s):
    out = feature_bar(x, s.get("heading") or x.p["section_titles"]["photos"])
    inner = ""
    for album in s["albums"]:
        if album.get("caption"):
            inner += f'<p dir="auto" style="margin:14px 0 10px 0;font-family:{FONT};font-size:16px;font-weight:bold;color:{x.c["text"]};text-align:center;">{inline(album["caption"])}</p>'
        photos = album["photos"]
        pend = []  # portraits waiting for a partner

        def flush_pair():
            nonlocal inner
            if len(pend) == 2:
                inner += ('<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0"><tr>'
                          + "".join(f'<td class="stack" width="50%" align="center" valign="top" style="padding:0 5px 10px 5px;">{image_tag(x, p, 270, album.get("caption") or "Photo", extra="margin:0 auto;")}</td>' for p in pend)
                          + '</tr></table>')
            elif len(pend) == 1:
                inner += f'<div style="text-align:center;padding:0 0 10px 0;">{image_tag(x, pend[0], 320, album.get("caption") or "Photo", extra="margin:0 auto;")}</div>'
            pend.clear()

        for p in photos:
            w, h = img_dims(p, x.base)
            if w >= h * 1.05:
                flush_pair()
                inner += f'<div style="text-align:center;padding:0 0 10px 0;">{image_tag(x, p, 560, album.get("caption") or "Photo", extra="margin:0 auto;")}</div>'
            else:
                pend.append(p)
                if len(pend) == 2:
                    flush_pair()
        flush_pair()
    return out + row(inner, pad="0 20px 10px 20px") + divider(x)


def b_text(x, s):
    out = section_bar(x, s["heading"], s.get("byline")) if s.get("heading") else ""
    return out + row(paragraphs(s["body"], x.c["text"], align=s.get("align", "left")), pad="12px 20px 2px 20px") + divider(x)


def b_footer(x):
    p, c = x.p, x.c
    d = p["donate"]
    blurb = "".join(f'<p style="margin:0 0 4px 0;font-family:{FONT};font-size:14px;color:{c["text"]};text-align:center;">{html.escape(l)}</p>' for l in d["blurb"])
    button = (f'<table role="presentation" align="center" border="0" cellpadding="0" cellspacing="0" style="margin:10px auto 0 auto;"><tr>'
              f'<td bgcolor="{c["button"]}" style="background-color:{c["button"]};border-radius:2px;padding:10px 24px;">'
              f'<a href="{html.escape(d["url"])}" target="_blank" style="font-family:{FONT};font-size:14px;font-weight:bold;color:#FFFFFF;text-decoration:none;">{html.escape(d["label"])}</a></td></tr></table>')
    out = row(blurb + button, pad="16px 20px", align="center") + divider(x)

    def h(t):
        return f'<div style="font-family:{FONT};font-size:22px;font-weight:bold;color:{c["footer_heading"]};margin:0 0 10px 0;">{t}</div>'

    def person(s):
        name, role, org, email = s
        return (f'<p style="margin:0 0 10px 0;font-family:{FONT};font-size:11px;line-height:1.35;color:{c["text"]};">'
                f'<strong>{html.escape(name)}</strong><br>{html.escape(role)}<br>{html.escape(org)}<br>'
                f'<a href="mailto:{html.escape(email)}" style="color:{c["text"]};">{html.escape(email)}</a></p>')
    half = (len(p["staff"]) + 1) // 2
    staff = (f'<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0"><tr>'
             f'<td class="stack" width="50%" valign="top">{"".join(person(s) for s in p["staff"][:half])}</td>'
             f'<td class="stack" width="50%" valign="top">{"".join(person(s) for s in p["staff"][half:])}</td></tr></table>')
    out += row(h("OUR STAFF") + staff, pad="14px 20px 4px 20px") + divider(x)

    ct = p["contact"]
    tel = lambda n: f'<a href="tel:{n}" style="color:{c["text"]};text-decoration:none;">{n}</a>'
    contact = (f'<p style="margin:0;font-family:{FONT};font-size:12px;line-height:1.5;color:{c["text"]};">'
               f'<strong style="font-size:14px;">{html.escape(ct["name"])}</strong><br>'
               f'<strong>Israel Address &amp; Phone:</strong> {html.escape(ct["israel"])} | {" | ".join(tel(n) for n in ct["israel_phones"])}<br>'
               f'<strong>NY Office Address &amp; Phone:</strong> {html.escape(ct["ny"])} | {tel(ct["ny_phone"])}<br>'
               f'<strong>Email:</strong> <a href="mailto:{ct["email"]}" style="color:{c["text"]};">{ct["email"]}</a> | '
               f'<strong>Website:</strong> <a href="{ct["website_url"]}" target="_blank" style="color:{c["text"]};">{ct["website"]}</a></p>')
    out += row(h("CONTACT US") + contact, pad="14px 20px") + divider(x)

    about = ("TVA is one of the many programs under the umbrella of Bnei Akiva, the pioneering Religious Zionist youth movement, "
             "which has more than 50 years of experience running programs for young men and women in their year in Israel.",
             "Bnei Akiva is your family in Israel. In addition to Israel programs, Bnei Akiva runs summer camps for thousands of young "
             "people, and year-round programs in dozens of communities in North America and across the world. On TVA, you will have "
             "the remarkable opportunity to connect with Bnei Akiva students from across the world - from the UK, Australia, South "
             "Africa, Germany, France, South America, and more!")
    atext = "".join(f'<p style="margin:0 0 8px 0;font-family:{FONT};font-size:11px;line-height:1.4;color:{c["text"]};">{t}</p>' for t in about)
    logo = image_tag(x, p["assets"]["about_logo"], 98, "Bnei Akiva")
    out += row(h("ABOUT BNEI AKIVA") + f'<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0"><tr>'
               f'<td class="stack" width="98" valign="middle" style="padding:0 15px 0 0;">{logo}</td><td class="stack" valign="middle">{atext}</td></tr></table>',
               pad="14px 20px")
    if p.get("social"):
        icons = "".join(f'<a href="{u}" target="_blank" style="text-decoration:none;"><img src="{i}" width="32" alt="{n}" border="0" style="display:inline-block;width:32px;height:32px;margin:0 4px;"></a>' for n, u, i in p["social"])
        out += row(f'<div style="font-family:{FONT};font-size:12px;color:#FFFFFF;margin-bottom:6px;">STAY CONNECTED</div>{icons}', bg=c["frame"], pad="10px 20px", align="center")
    return out


BLOCKS = {"article": b_article, "video": b_video, "media": b_media, "podcasts": b_media,
          "announcement": b_announcement, "birthdays": b_birthdays, "mazal_tov": b_mazal_tov,
          "sponsors": b_sponsors, "photos": b_photos, "text": b_text}


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
    hdr["date_line"] = issue.get("date_line") or f"{friday.strftime('%B')} {day}, {friday.year} | {hdr.get('hebrew_date', '')}".rstrip(" |")
    hdr["candles"] = issue.get("candles") or hdr.get("candles")
    fields = {"parsha": parsha or issue["title"], "date": friday.isoformat(), "hebrew_year": hdr.get("hebrew_year", "")}
    subject = issue.get("subject") or prog["subject"].format(**fields)
    preheader = issue.get("preheader") or f"{issue['title']} | {hdr['date_line']}"
    campaign_name = " ".join(prog["campaign_name"].format(**fields).split())

    body = b_header(x, issue, hdr)
    for s in issue["sections"]:
        if s.get("skip"):
            continue
        if s["type"] not in BLOCKS:
            sys.exit(f"Unknown section type {s['type']!r}; use one of {sorted(BLOCKS)}")
        body += BLOCKS[s["type"]](x, s)
    body += b_footer(x)

    c = prog["colors"]
    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="X-UA-Compatible" content="IE=edge"><title>{html.escape(subject)}</title>
<style>
body {{ margin:0; padding:0; -webkit-text-size-adjust:100%; -ms-text-size-adjust:100%; }}
table {{ border-collapse:collapse; }}
img {{ -ms-interpolation-mode:bicubic; }}
a[x-apple-data-detectors] {{ color:inherit !important; text-decoration:none !important; }}
@media only screen and (max-width:640px) {{
  .shell {{ width:100% !important; }}
  .stack {{ display:block !important; width:100% !important; padding-left:0 !important; padding-right:0 !important; text-align:center !important; }}
  .full {{ width:100% !important; height:auto !important; }}
  .scale {{ max-width:100% !important; height:auto !important; margin-left:auto !important; margin-right:auto !important; }}
  .float-img {{ float:none !important; width:100% !important; }}
  .float-img td {{ padding:0 0 12px 0 !important; text-align:center !important; }}
}}
</style></head>
<body style="margin:0;padding:0;background-color:{c['page']};">
<div style="display:none;font-size:1px;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;color:transparent;">{html.escape(preheader)}</div>
<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0" bgcolor="{c['page']}" style="background-color:{c['page']};"><tr><td align="center" style="padding:15px 10px;">
<table role="presentation" class="shell" width="620" border="0" cellpadding="0" cellspacing="0" style="width:620px;"><tr>
<td bgcolor="#FFFFFF" style="background-color:#FFFFFF;border:10px solid {c['frame']};">
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
