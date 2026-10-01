#!/usr/bin/env python3
"""Resize every local image an issue uses, host it, and write issue.hosted.json.

    python3 images.py WEEK/MTVA/issue.json            # resize + upload + verify
    python3 images.py WEEK/MTVA/issue.json --dry-run  # resize only, show what would upload

Constant Contact's API cannot upload images, and custom-code emails need every
image at a public https URL. The host is set in ~/.config/tva-newsletter/config.json
under "image_host":

  {"type": "r2", "account_id": "...", "bucket": "...", "access_key_id": "...",
   "secret_access_key": "...", "public_base_url": "https://pub-xxxx.r2.dev", "prefix": "newsletter"}

  {"type": "manual"}   -> writes out/img/ + out/upload-urls.json. Upload the files to the
                          Constant Contact Library, paste each file's URL into the JSON,
                          and run this script again.

Needs Pillow (pip install pillow).
"""
import argparse, datetime as dt, hashlib, hmac, io, json, re, sys, urllib.error, urllib.request
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageOps
except ImportError:
    sys.exit("Pillow is required: pip3 install pillow")

CONFIG = Path.home() / ".config" / "tva-newsletter" / "config.json"
PROGRAMS = Path(__file__).resolve().parent.parent / "programs"
# max pixel width per role (2x the display width, for sharp phones)
WIDTH = {"photo": 1080, "flyer": 1000, "avatar": 240, "mazal": 440, "thumb": 200, "video": 1080}


def is_local(ref, known):
    src = ref["src"] if isinstance(ref, dict) else ref
    return isinstance(src, str) and not src.startswith("http") and src not in known


def walk(issue):
    """Yield (container, key, role) for every image slot in the issue."""
    for s in issue["sections"]:
        t = s["type"]
        if t in ("article", "video", "text") and s.get("image"):
            yield s, "image", "avatar"
        if t == "announcement" and s.get("image"):
            yield s, "image", "flyer"
        if t == "video" and s.get("thumbnail"):
            yield s, "thumbnail", "video"
        if t in ("media", "podcasts"):
            for it in s["items"]:
                if it.get("image"):
                    yield it, "image", "thumb"
        if t == "mazal_tov":
            for i, it in enumerate(s["items"]):
                if isinstance(it, dict) and it.get("image"):
                    yield it, "image", "mazal"
        if t == "photos":
            for album in s["albums"]:
                for i in range(len(album["photos"])):
                    yield album["photos"], i, "photo"


def play_overlay(im):
    """Draw a YouTube-style play button so a video thumbnail reads as a video."""
    im = im.convert("RGB")
    w, h = im.size
    d = ImageDraw.Draw(im, "RGBA")
    r = int(min(w, h) * 0.13)
    cx, cy = w // 2, h // 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, 0, 0, 140))
    d.polygon([(cx - r * 0.35, cy - r * 0.55), (cx - r * 0.35, cy + r * 0.55), (cx + r * 0.6, cy)], fill=(255, 255, 255, 235))
    return im


def prepare(path, role):
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", im.size, "white")
            im = im.convert("RGBA")
            bg.paste(im, mask=im.split()[-1])
            im = bg
        im = im.convert("RGB")
        if role == "avatar":  # square, biased toward the top where faces are
            side = min(im.size)
            top = int((im.height - side) * 0.2)
            left = (im.width - side) // 2
            im = im.crop((left, top, left + side, top + side))
        if im.width > WIDTH[role]:
            im = im.resize((WIDTH[role], round(im.height * WIDTH[role] / im.width)), Image.LANCZOS)
        if role == "video":
            im = play_overlay(im)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85 if role == "flyer" else 78, optimize=True, progressive=True)
        return buf.getvalue(), im.size


def youtube_thumb(url):
    m = re.search(r"(?:youtu\.be/|v=|shorts/|embed/)([\w-]{11})", url)
    if not m:
        return None
    for q in ("maxresdefault", "hqdefault"):
        try:
            return urllib.request.urlopen(f"https://i.ytimg.com/vi/{m.group(1)}/{q}.jpg", timeout=20).read()
        except urllib.error.HTTPError:
            continue
    return None


