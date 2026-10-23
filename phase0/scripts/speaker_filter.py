"""Keep only the main speaker's clips in a dataset (e.g. a Zoom recording with Q&A).
usage (in avatar-hub-app:p0): python speaker_filter.py <dataset dir> <out dataset dir> [--thr 0.75]
VoiceEncoder embedding per clip -> iterated centroid of the dominant speaker -> clips with cosine >= thr are kept."""
import argparse, json, os, shutil, sys
sys.path.insert(0, "/hub/app")
import numpy as np, torch, librosa
from engine import Engine
ap = argparse.ArgumentParser(); ap.add_argument("ds"); ap.add_argument("out"); ap.add_argument("--thr", type=float, default=0.75)
a = ap.parse_args()
clips = json.load(open(os.path.join(a.ds, "clips.json")))
eng = Engine(with_asr=False)
wavs = [librosa.load(os.path.join(a.ds, "wavs", c["clip"] + ".wav"), sr=16000)[0] for c in clips]
E = torch.from_numpy(eng.tts.ve.embeds_from_wavs(wavs, sample_rate=16000)); E = torch.nn.functional.normalize(E, dim=1)
keep = torch.ones(len(clips), dtype=torch.bool)
for _ in range(5):  # centroid of the dominant speaker, re-estimated without outliers
    cen = torch.nn.functional.normalize(E[keep].mean(0, keepdim=True), dim=1)
    sim = (E @ cen.T).squeeze(1); keep = sim >= np.percentile(sim.numpy(), 20)
sim = sim.numpy(); keep = sim >= a.thr
print("similarity percentiles 1/5/10/25/50:", np.round(np.percentile(sim, [1, 5, 10, 25, 50]), 3))
for i in np.argsort(sim)[:25]: print(f"{sim[i]:.3f} {clips[i]['clip']} {clips[i]['dur']:.1f}s {clips[i]['text'][:90]}")
os.makedirs(os.path.join(a.out, "wavs"), exist_ok=True)
kept = [c for c, k in zip(clips, keep) if k]
for c in kept: shutil.copy(os.path.join(a.ds, "wavs", c["clip"] + ".wav"), os.path.join(a.out, "wavs"))
json.dump(kept, open(os.path.join(a.out, "clips.json"), "w"), indent=0, ensure_ascii=False)
names = {c["clip"] for c in kept}
rows = [l for l in open(os.path.join(a.ds, "metadata.csv")).read().strip().split("\n") if l.split("|")[0] in names]
open(os.path.join(a.out, "metadata.csv"), "w").write("\n".join(rows) + "\n")
json.dump({c["clip"]: float(s) for c, s in zip(clips, sim)}, open(os.path.join(a.out, "speaker_sim.json"), "w"), indent=0)
print(f"kept {len(kept)}/{len(clips)} clips, {sum(c['dur'] for c in kept) / 60:.1f} min")
