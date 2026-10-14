"""Build a fine-tuning dataset from long recordings: Whisper (verbatim, word timestamps) -> clips of 3-10 s cut at
word/pause boundaries -> 24 kHz mono WAVs + LJSpeech metadata.csv (filename|text|text) + stats.
usage: prep_voice_dataset.py <in_dir with audio files> <out_dir> [--lang_map "f finnish=fi"]
Language is English unless the filename matches a key of the lang map (substring, case-insensitive)."""
import sys, os, re, json, glob, numpy as np, soundfile as sf, librosa, torch
from transformers import pipeline

IN, OUT = sys.argv[1], sys.argv[2]
LANG = {"finnish": "fi", "swedish": "sv", "suomi": "fi", "svenska": "sv"}
os.makedirs(f"{OUT}/wavs", exist_ok=True)
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", device="cuda", torch_dtype=torch.float16)
MIN, MAX, SR = 3.0, 10.0, 24000
rows, stats = [], []
files = sorted(glob.glob(f"{IN}/*"))
for fi, path in enumerate(files):
    base = os.path.splitext(os.path.basename(path))[0]
    lang = next((v for k, v in LANG.items() if k in base.lower()), "en")
    y, _ = librosa.load(path, sr=SR, mono=True)
    # 1) cut at natural pauses (silence > ~0.3 s), then merge/split into 3-10 s clips
    iv = librosa.effects.split(y, top_db=38, frame_length=1024, hop_length=256)
    segs = []
    for s0, e0 in iv:
        s0, e0 = s0 / SR, e0 / SR
        if segs and s0 - segs[-1][1] < 0.30: segs[-1][1] = e0          # bridge short gaps
        else: segs.append([s0, e0])
    clips, cur = [], None
    for s0, e0 in segs:
        if cur is None: cur = [s0, e0]; continue
        if (e0 - cur[0]) <= MAX and (cur[1] - cur[0]) < MIN: cur[1] = e0   # too short: merge with next
        else: clips.append(cur); cur = [s0, e0]
    if cur: clips.append(cur)
    out = []
    for s0, e0 in clips:                                                  # split over-long clips evenly
        n = int(np.ceil((e0 - s0) / MAX)); step = (e0 - s0) / n
        out += [[s0 + k * step, s0 + (k + 1) * step] for k in range(n)]
    clips = [c for c in out if c[1] - c[0] >= 1.5]
    # 2) transcribe clips in GPU batches (verbatim: keep fillers)
    auds = [librosa.resample(y[int(max(0, a - 0.12) * SR):int(min(len(y) / SR, b + 0.18) * SR)], orig_sr=SR, target_sr=16000) for a, b in clips]
    res = asr(auds, batch_size=16, generate_kwargs={"language": lang, "task": "transcribe"})
    tr = []
    for ci, ((a, b), r) in enumerate(zip(clips, res)):
        a, b = max(0, a - 0.12), min(len(y) / SR, b + 0.18)
        text = re.sub(r"\s+", " ", r["text"]).strip()
        if not text or len(text) < 3: continue
        name = f"{re.sub(r'[^a-z0-9]+', '_', base.lower())}_{ci:03d}"
        seg = y[int(a * SR):int(b * SR)]
        seg = seg / (np.abs(seg).max() + 1e-9) * 0.89 if np.abs(seg).max() > 0.95 else seg
        sf.write(f"{OUT}/wavs/{name}.wav", seg, SR)
        rows.append(f"{name}|{text}|{text}"); stats.append({"clip": name, "lang": lang, "dur": round(b - a, 2), "text": text})
        tr.append({"clip": name, "start": round(a, 2), "end": round(b, 2), "text": text})
    json.dump({"lang": lang, "clips": tr}, open(f"{OUT}/{base}.transcript.json", "w"), ensure_ascii=False, indent=0)
    print(f"{fi + 1}/{len(files)} [ {base}: lang={lang} {len(y) / SR:.0f}s -> {len(clips)} clips", flush=True)
open(f"{OUT}/metadata.csv", "w").write("\n".join(rows) + "\n")
json.dump(stats, open(f"{OUT}/clips.json", "w"), ensure_ascii=False, indent=0)
d = np.array([s["dur"] for s in stats])
print(f"DONE clips={len(d)} total={d.sum() / 60:.1f} min mean={d.mean():.1f}s min={d.min():.1f}s max={d.max():.1f}s "
      f"en={sum(s['lang'] == 'en' for s in stats)} fi={sum(s['lang'] == 'fi' for s in stats)}")
