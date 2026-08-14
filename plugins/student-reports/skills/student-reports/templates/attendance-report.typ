// Attendance report — one page per student.
// Fill in the DATA block below, then: typst compile this.typ out.pdf
//
// Design intent: factual, neutral, readable by a parent. No warning language,
// no editorialising. The advisor adds meaning in the comments box.

// ─────────────────────────────  DATA  ─────────────────────────────

#let school = (
  name:    "Your School Name",
  address: "Street Address · City",
  contact: "office@school.org · (000) 000-0000",
)

#let student = (
  name:    "Sara Levi",
  group:   "Year 10 · Kevutza Aleph",
  advisor: "R. Cohen",
)

#let period    = "September 2025 – June 2026"
#let generated = "14 August 2026"
#let threshold = 85    // percent; shown on the chart as a reference line

#let totals = (
  present: 142,
  absent:  24,
  late:    8,
  total:   174,
)

// (label, attendance rate 0.0–1.0)
#let monthly = (
  ("Sep", 0.98), ("Oct", 0.95), ("Nov", 0.91), ("Dec", 0.72),
  ("Jan", 0.88), ("Feb", 0.94), ("Mar", 0.79), ("Apr", 0.86),
  ("May", 0.90), ("Jun", 0.93),
)

// Dates missed. Group consecutive runs — consecutive absence usually means
// illness or family travel, and listing it as a run says so without comment.
#let missed = (
  "8–12 Dec",  "19 Dec",   "6 Jan",   "3–5 Mar",
  "17 Mar",    "2 Apr",    "28 May",
)

// ────────────────────────────  STYLE  ─────────────────────────────

#let ink    = rgb("#1A1D1B")
#let muted  = rgb("#6A736C")
#let hair   = rgb("#D3D8CF")
#let accent = rgb("#1C5674")

#set page(
  paper: "a4",
  margin: (x: 2.0cm, y: 1.8cm),
  footer: context [
    #set text(7.5pt, fill: muted)
    #line(length: 100%, stroke: 0.4pt + hair)
    #v(2pt)
    #grid(
      columns: (1fr, auto),
      align(left)[#school.name — attendance record for #student.name],
      align(right)[Page #counter(page).display()],
    )
  ],
)

// Both families are present on staff macs and on most Linux boxes, so this
// compiles without a fallback warning. Both carry Hebrew glyphs. If you add a
// family here, run `typst fonts` first — Typst warns on any name it can't find.
#set text(font: ("Helvetica Neue", "DejaVu Sans"), size: 9.5pt, fill: ink)
#set par(leading: 0.62em, justify: false)

#let label(body) = text(7.5pt, fill: muted, weight: 600, tracking: 0.08em)[#upper(body)]

#let stat(value, name) = block[
  #text(19pt, weight: 600, fill: ink)[#value]
  #v(-4pt)
  #label(name)
]

// Native bar chart. No external plotting — an embedded PNG would not match
// the document's type and reads as pasted in.
// The y-axis starts at zero. Do not "zoom in" to dramatise a dip.
#let bar-chart(data, h: 2.9cm) = {
  block(width: 100%, {
    grid(
      columns: (1fr,) * data.len(),
      column-gutter: 6pt,
      ..data.map(d => {
        let name = d.at(0)
        let v    = d.at(1)
        let low  = v < (threshold / 100)
        stack(
          dir: ttb,
          spacing: 5pt,
          box(height: h, width: 100%, align(bottom + center,
            stack(
              dir: ttb,
              spacing: 3pt,
              text(6.8pt, fill: if low { accent } else { muted })[#calc.round(v * 100)],
              rect(
                width: 100%,
                height: h * v * 0.82,
                fill: if low { accent } else { accent.lighten(58%) },
                radius: (top: 1pt),
              ),
            )
          )),
          align(center, text(7.2pt, fill: muted)[#name]),
        )
      })
    )
  })
}

// ───────────────────────────  DOCUMENT  ───────────────────────────

// Letterhead
#grid(
  columns: (1fr, auto),
  align: (left + bottom, right + bottom),
  [
    #text(13pt, weight: 600)[#school.name]
    #v(-3pt)
    #text(7.5pt, fill: muted)[#school.address]
  ],
  text(7.5pt, fill: muted)[#school.contact],
)

#v(6pt)
#line(length: 100%, stroke: 1.2pt + ink)
#v(14pt)

// Title + who
#block(breakable: false)[
  #label("Attendance record")
  #v(2pt)
  #text(22pt, weight: 600)[#student.name]
  #v(2pt)
  #text(9pt, fill: muted)[#student.group  ·  Advisor: #student.advisor]
  #v(1pt)
  #text(9pt, fill: muted)[Reporting period: #period]
]

#v(16pt)

// Headline figures
#let rate = totals.present / totals.total
#grid(
  columns: (1fr, 1fr, 1fr, 1fr),
  column-gutter: 10pt,
  stat[#calc.round(rate * 100)%][Attendance rate],
  stat[#totals.present][Days present],
  stat[#totals.absent][Days absent],
  stat[#totals.late][Late arrivals],
)

#v(4pt)
#line(length: 100%, stroke: 0.4pt + hair)
#v(14pt)

// Chart
#block(breakable: false)[
  #label("By month")
  #v(8pt)
  #bar-chart(monthly)
  #v(4pt)
  #text(7.5pt, fill: muted)[
    Percentage of scheduled days attended. Months below the #threshold% reference
    threshold are shown in full colour.
  ]
]

#v(16pt)

// Dates missed
#block(breakable: false)[
  #label("Days missed")
  #v(7pt)
  #grid(
    columns: (1fr,) * 4,
    column-gutter: 8pt,
    row-gutter: 5pt,
    ..missed.map(d => text(9pt)[#d]),
  )
  #v(7pt)
  #text(7.5pt, fill: muted)[
    Consecutive days are shown as a single range.
  ]
]

#v(18pt)

// Advisor comments — the human adds the meaning.
#block(breakable: false)[
  #label("Advisor comments")
  #v(7pt)
  #rect(
    width: 100%,
    height: 3.4cm,
    stroke: 0.5pt + hair,
    radius: 2pt,
    inset: 10pt,
  )[]
  #v(7pt)
  #text(7.5pt, fill: muted)[
    Generated #generated. This record states attendance only. Please contact
    #student.advisor with any question about the figures or the context behind
    them.
  ]
]
