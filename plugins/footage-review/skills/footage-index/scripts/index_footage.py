#!/usr/bin/env python3
"""Transcribe one video/audio file into timestamped segments.

Everything runs locally: ffmpeg strips and normalises the audio, Whisper
transcribes it. No footage leaves the machine.

Run it under uv so the heavy dependencies stay out of the system Python:

    uv run --with openai-whisper --with torch \
      python index_footage.py --file clip.mp4 --json clip.json

Emits JSON on stdout (or to --json) and a human-readable progress line to
stderr, so stdout stays pipeable.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

SAMPLE_RATE = 16000


def log(msg):
    print(f"[index_footage] {msg}", file=sys.stderr, flush=True)


def require(binary):
    if shutil.which(binary) is None:
        sys.exit(
            f"error: '{binary}' not found on PATH.\n"
            f"Install it with:  brew install {binary}   (macOS)\n"
            f"                  sudo apt install {binary}   (Debian/Ubuntu)"
        )


def probe_duration(path):
    """Seconds as float, or None if ffprobe can't tell."""
    if shutil.which("ffprobe") is None:
        return None
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return float(out)
    except (subprocess.CalledProcessError, ValueError):
        return None


def extract_audio(src, dest):
    """16 kHz mono WAV, loudness-normalised.

    Field recordings — a phone at the back of a room, wind on a tiyul — are
    quiet and uneven. loudnorm plus a high-pass to kill rumble makes a large
    difference to what Whisper returns. This is the same preprocessing chain
    that fixed short-return transcriptions on WhatsApp voice notes.
    """
    subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-i", src,
         "-vn",
         "-af", "highpass=f=80,loudnorm=I=-16:TP=-1.5:LRA=11",
         "-ac", "1", "-ar", str(SAMPLE_RATE),
         "-c:a", "pcm_s16le", dest],
        capture_output=True, check=True,
    )


def hhmmss(seconds):
    s = int(seconds)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", required=True, help="video or audio file")
    ap.add_argument("--model", default="small",
                    help="tiny|base|small|medium|large (default: small). "
                         "First use downloads the weights (~460 MB for small).")
    ap.add_argument("--language", default=None,
                    help="ISO code e.g. 'en', 'he'. Omit to auto-detect.")
    ap.add_argument("--vocab", default=None,
                    help="text file of names/terms to bias decoding toward — "
                         "staff names, place names, program vocabulary")
    ap.add_argument("--json", default=None, help="write JSON here instead of stdout")
    args = ap.parse_args()

    if not os.path.isfile(args.file):
        sys.exit(f"error: no such file: {args.file}")

    require("ffmpeg")

    try:
        import whisper  # noqa: PLC0415
    except ImportError:
        sys.exit(
            "error: the 'whisper' module is not available.\n"
            "Run this script under uv so the dependencies are supplied:\n"
            "  uv run --with openai-whisper --with torch python "
            + os.path.basename(__file__) + " --file ...")

    duration = probe_duration(args.file)
    log(f"{os.path.basename(args.file)} "
        f"({hhmmss(duration) if duration else 'unknown length'})")

    prompt = None
    if args.vocab and os.path.isfile(args.vocab):
        terms = [t.strip() for t in open(args.vocab, encoding="utf-8")
                 if t.strip() and not t.startswith("#")]
        if terms:
            # Whisper's initial_prompt is capped around 224 tokens; a long list
            # silently truncates, so keep vocab files short and specific.
            prompt = ", ".join(terms)[:900]
            log(f"biasing toward {len(terms)} vocabulary terms")

    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "audio.wav")
        log("extracting and normalising audio")
        try:
            extract_audio(args.file, wav)
        except subprocess.CalledProcessError as e:
            sys.exit(f"error: ffmpeg failed on {args.file}\n"
                     f"{e.stderr.decode('utf-8', 'replace')[-800:]}")

        if os.path.getsize(wav) < 1024:
            sys.exit(f"error: {args.file} produced no audio — it may be a "
                     f"silent or video-only file")

        log(f"transcribing with the '{args.model}' model")
        model = whisper.load_model(args.model)
        result = model.transcribe(
            wav,
            language=args.language,
            initial_prompt=prompt,
            condition_on_previous_text=False,  # stops runaway repetition loops
            temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),  # fallback ladder
            verbose=False,
        )

    segments = [
        {
            "start": round(s["start"], 2),
            "end": round(s["end"], 2),
            "timecode": hhmmss(s["start"]),
            "text": s["text"].strip(),
        }
        for s in result.get("segments", [])
        if s["text"].strip()
    ]

    payload = {
        "file": os.path.abspath(args.file),
        "filename": os.path.basename(args.file),
        "duration_seconds": round(duration, 2) if duration else None,
        "duration": hhmmss(duration) if duration else None,
        "language": result.get("language"),
        "model": args.model,
        "segment_count": len(segments),
        "text": result.get("text", "").strip(),
        "segments": segments,
    }

    out = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            fh.write(out + "\n")
        log(f"wrote {args.json} — {len(segments)} segments")
    else:
        print(out)

    if not segments:
        log("WARNING: no speech found. If the clip definitely contains speech, "
            "retry with --model medium, or check that the audio track isn't silent.")


if __name__ == "__main__":
    main()
