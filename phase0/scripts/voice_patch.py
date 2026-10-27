"""Replace single sentences of a say_clean.py voice-over with a better take (made with say_clean.py --text).
usage: python3 voice_patch.py <voice dir> <slide>:<row>=<take.wav>[:<take.json>] ...
The take is level-matched to the sentence it replaces; later sentence times of the slide shift by the length
difference. Originals are kept as slide_NN.orig.{wav,json} (first patch only)."""
import json, os, shutil, sys
import numpy as np, soundfile as sf

vd = sys.argv[1]
for spec in sys.argv[2:]:
    key, take = spec.split("=", 1); sl, row = map(int, key.split(":"))
    base = os.path.join(vd, f"slide_{sl:02d}")
    for ext in ("wav", "json"):
        if not os.path.exists(f"{base}.orig.{ext}"): shutil.copy(f"{base}.{ext}", f"{base}.orig.{ext}")
    w, sr = sf.read(base + ".wav", dtype="float32"); j = json.load(open(base + ".json"))
    n, nsr = sf.read(take.split(":")[0], dtype="float32"); assert nsr == sr
    r = j["sentences"][row]; a, b = int(round(r["t0"] * sr)), int(round(r["t1"] * sr))
    rms = lambda x: float(np.sqrt(np.mean(x ** 2)) + 1e-9)
    n = n * (rms(w[a:b]) / rms(n)); n = np.clip(n, -0.99, 0.99)
    w = np.concatenate([w[:a], n, w[b:]]); d = (len(n) - (b - a)) / sr
    info = json.load(open(take.split(":")[1]))[0] if ":" in take else {}
    r.update({k: v for k, v in info.items() if k not in ("t0", "t1", "para", "cue")}); r["t1"] = round(r["t0"] + len(n) / sr, 3)
    for q in j["sentences"][row + 1:]: q["t0"] = round(q["t0"] + d, 3); q["t1"] = round(q["t1"] + d, 3)
    j["dur"] = round(len(w) / sr, 3); sf.write(base + ".wav", w, sr); json.dump(j, open(base + ".json", "w"), indent=1, ensure_ascii=False)
    print(f"slide {sl} row {row}: {d:+.2f} s, now {j['dur']:.2f} s")
