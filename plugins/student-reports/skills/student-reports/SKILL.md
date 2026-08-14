---
name: student-reports
description: Turn attendance, grade, or roster spreadsheets into analysis and per-student PDF reports. Reads .xlsx/.csv, computes attendance rates and flags thresholds, and renders one letterheaded PDF per student via Typst. Use when the user mentions attendance, absences, progress reports, report cards, parent letters, or asks for "one PDF per student" from a spreadsheet.
---

# Student Reports

Spreadsheet in, analysis and a batch of parent-facing PDFs out. Two phases, and
**they are always separate**: understand the data and get the user to confirm
the numbers, *then* generate documents. Never generate 60 PDFs from an
interpretation nobody has checked.

## Pre-flight

Typst renders the PDFs. Confirm it is installed before promising output:

```bash
typst --version || {
  case "$(uname -s)" in
    Darwin) brew install typst ;;
    Linux)  command -v apt-get >/dev/null && sudo apt-get install -y typst \
              || { mkdir -p ~/.local/bin && curl -L "https://github.com/typst/typst/releases/latest/download/typst-x86_64-unknown-linux-musl.tar.xz" \
                   | tar -xJ -C /tmp && mv /tmp/typst-*/typst ~/.local/bin/ && export PATH="$HOME/.local/bin:$PATH"; } ;;
  esac
  typst --version
}
```

Version 0.11 or newer. Older builds lack features the template uses.

## Phase 1 — read the data, report back, stop

1. **Open the sheet and describe what's actually there** before computing
   anything. Real school exports are messy: merged header cells, a title row
   above the headers, blank spacer rows, totals rows mixed in with students,
   inconsistent name spellings, dates as text.
2. **Say what you found and what you're going to do about it.** Name the
   specific problems — "rows 1–2 are a title block, row 3 is the real header,
   rows 48 and 49 are totals not students, and 'Levi, Sara' and 'Sara Levi'
   look like the same person."
3. **Compute the metrics**, then report the summary: total students, the
   distribution, who crosses the threshold, and any pattern worth naming (a
   day-of-week effect, a month where everything drops, a student whose absences
   are all consecutive — that last one usually means illness or a family trip,
   not a discipline problem, and the report should not imply otherwise).
4. **Stop and get confirmation.** Ask the user to check two or three figures by
   hand before you generate anything. Say it plainly: these documents go to
   parents.

Never silently drop a row you couldn't parse. If eight rows are unusable, say
so and show them.

### Definitions that must be pinned before computing

Ask if the sheet doesn't make it obvious:

- Does an excused absence count against the rate?
- Are late arrivals a separate category, or fractional attendance?
- Is the denominator days-enrolled or days-in-term? These differ for anyone who
  joined mid-year, and using the wrong one produces an unfair number.
- What's the flag threshold? Don't assume 85%.

## Phase 2 — generate the PDFs

Only after the user confirms.

1. Copy `templates/attendance-report.typ` into the working directory. Do not
   author a template from scratch — this one is already debugged.
2. Write the per-student data into the template's data block. For a batch,
   generate one `.typ` per student and compile in a loop:

```bash
for f in out/*.typ; do typst compile "$f" "${f%.typ}.pdf"; done
```

3. **Read the first rendered PDF before compiling the rest.** Not the `.typ`
   source — the actual PDF. Check the layout gotchas below. Fix, recompile, and
   only then run the batch.
4. Name files predictably: `Surname-Firstname-attendance-2026-08.pdf`. Sortable
   and unambiguous when someone is looking for one student.
5. Save output where the user asked. If they didn't say, ask — do not scatter
   sixty PDFs into the folder holding the source spreadsheet.

### Tone of the generated document

These are read by a parent who may be worried, defensive, or reading in a
second language. The document states facts and leaves interpretation to the
advisor.

- Report the number and the dates. Do not editorialise about them.
- No warning language, no consequences, no implied judgement. "Attendance rate:
  78%" — not "unacceptably low attendance."
- Always include a comments box the advisor fills in by hand or in a follow-up.
  The human adds the meaning.
- If the school has a standard closing paragraph or contact line, ask for it
  rather than inventing one.

## Layout gotchas — verify on every compile

Inspect the rendered PDF, every page, before calling it done:

- **No page under 40% ink coverage.** A trailing page with four lines on it is
  a failure, not an acceptable result. Fix by tightening in this order: spacing
  between blocks, leading, margins, then font size by 0.5pt.
- **No orphaned headers.** A section heading must never sit alone at the bottom
  of a page. Wrap header-plus-first-child in `block(breakable: false)`.
- **Check the page count**: `pdfinfo file.pdf | grep Pages`. A one-page report
  that became two needs investigating, not accepting.
- **Escape dollar signs.** In Typst markup `$` opens math mode; `$40` produces
  an unclosed-delimiter error. Write `\$40`.
- **Never mix Hebrew and Latin characters inside one token.** `(rישוי)` renders
  bidi-corrupted, with the bracket migrating to the wrong side. Keep Hebrew
  words whole and standalone, or transliterate.
- **Don't speculatively insert `#pagebreak()`** — if the content already fits,
  you have manufactured a blank gap.
- **Don't put `#v(1fr)` before a footer** unless every page is guaranteed to
  overflow; it will push the footer onto a blank page of its own.

## Charts

The attendance bar chart is drawn natively in Typst — see the template. Don't
reach for an external plotting library and embed a PNG; it will not match the
document's type and will look pasted in.

Keep the chart honest: a y-axis that starts at 70% to make a dip look dramatic
is not acceptable on a document going to a parent. Start at zero.

## Reusing the format next term

Once a report format is approved, write down the recipe — the column mapping,
the threshold, the definitions settled above, the output path — in a
`report-recipe.md` next to the data. Next term becomes one sentence instead of
this whole conversation.
