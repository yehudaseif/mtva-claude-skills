---
name: face-roster
description: Identify which enrolled students appear in a video clip, by face, and produce a per-clip roster with timestamps. Builds a named face database from reference photos and matches footage against it locally. Use when the user asks who is in a clip, wants footage logged by who appears, wants all footage of a particular student, or mentions face recognition or identifying people in video.
---

# Face Roster

Answers "who is in this clip?" for a folder of footage, so it can be logged and
filed as it comes in.

Runs entirely on this machine — detection and matching both local, nothing
uploaded. Say so if anyone asks; it is the main reason to do it this way rather
than with a hosted service.

## Before the first run — the part that isn't code

The enrolled database is a set of face templates of identifiable minors. That
is biometric data, and in several jurisdictions it is a special category
needing specific parental consent, which a general photo-release form often
does **not** cover.

Before building a database for a new cohort, ask the user — once, plainly — 
whether consent covers biometric processing. If they don't know, say that the
answer lives in the release form, not in the code, and offer to continue with
a database you both treat as provisional. Do not lecture, do not repeat it
every session, and do not refuse to proceed when they say it's handled.

Practical handling, which the scripts assume:

- Keep `faces.npz` and the reference photos on one machine. Don't sync them to
  a shared drive, and don't commit them to a repo.
- Delete both at the end of the program year. Put the deletion date in the
  folder name so it's obvious when it's overdue.
- If a family withdraws consent, delete that person's folder and rebuild the
  database. Rebuilding is cheap; it takes seconds.
- The roster output is a working note, not a record to file against a student.

## Pre-flight

```bash
command -v ffmpeg >/dev/null || brew install ffmpeg
command -v uv     >/dev/null || brew install uv
```

Every script runs under `uv` so nothing installs into the system Python:

```bash
uv run --with insightface --with onnxruntime --with opencv-python-headless \
  python scripts/<script>.py ...
```

First run downloads the `buffalo_l` model (~300 MB) to `~/.insightface`, cached
after that. On Apple silicon, CoreML acceleration is picked up automatically.
A `CUDAExecutionProvider is not available` warning on a Mac is expected and
harmless — do not go chasing it.

## Step 1 — enrol

One folder per student, 2–5 photos each:

```
photos/
  Sara Levi/
    sept-headshot.jpg
    tiyul-candid.jpg
  David Cohen/
    ...
```

```bash
uv run --with insightface --with onnxruntime --with opencv-python-headless \
  python scripts/enroll_faces.py --photos photos/ --out faces.npz
```

**Reference photo quality is the whole ballgame.** A weak template produces
wrong names downstream, and no threshold tuning rescues it. What matters, in
order:

1. **More than one photo.** A single photo bakes in that day's lighting and
   angle. Two or three across different days is a large accuracy jump — the
   script marks anyone enrolled from one photo with `~` for exactly this reason.
2. **One face per photo.** A photo with a friend in it is ambiguous, and the
   script refuses it rather than guessing which face is the student. Crop it.
3. **Face reasonably large and roughly front-on.** Sunglasses, heavy shadow and
   sharp profiles all weaken a template.

Tight crops are fine — the script pads them automatically and reports
`tight crop, detected after padding`. A cropped ID photo enrols correctly.

**Read the enrolment report before going further.** Anyone listed under `!!`
built no template and will come back as `unknown` in every clip, which reads
identically to "wasn't there". That distinction matters, so fix it now.

## Step 2 — identify

```bash
uv run --with insightface --with onnxruntime --with opencv-python-headless \
  python scripts/identify_faces.py --file clip.mp4 --db faces.npz \
  --every 2 --json rosters/clip.json
```

For a folder, loop and skip anything already done so an interrupted run
resumes:

```bash
mkdir -p rosters
for f in *.mp4 *.mov; do
  [ -e "$f" ] || continue
  out="rosters/$(basename "${f%.*}").json"
  [ -s "$out" ] && continue
  uv run --with insightface --with onnxruntime --with opencv-python-headless \
    python scripts/identify_faces.py --file "$f" --db faces.npz --json "$out"
done
```

`--every 2` samples a frame every two seconds, which is plenty for "who is in
this clip". Drop to `--every 5` for long static footage; go to `--every 1` only
when people pass through quickly.

### Reading the output

Each person comes back with a frame count, a best similarity, and a
`confidence` of `firm` or `check`:

- **`firm`** — three or more frames and similarity ≥ 0.55. Safe to log.
- **`check`** — one or two frames, or a borderline score. Usually a passer-by,
  a half-turned head, or a genuine mismatch. **Look at these by eye.**

`unknown_face_count` is faces that matched nobody. A high number is normal and
healthy: other people's children, staff, members of the public. It is not an
error, and it is much better than the alternative.

**A face below threshold is never snapped to the nearest name.** Attaching the
wrong student's name to footage is the failure that actually causes harm here,
so the pipeline says "unknown" instead of guessing. Do not lower `--threshold`
to make unknowns go away — that manufactures false positives. If someone is
consistently missed, fix their reference photos instead.

Verified behaviour on a six-person test clip with two people enrolled: both
enrolled matched at 0.95+, and all four strangers came back unknown with no
name attached.

## Step 3 — the roster file

The deliverable is one markdown file for the folder. That file, not the
footage, is what people search later.

```markdown
## tiyul-day3.mp4 — 12:04
**Present:** Sara Levi (00:00–09:12) · David Cohen (04:10–11:58)
**Check:** Miriam Katz — 2 frames at 07:30, low score
**Unknown faces:** 14 sightings
```

Lead with a count when reporting back — "11 of 14 clips have a confirmed
roster; 3 need eyes on them" — then the detail. Never present a `check` row as
settled fact.

## Combining with the audio index

Run the `footage-index` skill on the same folder and join on filename. Faces
say *who*; the transcript says *what is happening*. Together you can answer
"find the clip where Sara is being interviewed", which neither signal answers
alone. When both exist, build one merged index rather than two.

## Don't

- Don't lower the threshold to reduce unknowns.
- Don't treat a roster as attendance. Someone off-camera is not absent, and
  this is not an attendance system — say so if asked to use it as one.
- Don't delete, blur, or edit footage on your own initiative. Flag and let a
  person decide.
- Don't copy `faces.npz` anywhere. If a second machine needs it, that's a
  decision for the user, not a convenience step.
