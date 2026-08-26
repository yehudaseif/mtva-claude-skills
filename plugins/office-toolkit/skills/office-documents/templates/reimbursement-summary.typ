// Reimbursement summary — the one-pager someone signs.
// Compile:  typst compile reimbursement-summary.typ reimbursement-summary.pdf
//
// Amounts are strings, not numbers, on purpose: a receipt that couldn't be read
// stays blank rather than becoming a guess. Never invent a figure to fill a row.

// ─────────────────────────────  CONTENT  ─────────────────────────────

#let school    = "Example School"
#let claimant  = "M. Levinson"
#let period    = "3–7 August 2026"
#let submitted = "10 August 2026"
#let currency  = "ILS"
#let policyCap = "200"          // per-item limit; blank string disables flagging

// (date, vendor, description, amount, flag)
// flag: "" | "over" | "duplicate" | "unreadable" | "foreign"
#let items = (
  ("03/08", "Supersol Deal",  "Kitchen supplies",        "128.60", ""),
  ("04/08", "Paz Yellow",     "Fuel, minibus",           "287.15", "over"),
  ("05/08", "Office Depot",   "Paper, markers, pouches", "204.80", "over"),
  ("05/08", "Cafe Neeman",    "Staff meeting",            "82.00", ""),
  ("05/08", "Cafe Neeman",    "Staff meeting",            "82.00", "duplicate"),
  ("06/08", "Home Center",    "Extension lead, tape",    "141.30", ""),
  ("06/08", "Egged",          "Group coach tickets",     "812.00", "over"),
  ("07/08", "Amazon.com",     "Microphone, SD card",      "71.49", "foreign"),
  ("07/08", "Mini Market",    "Sundries — receipt unreadable", "", "unreadable"),
)

#let claimedTotal = "1,737.34"   // sum of unflagged + approved rows only
#let note = "Two items exceed the per-item limit and need a signature before payment. One receipt could not be read and one appears to be a duplicate of the 05/08 cafe receipt — both are excluded from the total above."

// ──────────────────────────────  STYLE  ──────────────────────────────

#let ink    = rgb("#1A1D1B")
#let muted  = rgb("#5D665F")
#let hair   = rgb("#D3D8CF")
#let accent = rgb("#0E5D53")
#let warm   = rgb("#8C3B12")

#set page(paper: "a4", margin: (x: 1.9cm, top: 1.6cm, bottom: 1.4cm))
#set text(font: ("Segoe UI", "Arial", "DejaVu Sans"), size: 9.5pt, fill: ink)
#set par(leading: 0.55em)

#let kicker(body, col: muted) = text(7pt, fill: col, weight: 700, tracking: 0.1em)[#upper(body)]

#let flagLabel(f) = {
  if f == "over" { text(7.5pt, fill: warm, weight: 700)[OVER LIMIT] }
  else if f == "duplicate" { text(7.5pt, fill: warm, weight: 700)[DUPLICATE?] }
  else if f == "unreadable" { text(7.5pt, fill: warm, weight: 700)[UNREADABLE] }
  else if f == "foreign" { text(7.5pt, fill: warm, weight: 700)[#currency? ] }
  else { [] }
}

// ────────────────────────────  DOCUMENT  ─────────────────────────────

#grid(columns: (1fr, auto), align: (left + bottom, right + bottom),
  [
    #text(13pt, weight: 700)[#school]
    #v(-3pt)
    #kicker("Reimbursement summary")
  ],
  text(8pt, fill: muted)[Submitted #submitted],
)
#v(5pt)
#line(length: 100%, stroke: 1.2pt + ink)
#v(12pt)

#grid(columns: (1fr, 1fr, 1fr), column-gutter: 10pt,
  [#kicker("Claimant") #v(2pt) #text(11pt, weight: 600)[#claimant]],
  [#kicker("Period") #v(2pt) #text(11pt, weight: 600)[#period]],
  [#kicker("Currency") #v(2pt) #text(11pt, weight: 600)[#currency]],
)

#v(14pt)

#table(
  columns: (1.5cm, 3.6cm, 1fr, 2.1cm, 2.4cm),
  inset: (x: 5pt, y: 5pt),
  align: (left, left, left, right, left),
  stroke: (x, y) => (
    bottom: if y == 0 { 0.9pt + ink } else { 0.4pt + hair },
  ),
  table.header(
    text(7.5pt, weight: 700)[DATE],
    text(7.5pt, weight: 700)[VENDOR],
    text(7.5pt, weight: 700)[DESCRIPTION],
    text(7.5pt, weight: 700)[AMOUNT],
    text(7.5pt, weight: 700)[FLAG],
  ),
  ..items.map(i => (
    text(9pt)[#i.at(0)],
    text(9pt)[#i.at(1)],
    text(9pt, fill: if i.at(4) == "" { ink } else { muted })[#i.at(2)],
    text(9pt, weight: if i.at(4) == "" { 400 } else { 400 })[#i.at(3)],
    flagLabel(i.at(4)),
  )).flatten()
)

#v(10pt)

#grid(columns: (1fr, auto), column-gutter: 14pt,
  [
    #kicker("Notes", col: warm)
    #v(3pt)
    #text(8.5pt, fill: muted)[#note]
    #v(6pt)
    #text(8.5pt, fill: muted)[Per-item limit: #currency #policyCap.]
  ],
  block(width: 5.6cm)[
    #kicker("Approved for payment")
    #v(3pt)
    #line(length: 100%, stroke: 0.9pt + ink)
    #v(2pt)
    #text(11pt, weight: 700)[#currency #claimedTotal]
    #v(14pt)
    #line(length: 100%, stroke: 0.5pt + hair)
    #v(2pt)
    #text(7.5pt, fill: muted)[Signature]
    #v(12pt)
    #line(length: 100%, stroke: 0.5pt + hair)
    #v(2pt)
    #text(7.5pt, fill: muted)[Date]
  ],
)
