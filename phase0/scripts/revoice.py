"""Re-voice chosen sentences of a say_clean.py voice dir and splice them in (one model load for all of them).
usage (in avatar-hub-app:p0): python revoice.py <voice id> <voice dir> <lexicon.json> <slide:row>[=new text] [...] [--cfg 0.2] [--takes 12]
Each row's own text (the piece say_clean voiced), or the new text given after '=' (e.g. a long sentence split in two;
update spoken.txt to match), is generated again with the same strict QC; the new take replaces the
old one via voice_patch.py (level-matched, later times shifted, originals kept as slide_NN.orig.*) when it scores
below 1.0 or below the old take. Rows come from voice_review.py / disfl_rows.py; check the result with disfl_rows.py."""
import argparse, json, os, subprocess, sys
ap = argparse.ArgumentParser(); ap.add_argument("vid"); ap.add_argument("vd"); ap.add_argument("lexicon"); ap.add_argument("rows", nargs="+")
ap.add_argument("--cfg", type=float); ap.add_argument("--takes", type=int, default=12); ap.add_argument("--tag", default="fix")
ap.add_argument("--force", action="store_true", help="patch the best new take even if its score is not lower (the old take has a misheard word the score cannot see)")
a = ap.parse_args()
here = os.path.dirname(os.path.abspath(__file__)); fd = os.path.join(a.vd, a.tag); os.makedirs(fd, exist_ok=True)
rows, texts = [], {}
for spec in a.rows:
    key, _, txt = spec.partition("="); rows.append(tuple(map(int, key.split(":"))))
    if txt: texts[rows[-1]] = txt.strip()
old = {}
with open(os.path.join(fd, "fix.txt"), "w") as f:
    for k, (sl, row) in enumerate(rows, 1):
        r = json.load(open(os.path.join(a.vd, f"slide_{sl:02d}.json")))["sentences"][row]; old[k] = r
        f.write(f"### {k}\n{texts.get((sl, row), r['text'])}\n\n")
cmd = [sys.executable, os.path.join(here, "say_clean.py"), a.vid, "--script", os.path.join(fd, "fix.txt"), "--outdir", fd,
       "--takes", str(a.takes), "--accept", "0.3", "--lexicon", a.lexicon] + (["--cfg", str(a.cfg)] if a.cfg is not None else [])
subprocess.run(cmd, check=True)
specs = []
for k, (sl, row) in enumerate(rows, 1):
    nj = json.load(open(os.path.join(fd, f"slide_{k:02d}.json"))); ss = nj["sentences"]
    new = max(ss, key=lambda x: x["score"]).copy()          # several sentences (new text): the worst one decides
    new.update(text=" ".join(x["text"] for x in ss), heard=" ".join(x["heard"] for x in ss), wer=max(x.get("wer", 0) for x in ss))
    keep = a.force or new["score"] < 1.0 or new["score"] < old[k]["score"]
    print(f"REVOICE {sl}:{row} old {old[k]['score']:.2f} -> new {new['score']:.2f} ({new.get('worst', '')}) {'PATCH' if keep else 'kept old'} | {new['heard']}", flush=True)
    if keep:
        tj = os.path.join(fd, f"take_{sl:02d}_{row:02d}.json"); json.dump([new], open(tj, "w"), indent=1, ensure_ascii=False)
        os.replace(os.path.join(fd, f"slide_{k:02d}.wav"), os.path.join(fd, f"take_{sl:02d}_{row:02d}.wav"))
        specs.append(f"{sl}:{row}={os.path.join(fd, f'take_{sl:02d}_{row:02d}.wav')}:{tj}")
    for ext in ("wav", "json"):   # the per-fix files are inputs only; a later run must not skip them as "done"
        p = os.path.join(fd, f"slide_{k:02d}.{ext}")
        if os.path.exists(p): os.remove(p)
if specs: subprocess.run([sys.executable, os.path.join(here, "voice_patch.py"), a.vd] + specs, check=True)
print(f"REVOICE_DONE {len(specs)} of {len(rows)} patched", flush=True)
