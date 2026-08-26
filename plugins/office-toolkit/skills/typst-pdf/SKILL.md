---
name: typst-pdf
description: Render any document to a polished, printable PDF using Typst — schedules, agendas, lists, briefs, letters, one-off handouts. Use whenever the user asks for a PDF, something printable, a nicely formatted document, or a handout, and no more specific document skill applies. Works on Windows, macOS and Linux.
---

# Typst PDF

Turns assembled content into a PDF that looks like someone laid it out on
purpose. Typst is the engine: you write a `.typ` file and compile it.

## Pre-flight — is Typst installed?

Run `typst --version` first. If it's missing, install it for the platform in
front of you, then check again.

### Windows

```powershell
winget install -e --id Typst.Typst
```

**If winget returns a 404 or can't find the package** — a known intermittent
problem — fall back to the release zip, which needs no installer:

```powershell
$dest = "$env:LOCALAPPDATA\Programs\typst"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$url = "https://github.com/typst/typst/releases/latest/download/typst-x86_64-pc-windows-msvc.zip"
Invoke-WebRequest -Uri $url -OutFile "$env:TEMP\typst.zip"
Expand-Archive -Path "$env:TEMP\typst.zip" -DestinationPath $dest -Force
$exe = (Get-ChildItem -Path $dest -Filter typst.exe -Recurse | Select-Object -First 1).FullName
[Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";" + (Split-Path $exe), "User")
& $exe --version
```

On an ARM machine swap `x86_64` for `aarch64`. After a PATH change, restart
Claude Code so the new PATH is picked up — otherwise `typst` still won't
resolve and you'll waste time debugging a shell that simply hasn't reloaded.

`scoop install typst` also works if the user already has Scoop.

### macOS

```bash
brew install typst
```

If `brew` itself is missing, don't install Homebrew just for this — download the
release binary for `aarch64-apple-darwin` (Apple silicon) or `x86_64-apple-darwin`
into `~/.local/bin` instead.

### Linux

`sudo apt install typst`, or the `x86_64-unknown-linux-musl` release tarball
extracted into `~/.local/bin`.

Anything older than 0.11 lacks features these templates use. If a package
manager gives you an ancient version, take the release binary instead.

## Which shell you're in matters on Windows

If Claude Code is running on Windows **without** Git for Windows installed,
shell commands go through PowerShell, not bash. So:

- Don't write bash-isms (`for f in *.typ; do ... done`, `&&` chains, heredocs)
  and assume they'll run. On PowerShell they won't.
- `typst compile input.typ output.pdf` is identical everywhere. Keep the shell
  surface that small and the platform stops mattering.
- To loop over files in PowerShell:
  `Get-ChildItem *.typ | ForEach-Object { typst compile $_.Name ($_.BaseName + ".pdf") }`

## Procedure

1. Confirm Typst runs.
2. **Start from a template** if one fits — the `office-documents` skill carries
   notice sheets, reimbursement summaries and letters. Adapting a debugged
   template beats authoring from scratch every time.
3. Write or edit the `.typ`.
4. Compile: `typst compile document.typ document.pdf`
5. **Open the rendered PDF and look at it.** Not the source — the PDF. Reading
   your own `.typ` is not verification.
6. Iterate. Three or four passes is normal, not a sign something went wrong.

## Choosing a font — this is not decoration

The font is the document's first sentence. Pick deliberately.

| Font | Register | Use for |
|------|----------|---------|
| **DejaVu Sans** | Utilitarian, dense, legible at 7–8pt | Checklists, schedules, notice sheets — anything scanned on the run |
| **Noto Sans** | Professional, neutral, wide Unicode | Letters to parents, agendas, anything client-facing |
| **New Computer Modern** | Formal, serifed, weighty | Board papers, formal reports. No Hebrew glyphs. |
| **Liberation Sans** | Neutral, data-first | Financial tables, reimbursement summaries |
| **Libertinus Serif** | Editorial, warm at length | Long-form reading, newsletters |

Ask: who reads it, how fast, and does it carry Hebrew? A shopping list in a
formal serif reads like a dissertation; a board paper in DejaVu Sans reads like
a grocery list.

On Windows the safe bets are `Segoe UI`, `Calibri`, `Arial` and `Times New
Roman` — they're always present. Run `typst fonts` to see what's actually
available before naming one; **Typst warns on any family it can't find and
silently falls back**, which is how a document ends up in a font nobody chose.

## Markup traps that cost an hour

- **Escape dollar signs.** `$` opens math mode. `$40` produces "unclosed
  delimiter". Write `\$40`.
- **Never bold a slash-command.** `*/clear*` reads as the end of a block
  comment and the file stops parsing. Use backticks: `` `/clear` ``.
- **Never mix Hebrew and Latin inside one token.** `(rישוי)` renders
  bidi-corrupted, with the bracket jumping to the wrong side. Keep Hebrew words
  whole and standalone, or transliterate.

## Layout traps — check these on every compile

- **No page under about 40% ink.** Two lines spilling onto a blank final page
  is a failure, not an acceptable result. Fix in this order: tighten spacing
  between blocks, reduce leading, trim margins, then drop the font 0.5pt.
- **No orphaned headings.** A heading must never sit alone at the foot of a
  page. Wrap heading-plus-first-child in `block(breakable: false)`.
- **Check the page count** after each compile. A one-pager that became two needs
  investigating, not accepting.
- **Don't insert `#pagebreak()` speculatively.** If the content already fits,
  you've manufactured a blank gap.
- **Don't put `#v(1fr)` before a footer** unless every page is guaranteed to
  overflow — it pushes the footer onto a page of its own.

## Multi-column traps

Typst's column primitives don't behave like CSS.

- **`#grid` cells break across pages independently.** A long left cell spills
  while a short right cell ends early, leaving a half-empty continuation page.
  Pre-split long lists into balanced halves yourself; don't hope Typst balances
  them.
- **`#columns(n, body)` is fixed layout, not auto-balancing.** If the body fits
  in one column's page height, column two stays empty.

## Where the finished PDF goes

Ask, or put it beside the source. Don't scatter output into whatever folder
happened to be current. If the user has a standard destination, use it and say
where it went.
