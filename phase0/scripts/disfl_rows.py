"""Per-sentence filler/stutter check of a say_clean.py voice dir: each sentence is scanned alone, with 0.4 s of silence
around it, and together with its neighbours; a sentence is listed when two or more of the three hear the same problem.
usage (in avatar-hub-app:p0): python disfl_rows.py <voice dir> [slides]"""
import glob, json, os, sys
import numpy as np, librosa
import disfl_scan as D
vd = sys.argv[1]; want = {int(x) for x in sys.argv[2].split(",")} if len(sys.argv) > 2 else None
for f in sorted(glob.glob(os.path.join(vd, "slide_??.json"))):
    j = json.load(open(f)); n = j["slide"]
    if want and n not in want or not j["sentences"]: continue
    w = librosa.load(f[:-5] + ".wav", sr=16000)[0]; S = j["sentences"]; z = np.zeros(6400, np.float32)
    for i, r in enumerate(S):
        a, b = int(r["t0"] * 16000), int(r["t1"] * 16000)
        pa = int(S[i - 1]["t0"] * 16000) if i else a; nb = int(S[i + 1]["t1"] * 16000) if i + 1 < len(S) else b
        res = []
        for seg in (w[a:b], np.concatenate([z, w[a:b], z]), w[pa:nb]):
            text, fill, reps, _ = D.scan(seg); res.append((bool(fill or reps), text, fill, reps))
        if sum(x for x, *_ in res) >= 2:
            k = next(x for x in res if x[0])
            print(f"ROW {n}:{i} votes {sum(x for x, *_ in res)}/3 fill={[x for x, _ in k[2]]} reps={[x for x, _ in k[3]]} | {k[1][:220]}", flush=True)
print("ROWS_DONE")
