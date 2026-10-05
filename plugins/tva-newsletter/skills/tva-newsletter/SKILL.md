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
Friday: `YYYY-MM-DD Parsha/MTVA/` and `.../YTVA/`.

**The folder is shared in Google Drive** ("TVA Newsletter", owned by yehudaseif@gmail.com,
shared with the MTVA editor, the YTVA editor and the reviewer). If `drop_root` in the
config starts with `SET-ME`, find the synced copy and write its path into the config:
on a Mac `~/Library/CloudStorage/GoogleDrive-<account>/My Drive/TVA Newsletter`, on Windows
usually `G:/My Drive/TVA Newsletter`. A folder someone else shared only appears there after
the person adds it to their Drive (in drive.google.com: Shared with me → TVA Newsletter →
⋮ → Organize → Add shortcut → My Drive). If Google Drive for desktop isn't installed, say
so and stop; don't create a local folder instead, or the others won't see the work.

**Roles.** The config's `can_schedule` says whether this person may schedule. Editors
(`false`) build and test; the reviewer (`true`, `scheduler_name`) reviews, may edit
directly (section 5c), and schedules. When an editor's newsletter is ready, tell them
it's waiting for the reviewer; don't offer to schedule. Create next week's empty folders
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
prints the subject. If the staff-supplied time differs from Hebcal's (it happens — the
Shmini Atzeret 5787 draft said 5:48, Hebcal 5:43), use theirs via `"candles"` and flag it. Then **look at it**: render `out/preview.html` to a PNG with headless
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

## 5b. No API key yet? The browser route (Claude in Chrome)

Works today with only a logged-in Constant Contact tab. Every step below was learned
the hard way; follow it literally.

1. **Find the workspace.** The login is a multi-account *hub*. The newsletters live in
   the workspace **Bnei Akiva of the US & Canada** (Premium, user `bana2018`). Deep links
   such as `/pages/ecamp/emails` or `/pages/dashboard` 404 — open
   `https://app.constantcontact.com/home`, use the **Hub** dropdown (top left) to switch
   into that workspace, then **Campaigns**. Campaign names look like
   `MTVA Shmini Atzeret 5787` / `YTVA Parashat Haazinu 2026-7`.
2. **Reading an existing draft** (when content was entered in Constant Contact): row
   menu **…** → **Preview**. The email sits in a same-origin iframe. Tool output
   truncates at ~1,000 characters and Chrome blocks posting to localhost, so serialise the
   iframe body (text plus `**bold**`, `[IMG w= src=]`, `[text](href)` markers) into an
   `<article>` you prepend to the page, read it with `get_page_text`, then remove it.
   The Preview panel also shows the subject, From name and addresses.
3. **Uploading images** (manual host): **Assets → Library → Upload → My Computer** opens
   a cross-origin iframe. Navigate the tab to that iframe's `src`
   (`legacy-mlui.constantcontact.com/mlui/upload/view?…tab=localUploadTab…`), then
   `file_upload` all of `out/img/*.jpg` onto `#fileUploadSplash`, click **Upload Files**,
   **Done**. Each file's public URL is
   `https://files.constantcontact.com/da3b95bc001/<uuid>.jpg?rdr=true`, where `<uuid>` is
   in the Library thumbnail path (`…/da3b95bc001/<uuid>-thumbnail.jpg`) on
   `legacy-mlui.constantcontact.com/mlui/home` (newest first; **Show More** for the rest).
   Download each URL and compare bytes with the local file before writing
   `out/upload-urls.json`.
4. **Creating the email**: **Create a campaign → Email → Paste your own code (Paste
   HTML)**. The editor is CodeMirror 5. Put the HTML on the clipboard with
   **`LANG=en_US.UTF-8 pbcopy < out/email.html`** — without `LANG`, pbcopy reads the file
   as Mac Roman and silently mangles `·`, curly quotes and all Hebrew. Focus the editor,
   `CodeMirror.execCommand('selectAll')`, press cmd+v, then confirm the SHA-256 of
   `CodeMirror.getValue()` (UTF-8) equals `shasum -a 256 out/email.html`.
5. **Email Settings** (link above the editor): subject, From name
   (`Midreshet Torah V'Avodah` / `Yeshivat Torah V'Avodah`), reply-to
   `office@tvaisrael.org`. The From-address list for new emails only offers authenticated
   `*@bneiakiva.ccsend.com` senders (use `tvaoffice@bneiakiva.ccsend.com`); the existing
   MTVA drafts show `office@tvaisrael.org`, so check with the office which is right before
   a live send. Dropdown lists scroll — zoom and confirm the selected value after clicking.
   Rename the draft (pencil by the title), **Save**, **Check & Preview → Check For Errors**,
   then **Preview**, which also has the **Send test** box.
6. Test sends and scheduling follow the same rules as section 5: a test only to
   addresses the user names, the real send only on an explicit go-ahead.

## 5c. Changes after the draft exists (editor or reviewer)

The week folder is usually a **shared** folder (Google Drive), so the editor (Aliza for
MTVA, Aliya for YTVA) and the reviewer (Michelle) work on the same files. Whoever asks
for a change, the same rules apply:

- If `issue.json` already exists for that program and week, it is the **source of
  truth**. Change it in place. Never rebuild it from the drop folder unless the user
  explicitly asks to start over — that would silently undo someone else's fixes. Read
  `changes.md` first to see what others already changed.
- Make only the change asked for. For the authors' words, a requested correction (a
  name, a year, a typo the user points out) is fine; still no unrequested rewording.
- Then: `images.py` (only new photos upload; existing ones are reused) → `render.py
  issue.hosted.json` → `cc.py draft` (updates the **same** draft; it never makes a
  second one while `out/campaign.json` exists) → `cc.py test`.
- Append one plain line to `changes.md` saying who asked for what, e.g.
  `- Mon 14:05 Michelle: Rivka Levi's year 5782 → 5783`. `cc.py draft` adds a timestamp
  line on its own.
- Drive sync can lag or revert a just-written file: re-read `issue.json` after saving
  and before rendering.
- If the newsletter is already **scheduled**, `cc.py draft` refuses to edit it. Run
  `cc.py status`, tell the user it is scheduled and for when, and only with their OK run
  `cc.py unschedule`, make the change, send a new test, and reschedule (which again
  needs `--confirm` and an explicit time from the user). Never leave it unscheduled
  silently: say clearly that it will not go out until it is scheduled again.
- Two people editing the same week at the same minute will overwrite each other. If
  `changes.md` shows an edit in the last few minutes by someone else, mention it before
  saving.

## 6. Report back

Per program: subject line, sections included (and any left out because the folder was
empty), photo count, the draft name, who got the test, and anything you could not
verify — the user checks names, dates and facts before it goes to every family.

## Changing the fixed parts

Staff list, addresses, donate link, colours, header art, recurring headshots: edit
`programs/<program>.json`. Images there must already be public URLs (the current ones
are in the Constant Contact library). After any change, render last week's issue and
compare before using it live.
