#!/usr/bin/env python3
"""Build a named face database from reference photos.

Everything runs locally. The database this writes is biometric data about
identifiable minors — treat the output file with the same care as a medical
record, keep it on one machine, and delete it when the program ends.

    photos/
      Sara Levi/       one folder per student, 2-5 clear photos each
        img1.jpg
        img2.jpg
      David Cohen/
        ...

Run:

    uv run --with insightface --with onnxruntime --with opencv-python-headless \
      python enroll_faces.py --photos photos/ --out faces.npz

First run downloads the buffalo_l model (~300 MB), cached to ~/.insightface.
"""

import argparse
import os
import sys

import cv2
import numpy as np

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic")


def log(msg):
    print(f"[enroll] {msg}", file=sys.stderr, flush=True)


def detect_with_retry(app, img, min_face):
    """Detect faces, retrying on a padded copy for tightly-cropped headshots.

    Staff supply reference photos cropped hard to the face — from an ID card, a
    yearbook, a passport photo. The detector needs margin around a face and
    finds nothing in a 112x112 crop, so a perfectly good photo silently fails
    to enrol. Upscaling alone does not fix it; the border does.
    """
    faces = [f for f in app.get(img) if (f.bbox[2] - f.bbox[0]) >= min_face]
    if faces:
        return faces, False

    h, w = img.shape[:2]
    scale = max(1.0, 360.0 / max(1, min(h, w)))
    work = img if scale == 1.0 else cv2.resize(
        img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    border = int(0.35 * min(work.shape[:2]))
    padded = cv2.copyMakeBorder(work, border, border, border, border,
                                cv2.BORDER_REPLICATE)

    faces = [f for f in app.get(padded)
             if (f.bbox[2] - f.bbox[0]) >= min_face * scale]
    return faces, bool(faces)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--photos", required=True,
                    help="directory of per-person subfolders")
    ap.add_argument("--out", default="faces.npz", help="output database")
    ap.add_argument("--det-size", type=int, default=640,
                    help="detector input size (default 640)")
    ap.add_argument("--min-face", type=int, default=80,
                    help="ignore reference faces smaller than this many pixels "
                         "wide; small faces make unreliable templates")
    args = ap.parse_args()

    if not os.path.isdir(args.photos):
        sys.exit(f"error: not a directory: {args.photos}")

    from insightface.app import FaceAnalysis  # noqa: PLC0415

    log("loading model (first run downloads ~300 MB)")
    app = FaceAnalysis(name="buffalo_l", allowed_modules=["detection", "recognition"])
    app.prepare(ctx_id=0, det_size=(args.det_size, args.det_size))

    people = sorted(d for d in os.listdir(args.photos)
                    if os.path.isdir(os.path.join(args.photos, d))
                    and not d.startswith("."))
    if not people:
        sys.exit(f"error: no per-person subfolders found in {args.photos}\n"
                 f"Expected {args.photos}/<Student Name>/photo.jpg")

    names, vectors, report = [], [], []

    for person in people:
        pdir = os.path.join(args.photos, person)
        images = sorted(f for f in os.listdir(pdir)
                        if f.lower().endswith(IMAGE_EXT))
        embeddings, skipped = [], []

        for fname in images:
            path = os.path.join(pdir, fname)
            img = cv2.imread(path)
            if img is None:
                skipped.append((fname, "unreadable"))
                continue

            faces, rescued = detect_with_retry(app, img, args.min_face)
            if rescued:
                log(f"{person}/{fname}: tight crop, detected after padding")

            if len(faces) == 0:
                skipped.append((fname, "no face detected"))
                continue
            if len(faces) > 1:
                # A reference photo with two people in it is ambiguous, and
                # guessing which one is the student is exactly the mistake that
                # poisons a template. Make the human crop it.
                skipped.append((fname, f"{len(faces)} faces — crop to one"))
                continue

            emb = faces[0].normed_embedding
            embeddings.append(emb)

        if not embeddings:
            report.append((person, 0, len(images), skipped))
            log(f"SKIPPED {person!r} — no usable reference photo")
            continue

        # Mean of L2-normalised embeddings, renormalised. Averaging several
        # photos across lighting and angle gives a far more robust template
        # than any single shot.
        template = np.mean(embeddings, axis=0)
        template = template / np.linalg.norm(template)

        names.append(person)
        vectors.append(template)
        report.append((person, len(embeddings), len(images), skipped))

    if not names:
        sys.exit("error: no usable templates built. Check that the photos show "
                 "one clear, reasonably large face each.")

    np.savez(args.out,
             names=np.array(names),
             vectors=np.array(vectors, dtype=np.float32))

    print(f"\nEnrolled {len(names)} of {len(people)} people → {args.out}\n")
    for person, used, total, skipped in report:
        flag = "  " if used >= 2 else ("!!" if used == 0 else " ~")
        print(f"{flag} {person:<28} {used}/{total} photos used")
        for fname, why in skipped:
            print(f"       skipped {fname}: {why}")

    weak = [p for p, used, _, _ in report if 0 < used < 2]
    if weak:
        print(f"\n~ Built from a single photo, so less reliable: {', '.join(weak)}")
        print("  Add 2-3 more photos in different lighting before trusting these.")

    failed = [p for p, used, _, _ in report if used == 0]
    if failed:
        print(f"\n!! No template built for: {', '.join(failed)}")
        print("  These people will come back as 'unknown' in every clip.")


if __name__ == "__main__":
    main()
