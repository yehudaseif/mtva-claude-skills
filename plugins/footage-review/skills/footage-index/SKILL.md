---
name: footage-index
description: Review video footage without scrubbing timelines. Transcribes clips locally with ffmpeg and Whisper, builds a timestamped searchable index of a whole folder, flags clips where student names are spoken, and cuts clips and stills by timestamp. Use when the user mentions footage, video review, clips, recordings, selects, b-roll, or asks what happens in a video.
---

# Footage Index

Hours of video become a searchable text file. After that you search for the
moment instead of scrubbing for it.

Everything runs on this machine. Footage of students never leaves it, and that
is the point — say so if the user asks why this isn't a cloud service.

## Pre-flight

```bash
command -v ffmpeg >/dev/null || brew install ffmpeg   # also: ffprobe
command -v uv     >/dev/null || brew install uv
```

On Linux: `sudo apt install ffmpeg` and see astral.sh/uv for `uv`.

The first transcription downloads Whisper weights — about 460 MB for the
`small` model, cached afterwards. Warn the user before starting a long batch
so a slow first clip isn't mistaken for a hang.

## Transcribing

`scripts/index_footage.py` handles one file: strips the audio, normalises it,
transcribes it, and emits JSON with timestamped segments. Run it under `uv` so
the heavy dependencies never touch the system Python:

```bash
uv run --with openai-whisper --with torch python scripts/index_footage.py \
  --file "clip.mp4" --model small --vocab vocab.txt --json "clip.json"
```

For a folder, loop, and **skip files already done** so an interrupted batch
resumes instead of restarting:

```bash
mkdir -p .transcripts
for f in *.mp4 *.mov *.MP4; do
  [ -e "$f" ] || continue
  out=".transcripts/$(basename "${f%.*}").json"
  [ -s "$out" ] && { echo "skip $f"; continue; }
  uv run --with openai-whisper --with torch python scripts/index_footage.py \
    --file "$f" --model small --vocab vocab.txt --json "$out"
done
```

Run one clip first and read the result before launching the batch. A wrong
`--language` or a silent audio track is much cheaper to find on clip 1 than on
clip 40.

### The vocabulary file is the biggest quality lever

Whisper guesses at proper nouns. Given a list, it stops guessing. Build a
`vocab.txt` with one term per line — staff and student names, place names,
program vocabulary, Hebrew terms in the transliteration you want on the page:

```
Sara Levi
Kevutza Aleph
Har Herzl
madrich
tiyul
```

Keep it under about 40 terms. Whisper's prompt is capped and a long list
silently truncates. Ask the user for the names likely to appear rather than
inventing spellings — the whole point is getting *their* spelling.

### Model sizing

`small` is the working default. Go to `medium` for noisy field audio, heavy
accents, or Hebrew. `tiny` is for checking the pipeline works, not for output
anyone reads. If a transcript comes back suspiciously short for a long clip,
that's the signal to escalate the model, not to accept it.

## Building the index

Once the JSONs exist, write one markdown file for the whole folder. This file
is the deliverable — more useful than the footage, and the thing people
actually search later.

For each clip: filename, duration, and a timestamped summary. Summarise in your
own words at roughly one line per 30–60 seconds of footage; do not paste the
raw transcript into the index. Keep the JSONs alongside for exact quotes.

```markdown
## tiyul-day3.mp4 — 12:04
- **00:00** Bus arrival, general noise, no usable audio
- **01:15** Sara Levi briefs the group on the route
- **04:12** Student interview — favourite part of the trip *(good for newsletter)*
- **09:40** Group singing at the lookout
```

Mark anything genuinely usable — a clean interview answer, a good group shot —
because that is what someone is looking for when they come back to this file.

## Flagging names

When asked to flag clips where students are named, search the segment text and
report **filename plus timestamp** so a human can check the moment. Do not
delete, mute, or edit anything on your own initiative — flagging is the task,
and a person decides what happens next.

Report a plain count first ("6 of 14 clips name a student"), then the list.

## Cutting clips and stills

Stream-copy for speed and no re-encode quality loss:

```bash
# 20-second clip from 4:12
ffmpeg -nostdin -ss 00:04:12 -i in.mp4 -t 20 -c copy out.mp4

# single still at 4:20
ffmpeg -nostdin -ss 00:04:20 -i in.mp4 -frames:v 1 -q:v 2 still.jpg

# contact sheet, 4x4 grid of thumbnails across the whole clip
ffmpeg -nostdin -i in.mp4 -vf "fps=1/30,scale=320:-1,tile=4x4" -frames:v 1 sheet.jpg
```

`-c copy` cuts at the nearest keyframe, so the start can land up to a couple of
seconds off. When the cut has to be frame-accurate, re-encode instead:
`-c:v libx264 -c:a aac`. Mention the tradeoff rather than silently picking.

**Never overwrite the original.** Write cuts and stills to a separate output
folder. `ffmpeg -y` pointed at a source file destroys footage that may be the
only copy.

## Reporting back

Lead with what the user can act on — how many clips, total runtime, where the
index is, and the two or three moments actually worth their attention. The
per-clip detail goes in the file, not in the reply.
