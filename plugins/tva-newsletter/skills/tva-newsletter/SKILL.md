---
name: tva-newsletter
description: Build the weekly MTVA and YTVA Shabbat newsletters ("Shabbat Shalom from MTVA/YTVA") in Constant Contact. Reads the week's drop folder (dvar Torah, weekly update, student pieces, podcasts, flyers, birthdays, mazal tovs, sponsors, photos), fills each program's fixed house template, hosts the photos, and creates the Constant Contact draft and test send. Use when the user mentions the MTVA or YTVA newsletter, the weekly Shabbat email, the Friday email to parents, or "process the newsletter folder".
---

# TVA weekly newsletter (MTVA + YTVA)

Every Friday each program sends one email in a fixed house style. Everything that
never changes — header art, colours, date band, section bars, donate button, staff,
contact, About Bnei Akiva, social icons — lives in `programs/mtva.json` and
`programs/ytva.json`. The only weekly work is turning the drop folder into
`issue.json`; the scripts do the rest.

```
drop folder ──(you read it)──> issue.json ──render.py──> out/preview.html  (look at it)
                                     └──images.py──> issue.hosted.json ──render.py──> out/email.html
                                                                              └──cc.py draft / test ──> Constant Contact
```

Scripts are in `scripts/` next to this file (Python 3.9+, Pillow for images). Config and
the Constant Contact login live in `~/.config/tva-newsletter/`. If `config.json` is
missing, stop and walk the user through `SETUP.md`.

## 1. Find the week

`drop_root` in the config (default `~/Documents/TVA Newsletter`) holds one folder per
Friday: `YYYY-MM-DD Parsha/MTVA/` and `.../YTVA/`. Create next week's empty folders
with `python3 scripts/new_week.py [--date YYYY-MM-DD]` — staff fill them during the week.

Work one program at a time. Read **every** file in its folder, including subfolders.
- `.docx`: `textutil -convert txt -stdout file.docx` (macOS) or `pandoc -t plain`.
- `.pdf`: `pdftotext -layout`. Google Doc links: read through the Google Drive
  connector if available; otherwise ask for the text.
- Images: look at them. A headshot is a person facing the camera; everything else in
  an album folder is a photo for that album.
- An empty folder or a file holding only the `#` example lines means "no section this
  week". Leave it out; never fill a gap with your own text.

## 2. Write issue.json

Save it in the program folder (`.../MTVA/issue.json`). Image paths are relative to that
folder. Order the sections the way the real newsletters do:

**MTVA**: Dvar Torah(s) → This Week's Highlights (Rabbi Bayer) → Student Reflection →
Podcasts → Announcements → Birthdays → Sharing Corner (mazal tovs) → Photos.
Student pieces use heading `Student Dvar Torah` / `Student Reflection`, byline
`Name; Hometown, ST`, and their own title in `title`.

