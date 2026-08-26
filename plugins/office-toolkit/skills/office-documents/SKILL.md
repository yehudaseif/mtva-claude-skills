---
name: office-documents
description: Produce the school office's standard documents as polished PDFs — the weekly notice sheet or bulletin, reimbursement and expense summaries for signature, and letters to parents. Use when the user mentions a notice sheet, bulletin, newsletter for the board, expenses, receipts, a reimbursement claim, or a letter home.
---

# Office Documents

Three documents the office produces over and over. Each has a debugged
template — start from it rather than authoring a layout from scratch.

Rendering, fonts, install and the Typst traps live in the `typst-pdf` skill.
This skill is the templates and the house conventions.

| Template | For |
|---|---|
| `templates/notice-sheet.typ` | Weekly bulletin — times, schedule, menu, birthdays, notices |
| `templates/reimbursement-summary.typ` | Expense claim someone signs off |
| `templates/letter.typ` | Single letter or a mail-merge run to parents |

Copy the template into the working folder, rename it for the week or the job,
edit the content block at the top, and compile. The content block is separated
from the layout on purpose — most weeks you never touch the layout.

## Notice sheet

The content block at the top is the whole job. Switch `paper` to `"a3"` and
`base` to `14pt` for the bulletin board; leave A4 for handouts and for anything
going into email.

- **Ask where the pieces come from** the first time — times, menu, trips and
  birthdays usually arrive from four different people in four different
  formats. Once you know, write the sources into a note beside the file so the
  second week is a sentence.
- **Keep the two columns close in height.** Typst breaks grid cells
  independently, so a much longer left column spills onto a second page while
  the right one ends early. Move a panel across rather than letting it run.
- **Empty panels should be deleted, not left blank.** A "Birthdays" heading
  with nothing under it looks like a mistake; no heading looks deliberate.

## Reimbursement summary

The output is a page someone signs, so the discipline matters more than the
layout.

- **Never invent an amount.** If a receipt can't be read, the amount stays
  blank and the row is flagged `unreadable`. A blank cell is recoverable; a
  plausible wrong number in a finance document is not.
- **Never convert a currency without a stated rate.** Flag the row `foreign`
  and ask. A made-up exchange rate is the same failure as a made-up amount.
- **Flag, don't decide.** Over-limit items, suspected duplicates and unreadable
  receipts get a flag and stay in the table. Whoever signs decides what happens
  to them — that is the entire point of the signature.
- **Excluded rows must not silently vanish.** They stay visible with a flag,
  and the note explains that they're outside the total.
- Say in the note what the per-item limit is, so the reader can check the
  flagging rather than trust it.

## Letters to parents

- **Say the thing in the first two sentences.** A parent should know what the
  letter is about before deciding whether to keep reading.
- **Leave a door open.** Anything chasing or corrective ends with a way to
  respond — a phone number, an invitation to call. "It may simply have crossed
  with this letter" costs one line and defuses a lot.
- **No warning language unless the school has decided to warn.** State facts,
  name the next step. Escalation is a decision a person makes, not a tone the
  document adopts by default.
- **Never guess at a name, spelling, or figure.** Ask, or leave a clearly
  marked placeholder. A misspelled child's name undoes an otherwise good
  letter.

For a mail-merge run, generate one `.typ` per recipient and compile in a loop.
On Windows without Git Bash you're in PowerShell:

```powershell
Get-ChildItem *.typ | ForEach-Object { typst compile $_.Name ($_.BaseName + ".pdf") }
```

**Generate one and look at it before running the batch.** A layout problem
found on letter 1 costs a minute; found on letter 60 it costs the afternoon.

## House details to set once

The templates ship with `Example School` placeholders. Replace them with the
real letterhead, address, contact line and colours the first time, then keep
those edited templates as the house versions — don't re-enter them weekly.

If the school has a logo, place it in the letterhead grid with
`image("logo.png", height: 1.1cm)` in place of the school name text.
