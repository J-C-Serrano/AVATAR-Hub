"""Speech for avatar videos with a stricter, word-level QC (no stretched words, no mid-sentence pauses).
usage (in avatar-hub-app:p0): python say_clean.py <voice_id> "<text>" <out.wav> [--takes 12] [--temp 0.6] [--exag 0.35]
Per sentence: render up to N takes, score each by Whisper word timestamps:
  3*WER + 2*stray sound + 2*fillers (uh, um...) + stretch (time a word lasts beyond ~0.075 s/letter + 0.15 s) + gaps > 0.25 s between words.
Keeps the best take; prints a report per sentence."""
import argparse, json, os, re, sys
sys.path.insert(0, "/hub/app")
import numpy as np, torch, librosa, soundfile as sf
from engine import Engine

ap = argparse.ArgumentParser()
ap.add_argument("vid"); ap.add_argument("text"); ap.add_argument("out")
ap.add_argument("--takes", type=int, default=12); ap.add_argument("--temp", type=float, default=0.6)
ap.add_argument("--exag", type=float, default=0.35); ap.add_argument("--lang", default="en")
a = ap.parse_args()
V = f"/hub/data/voices/{a.vid}"; s = json.load(open(f"{V}/profile.json"))["settings"]
eng = Engine(); eng.use(os.path.join(V, s["lora"]), s["lora_scale"]); eng.set_ref(os.path.join(V, s["ref"]), a.exag)


FILLERS = {"uh", "um", "er", "erm", "ah", "eh", "hmm", "mm", "uhm"}


def score(w, text):
    base, heard = eng._qc(w, text, a.lang)
    w16 = librosa.resample(w, orig_sr=eng.sr, target_sr=16000)
    ch = eng.asr(w16, return_timestamps="word", generate_kwargs={"language": a.lang, "task": "transcribe"})["chunks"]
    stretch, gaps, worst = 0.0, 0.0, ""
    for i, c in enumerate(ch):
        t0, t1 = c["timestamp"]; t1 = t1 if t1 is not None else len(w16) / 16000
        n = len(re.sub(r"[^\w]", "", c["text"]))
        ex = max(0.0, (t1 - t0) - (0.075 * n + 0.15))
        if i == len(ch) - 1: ex = max(0.0, ex - 0.25)  # sentence-final words may trail
        if ex > stretch: worst = f"{c['text'].strip()} {t1 - t0:.2f}s"
        stretch = max(stretch, ex)
        if i: gaps += max(0.0, t0 - ch[i - 1]["timestamp"][1] - 0.25)
    fillers = sum(re.sub(r"[^\w]", "", c["text"].lower()) in FILLERS for c in ch)
    if fillers: worst = f"{fillers} filler(s)"
    return base + 3 * stretch + 2 * gaps + 2 * fillers, heard, round(stretch, 2), round(gaps, 2), worst


sents = [x.strip() for x in re.split(r"(?<=[.!?])\s+", a.text.strip()) if x.strip()]
parts, rep = [], []
for si, t in enumerate(sents):
    best = None
    for k in range(a.takes):
        torch.manual_seed(1000 + 101 * si + k); eng._clear_hooks()
        w = eng.tts.generate(t, language_id=a.lang, exaggeration=a.exag, cfg_weight=s["cfg_weight"], temperature=a.temp).squeeze().cpu().numpy()
        sc, heard, st, gp, worst = score(w, t)
        print(f"s{si + 1} take {k + 1}: score {sc:.2f} stretch {st} gaps {gp} worst [{worst}] heard: {heard}", flush=True)
        if best is None or sc < best[0]: best = (sc, w, heard, st, gp)
        if sc < 0.05: break
    parts += [best[1], np.zeros(int(0.32 * eng.sr), dtype=np.float32)]
    rep.append({"sentence": t, "score": round(best[0], 2), "stretch": best[3], "gaps": best[4], "heard": best[2]})
out = np.concatenate(parts); out = out / (np.abs(out).max() + 1e-9) * 0.89
sf.write(a.out, out, eng.sr)
print(json.dumps(rep, indent=1)); print("DUR", round(len(out) / eng.sr, 2))
