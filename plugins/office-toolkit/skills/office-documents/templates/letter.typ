// Standard school letter — one page, letterhead, signature block.
// Compile:  typst compile letter.typ letter.pdf
//
// For a mail-merge run, generate one .typ per recipient and compile in a loop.
// PowerShell:  Get-ChildItem *.typ | ForEach-Object { typst compile $_.Name ($_.BaseName + ".pdf") }

#let school  = "Example School"
#let address = "Street Address · City"
#let contact = "office@example-school.org · (000) 000-0000"

#let date      = "16 August 2026"
#let recipient = "Dear Mr and Mrs Adler,"
#let subject   = "Galil trip — outstanding consent form"

#let body = [
  We are writing about the Galil trip departing on 24 August. Our records show
  that we have not yet received Noa's signed consent form, which was due on
  Friday.

  We cannot confirm a place on the coach without it. If the form has already
  been sent, please let us know and we will check again at this end — it may
  simply have crossed with this letter.

  The form can be returned to the office in person, or scanned and emailed to
  the address at the top of this page. If anything about the trip is holding
  the decision up, please call and ask for the trips office; we would rather
  talk it through than chase paper.
]

#let signOff  = "With best wishes,"
#let signName = "M. Levinson"
#let signRole = "Office Administrator"

// ──────────────────────────────  STYLE  ──────────────────────────────

#let ink   = rgb("#1A1D1B")
#let muted = rgb("#5D665F")
#let hair  = rgb("#D3D8CF")

#set page(paper: "a4", margin: (x: 2.4cm, top: 2.0cm, bottom: 2.0cm))
// Noto Sans if present, else the universal fallbacks. A letter to a parent
// wants a neutral, professional face — not the dense one used for checklists.
#set text(font: ("Segoe UI", "Arial", "DejaVu Sans"), size: 11pt, fill: ink)
#set par(leading: 0.75em, justify: false, spacing: 1.15em)

#grid(columns: (1fr, auto), align: (left + bottom, right + bottom),
  [
    #text(15pt, weight: 700)[#school]
    #v(-4pt)
    #text(8.5pt, fill: muted)[#address]
  ],
  text(8.5pt, fill: muted)[#contact],
)
#v(6pt)
#line(length: 100%, stroke: 1.2pt + ink)
#v(20pt)

#text(9.5pt, fill: muted)[#date]
#v(14pt)
#text(11pt)[#recipient]
#v(10pt)
#text(11pt, weight: 700)[#subject]
#v(12pt)

#body

#v(22pt)
#text(11pt)[#signOff]
#v(30pt)
#line(length: 5.5cm, stroke: 0.5pt + hair)
#v(3pt)
#text(11pt, weight: 600)[#signName]
#v(-3pt)
#text(9pt, fill: muted)[#signRole]