# ---------------------------------------------------------------- hosts
def r2_put(cfg, key, data, ctype="image/jpeg"):
    """S3 SigV4 PUT to Cloudflare R2, stdlib only."""
    host = f"{cfg['account_id']}.r2.cloudflarestorage.com"
    path = "/" + cfg["bucket"] + "/" + "/".join(urllib.request.quote(p, safe="") for p in key.split("/"))
    now = dt.datetime.now(dt.timezone.utc)
    amzdate, datestamp = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
    payload_hash = hashlib.sha256(data).hexdigest()
    headers = {"content-type": ctype, "host": host, "x-amz-content-sha256": payload_hash, "x-amz-date": amzdate}
    signed = ";".join(sorted(headers))
    canonical = "\n".join(["PUT", path, "", "".join(f"{k}:{headers[k]}\n" for k in sorted(headers)), signed, payload_hash])
    scope = f"{datestamp}/auto/s3/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amzdate, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    k = ("AWS4" + cfg["secret_access_key"]).encode()
    for part in (datestamp, "auto", "s3", "aws4_request"):
        k = hmac.new(k, part.encode(), hashlib.sha256).digest()
    sig = hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()
    headers["authorization"] = f"AWS4-HMAC-SHA256 Credential={cfg['access_key_id']}/{scope}, SignedHeaders={signed}, Signature={sig}"
    req = urllib.request.Request(f"https://{host}{path}", data=data, method="PUT", headers=headers)
    urllib.request.urlopen(req, timeout=60).read()
    return cfg["public_base_url"].rstrip("/") + "/" + urllib.request.quote(key)


def verify(url):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=20)
        return r.status == 200 and r.headers.get("content-type", "").startswith("image/")
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("issue")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    path = Path(a.issue).resolve()
    base = path.parent
    issue = json.load(open(path))
    known = json.load(open(PROGRAMS / f"{issue['program'].lower()}.json")).get("known_headshots", {})
    host = json.load(open(CONFIG)).get("image_host", {"type": "manual"}) if CONFIG.exists() else {"type": "manual"}
    outdir = base / "out" / "img"
    outdir.mkdir(parents=True, exist_ok=True)
    manual_map_f = base / "out" / "upload-urls.json"
    manual_map = json.load(open(manual_map_f)) if manual_map_f.exists() else {}

    # video sections without a thumbnail: fetch YouTube's and burn in a play button
    for s in issue["sections"]:
        if s["type"] == "video" and not s.get("thumbnail"):
            raw = youtube_thumb(s["url"])
            if raw:
                p = outdir / "_yt_source.jpg"
                p.write_bytes(raw)
                s["thumbnail"] = str(p)

    week = issue["date"]
    prog = issue["program"].lower()
    todo, missing = [], []
    for cont, key, role in walk(issue):
        ref = cont[key]
        if role == "avatar" and isinstance(ref, str) and (ref in known or ref.startswith("http")):
            # headshots on file are not square: fetch and crop them like any other
            raw = urllib.request.urlopen(known.get(ref, ref), timeout=30).read()
            src = outdir / f"_src-{re.sub(r'[^a-z0-9]+', '-', ref.lower())[:30]}.jpg"
            src.write_bytes(raw)
        elif not is_local(ref, known):
            continue
        else:
            src = Path(ref).expanduser()
            src = src if src.is_absolute() else base / src
        if not src.exists():
            missing.append(str(src))
            continue
        data, (w, h) = prepare(src, role)
        name = f"{re.sub(r'[^a-z0-9]+', '-', src.stem.lower()).strip('-')[:40]}-{hashlib.sha1(data).hexdigest()[:8]}.jpg"
        (outdir / name).write_bytes(data)
        todo.append((cont, key, name, w, h, len(data)))
    if missing:
        sys.exit("missing image files:\n  " + "\n  ".join(missing))

    total = sum(t[5] for t in todo)
    print(f"{len(todo)} images prepared in {outdir} ({total/1e6:.1f} MB)")
    if a.dry_run:
        return

    failed = []
    for cont, key, name, w, h, n in todo:
        if host["type"] == "r2":
            url = r2_put(host, f"{host.get('prefix', 'newsletter')}/{week}/{prog}/{name}", (outdir / name).read_bytes())
        else:  # manual
            url = manual_map.get(name) or ""
            manual_map.setdefault(name, "")
        if url and not verify(url):
            failed.append(url)
        cont[key] = {"src": url, "w": w, "h": h} if url else cont[key]
    if host["type"] == "manual":
        manual_map_f.write_text(json.dumps(manual_map, indent=2))
        blank = [k for k, v in manual_map.items() if not v]
        if blank:
            sys.exit(f"manual hosting: upload the {len(blank)} file(s) in {outdir} to the Constant Contact Library,\n"
                     f"paste each URL into {manual_map_f}, then run this again.")
    if failed:
        sys.exit("uploaded but not publicly readable (check the bucket's public access):\n  " + "\n  ".join(failed))
    issue["_base"] = str(base)
    hosted = base / "issue.hosted.json"
    hosted.write_text(json.dumps(issue, indent=1, ensure_ascii=False))
    print(f"all images hosted and verified -> {hosted}")


if __name__ == "__main__":
    main()
