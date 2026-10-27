"""Whole-lecture filler/stutter scan: overlapping 12 s windows every 6 s (Whisper with a disfluent prompt), then each
hit re-checked in three windows around it; a spot counts when at least 2 of the 3 hear it.
usage (in avatar-hub-app:p0): python disfl_full.py <lecture.mp4|wav>"""
import subprocess, sys
import numpy as np, librosa
import disfl_scan as D
f = sys.argv[1]
w = librosa.load(f, sr=16000)[0] if f.endswith(".wav") else np.frombuffer(subprocess.run(
    ["ffmpeg", "-v", "error", "-i", f, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True, check=True).stdout, np.float32)
hits = []
for s in np.arange(0, len(w) / 16000, 6.0):
    text, fill, reps, words = D.scan(w[int(s * 16000):int((s + 12) * 16000)])
    for x, t0 in fill: hits.append((s + t0, f"'{x}'"))
    for x, i in reps:
        ts = [t for wd, t, _ in words if wd and not D.FILL.match(wd)]
        hits.append((s + (ts[i] if i < len(ts) else 0), f"'{x} {x}'"))
spots = []
for t, what in sorted(hits):
    if spots and t - spots[-1][0] < 3: continue
    votes, texts = 0, []
    for lo, hi in ((4, 5), (8, 3), (2, 8)):
        text, fill, reps, _ = D.scan(w[int(max(0, t - lo) * 16000):int((t + hi) * 16000)])
        votes += bool(fill or reps); texts.append(text)
    spots.append((t, what, votes))
    if votes >= 2: print(f"SPOT {int(t // 60)}:{t % 60:04.1f} {what} heard {votes}/3 | {texts[0][:200]}", flush=True)
print(f"SCANNED {len(w) / 16000:.0f}s hits {len(hits)} confirmed {sum(v >= 2 for _, _, v in spots)}")
