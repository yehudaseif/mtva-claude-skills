#!/usr/bin/env python3
"""Who appears in this clip? Samples frames, matches faces against an enrolled
database, and reports a per-clip roster with timestamps.

    uv run --with insightface --with onnxruntime --with opencv-python-headless \
      python identify_faces.py --file clip.mp4 --db faces.npz --json roster.json

Design rule: a face below the threshold is reported as UNKNOWN. It is never
snapped to the nearest name. Attaching the wrong student's name to footage is
the failure that actually causes harm here, so the pipeline is built to say
"I don't know" instead of guessing.
"""

import argparse
import json
import os
import sys

import cv2
import numpy as np

# Cosine similarity between L2-normalised ArcFace embeddings.
# ~0.45 is a conservative same-identity threshold for buffalo_l. Raise it if you
# see wrong names; lower it only after checking the review list by eye.
DEFAULT_THRESHOLD = 0.45


def log(msg):
    print(f"[identify] {msg}", file=sys.stderr, flush=True)


def hhmmss(seconds):
    s = int(seconds)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", required=True, help="video file")
    ap.add_argument("--db", required=True, help="faces.npz from enroll_faces.py")
    ap.add_argument("--every", type=float, default=2.0,
                    help="sample a frame every N seconds (default 2.0)")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                    help=f"match threshold 0-1 (default {DEFAULT_THRESHOLD})")
    ap.add_argument("--min-face", type=int, default=60,
                    help="ignore faces narrower than this many pixels; "
                         "background faces match unreliably")
    ap.add_argument("--det-size", type=int, default=640)
    ap.add_argument("--json", default=None, help="write JSON here")
    args = ap.parse_args()

    for path in (args.file, args.db):
        if not os.path.isfile(path):
            sys.exit(f"error: no such file: {path}")

    db = np.load(args.db, allow_pickle=False)
    names, vectors = list(db["names"]), db["vectors"]
    log(f"{len(names)} enrolled: {', '.join(names[:6])}"
        f"{'…' if len(names) > 6 else ''}")

    cap = cv2.VideoCapture(args.file)
    if not cap.isOpened():
        sys.exit(f"error: could not open {args.file}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = total / fps if total else None
    step = max(1, int(round(fps * args.every)))

    from insightface.app import FaceAnalysis  # noqa: PLC0415
    log("loading model (first run downloads ~300 MB)")
    app = FaceAnalysis(name="buffalo_l", allowed_modules=["detection", "recognition"])
    app.prepare(ctx_id=0, det_size=(args.det_size, args.det_size))

    log(f"sampling every {args.every}s of "
        f"{hhmmss(duration) if duration else 'unknown length'}")

    seen = {}          # name -> aggregated hits
    unknown_hits = []  # timestamps where a face matched nobody
    frames_sampled = 0
    idx = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step:
            idx += 1
            continue
        idx += 1
        frames_sampled += 1
        t = (idx - 1) / fps

        faces = [f for f in app.get(frame)
                 if (f.bbox[2] - f.bbox[0]) >= args.min_face]

        for f in faces:
            sims = vectors @ f.normed_embedding      # both L2-normalised
            best = int(np.argmax(sims))
            score = float(sims[best])

            if score < args.threshold:
                unknown_hits.append({"timecode": hhmmss(t),
                                     "best_guess": str(names[best]),
                                     "similarity": round(score, 3)})
                continue

            name = str(names[best])
            rec = seen.setdefault(name, {
                "name": name, "frames": 0, "best_similarity": 0.0,
                "first_seen": t, "last_seen": t, "timecodes": [],
            })
            rec["frames"] += 1
            rec["best_similarity"] = max(rec["best_similarity"], score)
            rec["first_seen"] = min(rec["first_seen"], t)
            rec["last_seen"] = max(rec["last_seen"], t)
            if len(rec["timecodes"]) < 40:
                rec["timecodes"].append(hhmmss(t))

    cap.release()

    roster = sorted(seen.values(), key=lambda r: -r["frames"])
    for r in roster:
        r["first_seen"] = hhmmss(r["first_seen"])
        r["last_seen"] = hhmmss(r["last_seen"])
        r["best_similarity"] = round(r["best_similarity"], 3)
        # A single hit is usually a mis-detection or a passer-by, not presence.
        r["confidence"] = ("firm" if r["frames"] >= 3 and r["best_similarity"] >= 0.55
                           else "check")

    payload = {
        "file": os.path.abspath(args.file),
        "filename": os.path.basename(args.file),
        "duration": hhmmss(duration) if duration else None,
        "frames_sampled": frames_sampled,
        "sample_interval_seconds": args.every,
        "threshold": args.threshold,
        "enrolled_count": len(names),
        "roster": roster,
        "unknown_face_count": len(unknown_hits),
        "unknown_samples": unknown_hits[:20],
    }

    out = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            fh.write(out + "\n")
    else:
        print(out)

    print(f"\n{payload['filename']} — {frames_sampled} frames sampled", file=sys.stderr)
    if roster:
        for r in roster:
            mark = "✔" if r["confidence"] == "firm" else "?"
            print(f"  {mark} {r['name']:<26} {r['frames']:>3} frames  "
                  f"best {r['best_similarity']:.2f}  "
                  f"{r['first_seen']}–{r['last_seen']}", file=sys.stderr)
    else:
        print("  no enrolled person identified", file=sys.stderr)
    if unknown_hits:
        print(f"  · {len(unknown_hits)} face sightings matched nobody enrolled",
              file=sys.stderr)

    if any(r["confidence"] == "check" for r in roster):
        print("\n  Rows marked ? are weak — few frames or low similarity. "
              "Check those by eye before using this roster.", file=sys.stderr)


if __name__ == "__main__":
    main()
