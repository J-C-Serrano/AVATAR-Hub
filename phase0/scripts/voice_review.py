"""List the sentences of a say_clean.py voice dir that need a listen or a re-voice (CPU only, reads the slide JSONs).
usage: python3 voice_review.py <voice dir> [--score 0.9]
Flags: best take still above --score (stretched word, gap, stray sound), any filler/repeat left, or the words heard
differ from the script (WER > 0; often a name Whisper spells differently, so check before re-voicing).
Output: one line per suspect, `slide:row score reason | script | heard` (row = index for voice_patch.py)."""
import argparse, glob, json, os, re
ap = argparse.ArgumentParser(); ap.add_argument("vd"); ap.add_argument("--score", type=float, default=0.9); a = ap.parse_args()
n = tot = 0
for f in sorted(glob.glob(os.path.join(a.vd, "slide_??.json"))):
    j = json.load(open(f))
    for i, r in enumerate(j.get("sentences", [])):
        tot += 1; w = r.get("worst", "")
        why = [x for x, c in [("filler", bool(re.match(r"\d+ filler", w))), ("repeat", bool(re.match(r"\d+ repeat", w))), (f"score {r['score']:.2f} ({w})", r["score"] > a.score),
                              (f"wer {r.get('wer', 0):.2f}", r.get("wer", 0) > 0)] if c]
        if why:
            n += 1; print(f"{int(os.path.basename(f)[6:8])}:{i} {r['score']:.2f} {'; '.join(why)} | {r['text']} | {r.get('heard', '')}")
print(f"# {n} of {tot} sentences flagged in {a.vd}")
