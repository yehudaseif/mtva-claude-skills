#!/usr/bin/env python3
"""Create this week's drop folders for the staff who feed the newsletter.

    python3 new_week.py                 # the coming Friday
    python3 new_week.py --date 2026-10-09

Makes  <drop_root>/<YYYY-MM-DD Parsha>/{MTVA,YTVA}/  with one subfolder per kind of
piece and a short README in each program folder. drop_root comes from
~/.config/tva-newsletter/config.json ("drop_root"), default ~/Documents/TVA Newsletter.
"""
import argparse, datetime as dt, json, urllib.request
from pathlib import Path

CONFIG = Path.home() / ".config" / "tva-newsletter" / "config.json"

FOLDERS = {
    "1 Dvar Torah": "The week's dvar Torah: a Word/Google Doc/text file, plus the author's photo.\n"
                    "Several divrei Torah? One subfolder each. A video dvar Torah: put the YouTube link in link.txt.",
    "2 Weekly Update": "The director's update (doc or text). Headshot optional; the regular one is on file.",
    "3 Student Pieces": "Student divrei Torah / reflections: one subfolder per student with the text and a photo.\n"
                        "Name the folder 'Name; Hometown' if you can.",
    "4 Podcasts": "links.txt: one per line, 'Speaker: Title | https://link'. Spotify/YouTube thumbnails are fetched automatically.",
    "5 Announcements": "One subfolder per announcement: the flyer image plus notes.txt (heading line, optional link,\n"
                       "optional 'RSVP: text | url' strip).",
    "6 Photos": "One subfolder per album, named with the caption you want printed above it, e.g. 'Chevron Tiyul!'.\n"
                "Put the photos in the order you want them shown (sorted by file name).",
}
FILES = {
    "Birthdays.txt": "# One per line, e.g.\n# Lilly Golombeck | on Shabbat\n",
    "Mazal Tovs.txt": "# One per line, written as it should appear, e.g.\n"
                      "# Mazal Tov to **Hannah Friedman** (5783) and Sam on their engagement!\n"
                      "# A photo for one of them: put it in this folder named after the person.\n",
    "Sponsors.txt": "# One per line, e.g.\n# Thank-you to the Kaufthal Family for sponsoring Sunday Morning breakfast!\n",
    "Notes.txt": "# Anything else: subject line wishes, sections to drop this week, corrections.\n",
}


def coming_friday(today=None):
    today = today or dt.date.today()
    return today + dt.timedelta(days=(4 - today.weekday()) % 7)


def parsha(friday):
    try:
        q = f"https://www.hebcal.com/shabbat?cfg=json&geonameid=281184&M=on&gy={friday.year}&gm={friday.month}&gd={friday.day}"
        for it in json.load(urllib.request.urlopen(q, timeout=20))["items"]:
            if it["category"] == "parashat":
                return it["title"].replace("Parashat ", "").replace("’", "'")
    except Exception:
        pass
    return ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", help="Friday, YYYY-MM-DD (default: the coming Friday)")
    a = ap.parse_args()
    friday = dt.date.fromisoformat(a.date) if a.date else coming_friday()
    cfg = json.load(open(CONFIG)) if CONFIG.exists() else {}
    root = cfg.get("drop_root", "~/Documents/TVA Newsletter")
    if root.startswith("SET-ME"):
        raise SystemExit("drop_root is not set yet: point it at the shared 'TVA Newsletter' Google Drive "
                         "folder on this computer (see SETUP.md 4b).")
    root = Path(root).expanduser()
    week = root / f"{friday.isoformat()} {parsha(friday)}".strip()
    for prog in ("MTVA", "YTVA"):
        p = week / prog
        for name, note in FOLDERS.items():
            (p / name).mkdir(parents=True, exist_ok=True)
        for name, body in FILES.items():
            f = p / name
            if not f.exists():
                f.write_text(body)
        readme = p / "README.txt"
        if not readme.exists():
            readme.write_text(f"{prog} newsletter for Shabbat {friday:%B %-d, %Y}.\n\nDrop this week's pieces here:\n\n"
                              + "\n\n".join(f"{k}/\n  {v}" for k, v in FOLDERS.items())
                              + "\n\nBirthdays.txt, Mazal Tovs.txt, Sponsors.txt, Notes.txt: see the examples inside each file.\n"
                              "Empty folders and files are simply left out of the email.\n")
    print(week)


if __name__ == "__main__":
    main()
