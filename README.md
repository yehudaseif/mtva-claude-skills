# MTVA Claude Skills

House Claude Code skills for admin staff. Three plugins, matched to the roles
covered in the onboarding session.

## Install

Add the marketplace once:

```bash
claude plugin marketplace add yehudaseif/mtva-claude-skills
```

Then install only what your job needs:

```bash
claude plugin install student-reports@mtva-skills      # attendance → PDF reports
claude plugin install footage-review@mtva-skills       # video transcription + indexing
claude plugin install classroom-materials@mtva-skills  # worksheets and answer keys
claude plugin install tva-newsletter@mtva-skills       # weekly MTVA + YTVA Constant Contact newsletters
```

Restart Claude Code. There is nothing to configure — describe what you want in
plain English and the right skill loads itself.

To update later, refresh the marketplace first, then the plugin — and note that
`update` needs the full `name@marketplace` form; a bare name fails with
"Plugin not found":

```bash
claude plugin marketplace update mtva-skills
claude plugin update footage-review@mtva-skills
```

To see what you have: `claude plugin list`.

## What's in each

### `student-reports`
Spreadsheet in, analysis and per-student PDFs out. Reads `.xlsx`/`.csv`, handles
the usual mess (merged headers, totals rows mixed in with students, inconsistent
name spellings), computes attendance rates against a threshold you set, and
renders one letterheaded PDF per student.

Two phases, deliberately separate: it reports the numbers and waits for you to
check them before generating anything. These documents go to parents.

Includes a debugged Typst report template with a native bar chart — edit
`templates/attendance-report.typ` once with your school's letterhead and colours.

**Needs:** `brew install typst`

### `footage-review`
Two skills. Everything runs locally — footage never leaves the machine.

**`face-roster`** answers "who is in this clip?". Enrol students from a few
reference photos each, then get a per-clip roster with timestamps and a
confidence mark on every row. Faces that match nobody are reported as unknown
and never snapped to the nearest name — attaching the wrong student's name to
footage is the failure that causes real harm, so the pipeline says "I don't
know" instead of guessing.

The enrolled database is biometric data about minors. Keep it on one machine,
don't sync it, and delete it at the end of the program year. Check that your
photo-release form actually covers biometric processing — a general release
often doesn't, and that's a form change rather than a code change.

**`footage-index`** transcribes the audio and builds a timestamped index of
what happens. Run both and join on filename: faces say *who*, the transcript
says *what*, and together you can find "the clip where Sara is being
interviewed".

**Needs:** `brew install ffmpeg uv`. First runs download the face model
(~300 MB) and Whisper weights (~460 MB), both cached after that.

### `classroom-materials`
A source text into worksheets, answer keys, differentiated reading-level
variants, vocabulary sets, and quizzes — as `.docx`, because teachers edit
these five minutes before the lesson.

The differentiated version is the point: same content and same answer key,
different access. It's the version nobody has time to make by hand.

**Needs:** nothing. The Word skill ships with Claude Code.

### `tva-newsletter`
The Friday MTVA and YTVA emails. Everything that never changes (header art,
colours, staff, contact, donate button, footer) is fixed in
`programs/mtva.json` / `programs/ytva.json`; staff drop the week's pieces into
`~/Documents/TVA Newsletter/<date> <parsha>/{MTVA,YTVA}/` and Claude builds the
email, hosts the photos, creates the Constant Contact draft and sends a test.
Scheduling the real send needs a person's go-ahead (`--confirm`).

**Needs:** a one-time setup — a free Constant Contact API key and a photo host.
See `plugins/tva-newsletter/skills/tva-newsletter/SETUP.md`. Plus `pip3 install pillow`.

## Not in here, on purpose

**Graphics and UI work** for programmers is covered by Anthropic's own plugin —
no house version needed:

```bash
claude plugin install frontend-design@claude-plugins-official
```

**Word, Excel, PowerPoint, PDF and chart-design skills ship with Claude Code.**
Nothing to install, and nothing to duplicate here.

## Ground rules these skills assume

- Student data stays on the machine it's already on.
- You read the permission prompt before approving a write.
- A human presses send on anything that reaches a parent.
- Spot-check two figures by hand before a batch of reports goes out.

## Adding a skill

A skill is a folder with a `SKILL.md` in it. The YAML `description` is the whole
triggering mechanism — it's what Claude reads to decide whether the skill is
relevant, so write it as the situations it applies to, not as a title.

```
plugins/<plugin-name>/
├── .claude-plugin/plugin.json
└── skills/<skill-name>/
    ├── SKILL.md          ← required; everything else is optional
    ├── references/       ← docs loaded only once the skill triggers
    ├── scripts/          ← code the skill can run
    └── templates/        ← files it can copy and fill
```

Add the plugin to `.claude-plugin/marketplace.json`, then check it before
pushing:

```bash
claude plugin validate . --strict
```

Bump the `version` in both `marketplace.json` and the plugin's `plugin.json`
when you change a skill, or installed copies won't pick up the update.
