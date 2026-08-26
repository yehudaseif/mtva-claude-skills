// Weekly notice sheet — one page for the board and the parent email.
// Compile:  typst compile notice-sheet.typ notice-sheet.pdf
//
// Switch `paper` to "a3" for the bulletin board; a4 is right for handouts and
// for pasting into email. Everything else scales from the two size variables.

#let paper = "a4"        // "a4" for handouts, "a3" for the board
#let base  = 11pt        // bump to 14pt when you switch to a3

// ─────────────────────────────  CONTENT  ─────────────────────────────

#let school   = "Example School"
#let weekOf   = "Week of 17–21 August 2026"
#let subtitle = "Parashat Ki Tavo"

// Left column
#let times = (
  ("Candle lighting",  "6:52 pm"),
  ("Shacharit",        "7:15 am daily"),
  ("Mincha",           "1:40 pm"),
  ("Shabbat ends",     "7:49 pm"),
)

#let schedule = (
  ("Mon",  "Normal timetable"),
  ("Tue",  "Year 10 tiyul — Old City. Depart 8:00, return 17:30"),
  ("Wed",  "Photographs, full uniform. Parent evening 19:30"),
  ("Thu",  "Normal timetable. Clubs finish 16:45"),
  ("Fri",  "Early finish, 12:30"),
)

// Right column
#let menu = (
  ("Mon", "Pasta bolognese · salad bar"),
  ("Tue", "Packed lunch — trip day"),
  ("Wed", "Schnitzel · rice · roasted vegetables"),
  ("Thu", "Fish and chips · peas"),
  ("Fri", "Soup · rolls · fruit"),
)

#let birthdays = (
  "Noa Adler (Mon)", "Eitan Roth (Wed)", "Tali Mizrahi (Fri)",
)

#let notices = (
  ("Trip forms", "Galil trip forms are due Friday. Six families still outstanding — the office will call."),
  ("Lost property", "Cleared at half term. Anything unclaimed goes to charity."),
  ("Parking", "Please don't use the neighbours' driveway at pickup. We've had two complaints."),
)

#let comingUp = (
  ("24 Aug",     "Galil trip departs, 07:00"),
  ("28 Aug",     "Reports issued to parents"),
  ("2 Sept",     "Term photographs, resit"),
)

#let footer = "Example School · office@example-school.org · (000) 000-0000"

// ──────────────────────────────  STYLE  ──────────────────────────────

#let ink    = rgb("#1A1D1B")
#let muted  = rgb("#5D665F")
#let hair   = rgb("#D3D8CF")
#let accent = rgb("#0E5D53")
#let warm   = rgb("#8C3B12")

#set page(
  paper: paper,
  margin: (x: 1.4cm, top: 1.2cm, bottom: 1.0cm),
  footer: context [
    #set text(base * 0.72, fill: muted)
    #line(length: 100%, stroke: 0.4pt + hair)
    #v(2pt)
    #align(center)[#footer]
  ],
)

// Segoe UI is the Windows default and always present there; Arial covers macOS
// and anywhere else. Run `typst fonts` before naming a different family —
// Typst warns and silently falls back on anything it can't find.
#set text(font: ("Segoe UI", "Arial", "DejaVu Sans"), size: base, fill: ink)
#set par(leading: 0.5em)

#let kicker(body, col: accent) = text(
  base * 0.72, fill: col, weight: 700, tracking: 0.1em,
)[#upper(body)]

// A titled block with a rule under the heading. breakable:false keeps the
// heading from orphaning at a page foot.
#let panel(title, body, col: accent) = block(breakable: false, width: 100%)[
  #kicker(title, col: col)
  #v(3pt)
  #line(length: 100%, stroke: 0.6pt + hair)
  #v(5pt)
  #body
  #v(base * 1.1)
]

// Two-column row: label left, value right. Used for times, schedule, menu.
#let row(label, value, labelWidth: 2.9cm) = grid(
  columns: (labelWidth, 1fr),
  column-gutter: 6pt,
  text(weight: 700)[#label],
  text(fill: ink)[#value],
)

// ────────────────────────────  DOCUMENT  ─────────────────────────────

#grid(
  columns: (1fr, auto),
  align: (left + bottom, right + bottom),
  [
    #text(base * 2.1, weight: 700)[#school]
    #v(-3pt)
    #text(base * 0.95, fill: accent, weight: 600)[#weekOf]
  ],
  text(base * 0.95, fill: muted, style: "italic")[#subtitle],
)
#v(5pt)
#line(length: 100%, stroke: 1.4pt + ink)
#v(base * 1.2)

// Both columns carry roughly equal content on purpose — Typst breaks grid
// cells independently, so wildly unbalanced columns produce a half-empty
// second page. Keep them close in height.
#grid(
  columns: (1fr, 1fr),
  column-gutter: 1.1cm,
  [
    #panel("Times")[
      #for t in times [
        #row(t.at(0), t.at(1))
        #v(2.5pt)
      ]
    ]

    #panel("This week")[
      #for s in schedule [
        #row(s.at(0), s.at(1), labelWidth: 1.2cm)
        #v(3pt)
      ]
    ]

    #panel("Coming up")[
      #for c in comingUp [
        #row(c.at(0), c.at(1), labelWidth: 2.9cm)
        #v(3pt)
      ]
    ]
  ],
  [
    #panel("Lunch")[
      #for m in menu [
        #row(m.at(0), m.at(1), labelWidth: 1.2cm)
        #v(2.5pt)
      ]
    ]

    #panel("Birthdays", col: warm)[
      #text(fill: ink)[#birthdays.join(" · ")]
    ]

    #panel("Notices", col: warm)[
      #for n in notices [
        #block(breakable: false)[
          #text(weight: 700)[#n.at(0)]
          #v(1pt)
          #text(base * 0.94, fill: muted)[#n.at(1)]
        ]
        #v(5pt)
      ]
    ]
  ],
)
