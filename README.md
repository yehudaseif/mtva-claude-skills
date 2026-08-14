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
```

Restart Claude Code. There is nothing to configure — describe what you want in
plain English and the right skill loads itself.

To update later: `claude plugin update <name>`. To see what you have:
`claude plugin list`.

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
Turns a folder of clips into a searchable timestamped index. Transcribes
locally with ffmpeg and Whisper — footage never leaves the machine — flags
clips where student names are spoken, and cuts clips and stills by timestamp.

The index file is the real deliverable. You stop scrubbing timelines and start
searching text.

**Needs:** `brew install ffmpeg uv`. First run downloads Whisper weights (~460 MB,
cached after that).

### `classroom-materials`
A source text into worksheets, answer keys, differentiated reading-level
variants, vocabulary sets, and quizzes — as `.docx`, because teachers edit
these five minutes before the lesson.

The differentiated version is the point: same content and same answer key,
different access. It's the version nobody has time to make by hand.

**Needs:** nothing. The Word skill ships with Claude Code.

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