**YTVA**: Dvar Torah (often Rav Yair's video) → Weekly Update (Rav Segal) → student
Dvar Torah (byline `Name; Hometown, ST; Shana Bet/Hesder`) → Podcasts → Announcements →
Happy Birthday → Thank you to our Sponsors → Photos.

```json
{
  "program": "mtva",                 // or "ytva"
  "date": "2026-10-09",              // the Friday
  "title": null,                     // omit: built from Hebcal ("Shabbat Parshat Bereshit",
                                     // "Shabbat Shuva - Parshat ...") — REQUIRED on chag weeks
  "subject": null, "preheader": null,// omit for the standard "Shabbat Shalom from MTVA - Parshat X"
  "sections": [
    {"type": "article", "heading": "Student Dvar Torah", "byline": "Name; Teaneck, NJ",
     "title": "Coming Back", "image": "1 Dvar Torah/name.jpg", "image_side": "right",
     "body": "Paragraph one.\n\nParagraph two with **bold**, *italic*, [a link](https://...)."},
    {"type": "article", "heading": "This Week's Highlights", "byline": "Rabbi Aaron Bayer; Director",
     "image": "Rabbi Aaron Bayer", "body": "..."},          // a known_headshots name = the photo on file
    {"type": "video", "heading": "Dvar Torah", "byline": "Rav Yair (Eisenstock) HaLevi, Rosh Yeshiva",
     "url": "https://youtu.be/..."},                        // thumbnail + play button made automatically
    {"type": "media", "heading": null, "intro": "optional", "items": [
       {"url": "https://open.spotify.com/episode/...", "caption": "Rav X: Title"}]},
    {"type": "announcement", "heading": "Line one\nLine two", "image": "5 Announcements/flyer.png",
     "url": "optional link on the flyer", "body": "optional text",
     "button": {"label": "RSVP for the Hachnasat Sefer Torah", "url": "https://..."}},
    {"type": "birthdays", "items": ["Happy birthday to **Name** whose birthday is on Shabbat!"]},
    {"type": "mazal_tov", "items": ["Mazal Tov to **Name** (5783) and Sam on their engagement!",
       {"text": "Mazal Tov to **Name** on her Aliyah!", "image": "photo.jpg"}]},
    {"type": "sponsors", "items": ["Thank-you to the X Family for sponsoring\nSunday breakfast!!"],
     "contact": {"text": "To sponsor any future programming, please contact",
                 "name": "Rav Gabi Katz", "email": "Gabikatz@tvaisrael.org"}},
    {"type": "photos", "albums": [{"caption": "Chevron Tiyul!", "photos": ["6 Photos/Chevron Tiyul!/01.jpg"]}]},
    {"type": "text", "heading": "optional", "body": "free text section"}
  ]
}
```
(Comments above are for you; the real file is plain JSON.) Headings left `null` use the
program's standard title (`section_titles` in the program file). Add `"skip": true` to
drop a section without deleting it.

How the layout uses these fields (it is automatic; this is so you fill them well):
- `byline` splits at the first `;` or `,`: the name in bold, the rest (role, hometown,
  shana) underneath in grey. An `image` there is shown as a round headshot beside it —
  use a photo of that person, never a group shot. Long pieces get "N min read" added.
- With a `title`, the `heading` becomes a small coloured label above it (student pieces:
  heading "Student Dvar Torah", title = the student's own title). Without one, the
  heading is the section title.
- Podcast captions split at the first `:` into speaker and episode title.
- Announcement buttons: use the wording the folder gives for the link ("RSVP", "Register
  here"). A legacy `strip` with `{HERE}` still works but makes a clumsier button.
- Landscape photos run full width; portraits pair up side by side; on phones everything
  stacks to full width.
- "In this issue" under the header is built from the section headings.

**The words are the authors'.** Copy divrei Torah, updates and reflections verbatim,
paragraph for paragraph — no rewording, trimming, or "polish". If you notice a typo or
a wrong name, list it for the user instead of fixing it silently. Every factual line
(birthdays, mazal tovs, sponsors, announcements) must come from the folder; if
something seems missing, say so rather than writing it.

## 3. Preview and look

```bash
python3 scripts/render.py ".../MTVA/issue.json" --preview
```
It pulls the parsha, Hebrew date and Jerusalem candle lighting (40 min) from Hebcal and
prints the subject. Then **look at it**: render `out/preview.html` to a PNG with headless
Chrome (`"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new
--hide-scrollbars --window-size=800,12000 --screenshot=out/preview.png file://…`) and read
the image. Check the header line, every section is present and in order, photos are the
right way up, Hebrew reads correctly, nothing is cut off.

## 4. Host the images and render the final email

```bash
python3 scripts/images.py ".../MTVA/issue.json"     # resize, upload, verify each URL -> issue.hosted.json
python3 scripts/render.py ".../MTVA/issue.hosted.json"
```
`render.py` fails (exit 1) on anything Constant Contact would reject: over 400 KB, the
forbidden pairs `[#` `${` `<@`, `[[trackingImage]]` outside the body, missing alt text,
or images still pointing at local files. It warns past ~102 KB, where Gmail clips the
message — trim photos if you see that.

## 5. Constant Contact

```bash
python3 scripts/cc.py draft ".../MTVA"    # creates the draft (re-running updates the same draft)
python3 scripts/cc.py test  ".../MTVA"    # test copy to the program's test_recipients
```
Creating the draft and the test send are routine once the user has asked for the
newsletter. **Sending to the families is not.** Only schedule after a person has read
the test email and said to send it, naming the time:
```bash
python3 scripts/cc.py schedule ".../MTVA" --at "2026-10-09 13:30" --confirm   # Jerusalem time
```
Without `--confirm` it only prints what it would do. Never add `--confirm` on your own
initiative, and never schedule from a recurring/automated run.

## 6. Report back

Per program: subject line, sections included (and any left out because the folder was
empty), photo count, the draft name, who got the test, and anything you could not
verify — the user checks names, dates and facts before it goes to every family.

## Changing the fixed parts

Staff list, addresses, donate link, colours, header art, recurring headshots: edit
`programs/<program>.json`. Images there must already be public URLs (the current ones
are in the Constant Contact library). After any change, render last week's issue and
compare before using it live.
