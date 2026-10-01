---
name: weekly-newsletter
description: Build the weekly parent newsletter as an email — produces paste-ready HTML for Constant Contact's Custom Code editor plus a plain-text version. Use when the user mentions Constant Contact, the weekly email, the parent newsletter, an email blast, or sending the week's update to parents. For the MTVA/YTVA Shabbat newsletters use tva-newsletter instead.
---

# Weekly Newsletter

Turns the week's raw pieces into an email that looks like the school meant it.
Output is HTML you paste into Constant Contact's **Custom Code** editor, plus a
plain-text version.

Start from `templates/weekly-email.html`. It is already inside every Constant
Contact constraint below and renders correctly in table-based clients — editing
it beats authoring email HTML from scratch, which is a genuinely unpleasant job.

## Constant Contact's hard rules

These are not style preferences. Break one and the campaign is rejected or the
reporting silently breaks.

- **400 KB maximum** for the whole email. Easy to stay under with text; blow it
  by pasting base64 images inline. Host images and link to them.
- **Three character pairs are forbidden anywhere in the source:** `[#`, `${`,
  and `<@`. Plain `#` in a hex colour is fine — it's the pair that breaks.
  Watch for `${` creeping in from a copied template, and `[#` from a stray
  bracket before a colour value.
- **`[[trackingImage]]` must appear inside the `<body>` element.** Without it,
  Constant Contact falls back to click data and your open rate is wrong. Put it
  immediately before `</body>`.
- **CSS in a `<style>` block is fine** — Constant Contact converts declarations
  to inline CSS on send. Keep selectors to plain classes and elements.

**Verify before handing it over.** Check the file for those three pairs, check
the size, and confirm the tracking tag is inside the body. It takes seconds and
catches the failure that otherwise surfaces after the paste.

## Personalization tags

Constant Contact substitutes these at send time:

- Contact fields — first name, last name, and so on
- Custom fields — `[[CUSTOM.field_name]]`
- Account details — organisation name, address, website

**Always give a fallback**, using the `OR` syntax:
`[[FIRSTNAME OR "there"]]`. Without it, a contact missing that field gets a
blank or a raw tag in their greeting, which is exactly the kind of thing a
parent screenshots.

If the contact data isn't reliably populated — and in a school it often isn't —
prefer "Dear Parents" over a personalised greeting that fails for a dozen
families.

## Writing email HTML that survives

- **Tables for layout.** No flexbox, no grid, no absolute positioning. Outlook
  renders with Word's engine and ignores all three.
- **600 pixels wide.** The long-standing safe width.
- **Web-safe fonts with real fallbacks** — Arial, Georgia, Times New Roman.
  A webfont will silently fall back in most clients, so design for the fallback.
- **Alt text on every image**, and never put essential information only in an
  image. Many clients block images by default, so an image-only newsletter
  arrives blank.
- **A written preheader.** The grey line after the subject in the inbox — set
  it deliberately, because it's the second thing a parent reads. The template
  has a hidden div for it at the top.
- **No script tags, no forms, no video.** They're stripped or they trip spam
  filters.

## The content itself

The failure mode of a school newsletter is that it's a wall of everything, so
parents stop opening it and then miss the thing that mattered.

- **Lead with what needs action.** The template has a highlighted block for
  exactly one thing. If everything is highlighted, nothing is.
- **One line per day** for the week's schedule. Detail goes on the website or
  in a separate letter.
- **Say what a parent must do, by when.** "Forms due Friday" beats "please
  return forms promptly".
- **Cut anything that's the same as last week.** Recurring information belongs
  on a page you link to, not in every issue.
- **Ask where the pieces come from** the first time — times, menu, trips and
  birthdays usually arrive from several people in several formats. Write the
  sources down beside the file and the second week is a sentence.

## Getting it into Constant Contact

1. Create new email, choose **Custom Code**, name the campaign, select HTML.
2. Delete the default code in the HTML body area.
3. Paste the whole file.
4. Use the live preview to check layout.
5. **Send a test to yourself and open it on a phone.** More than half of parent
   email is read on a phone, and the preview is not the same as the real thing.

## Always produce a plain-text version too

Some clients and some parents get plain text. Write it as real prose, not as a
stripped tag soup — same information, same order, no markup. It takes a minute
and it's what a screen reader user may receive.

## Before you say it's ready

Say plainly what you have and haven't checked. You've checked the constraints,
the size, and the tags. You have **not** checked the facts — the times, the
dates, whose birthday it is. Those come from whoever supplied them, and this
goes to every parent in the school, so it wants a human read before it goes.
