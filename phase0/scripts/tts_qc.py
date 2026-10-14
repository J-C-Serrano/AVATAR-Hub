"""Sentence-level TTS with automatic QC (best-of-N takes).
For each variant (language mode x reference) and sentence: generate N seeds, score each take with Whisper
(word error vs. the sentence) + stray non-speech sounds outside words + duration sanity; keep the best take.
usage: python tts_qc.py <out_prefix> [n_takes]
Writes /out/<prefix>_<variant>.wav and /out/<prefix>_report.json."""
import sys, json, re, time, numpy as np, soundfile as sf, torch, librosa
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
from transformers import pipeline

PREFIX = sys.argv[1]; NT = int(sys.argv[2]) if len(sys.argv) > 2 else 3
SENTS = ["Hello, I am {NAME} Serrano.", "Today I want to talk about servitization.",
         "Manufacturing companies no longer win only by selling machines.",
         "They win by selling outcomes, like uptime, performance, and reliable service over many years.",
         "This changes how we organise, how we price, and how we build trust with customers.",
         "In this short video, my digital avatar is presenting the idea, using my own voice and my own face, with my consent."]
REFS = {"A": "/in/ref_vid_A.wav", "B": "/in/ref_vid_B.wav"}
VARIANTS = {  # name: (language_id, ref, spelling of the name, exaggeration, cfg_weight)
    "en_A": ("en", "A", "Hulio", 0.5, 0.0),
    "es_A": ("es", "A", "Julio", 0.5, 0.0),
    "es_B": ("es", "B", "Julio", 0.5, 0.0),
    "es_A_cfg3": ("es", "A", "Julio", 0.5, 0.3),
}
m = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", device="cuda", torch_dtype=torch.float16)
norm = lambda s: re.sub(r"[^a-z ]", "", s.lower().replace("-", " ")).split()

def wer(ref, hyp):
    r, h = norm(ref), norm(hyp); d = np.arange(len(h) + 1)
    for i in range(1, len(r) + 1):
        prev, d[0] = d.copy(), i
        for j in range(1, len(h) + 1): d[j] = min(prev[j] + 1, d[j - 1] + 1, prev[j - 1] + (r[i - 1] != h[j - 1]))
    return d[len(h)] / max(len(r), 1)

def stray(wav, sr, chunks):  # energy outside recognised words (excluding 0.12 s edges): stray sounds / glitches
    y = librosa.resample(wav, orig_sr=sr, target_sr=16000); hop = 320
    rms = librosa.feature.rms(y=y, frame_length=640, hop_length=hop)[0]; ref = np.percentile(rms, 95) + 1e-9
    t = np.arange(len(rms)) * hop / 16000; inw = (t < 0.12) | (t > t[-1] - 0.12)
    for c in chunks:
        a, b = c["timestamp"]; inw |= (t >= (a or 0) - 0.05) & (t <= (b or t[-1]) + 0.05)
    return float(((rms > 0.15 * ref) & ~inw).sum() * hop / 16000)   # seconds of stray sound

report = {}
for vn, (lang, ref, name, ex, cfg) in VARIANTS.items():
    parts, rep = [], []
    for si, s in enumerate(SENTS):
        text = s.replace("{NAME}", name); target = s.replace("{NAME}", "Julio")
        best = None
        for k in range(NT):
            torch.manual_seed(100 * si + k)
            w = m.generate(text, language_id=lang, audio_prompt_path=REFS[ref], exaggeration=ex, cfg_weight=cfg, temperature=0.8)
            w = w.squeeze().cpu().numpy()
            r = asr(librosa.resample(w, orig_sr=m.sr, target_sr=16000), return_timestamps="word", generate_kwargs={"language": "en", "task": "transcribe"})
            e = wer(target.replace("Julio", "julio"), r["text"].replace("Giulio", "giulio").replace("Hulio", "julio"))
            st = stray(w, m.sr, r["chunks"]); dur = len(w) / m.sr; cps = len(text) / dur
            score = e * 3 + st * 2 + (0.5 if not 9 <= cps <= 20 else 0)
            name_ok = "julio" in r["text"].lower() or "hulio" in r["text"].lower()
            cand = dict(seed=100 * si + k, wer=round(float(e), 3), stray_s=round(st, 2), dur=round(dur, 2), cps=round(cps, 1), score=round(float(score), 3), text=r["text"].strip(), name_ok=name_ok)
            if si == 0 and not name_ok: cand["score"] += 1.0
            if best is None or cand["score"] < best[0]["score"]: best = (cand, w)
        parts += [best[1], np.zeros(int(0.3 * m.sr), dtype=np.float32)]; rep.append(best[0])
        print(vn, si, best[0], flush=True)
    a = np.concatenate(parts); sf.write(f"/out/{PREFIX}_{vn}.wav", a, m.sr)
    report[vn] = rep
json.dump(report, open(f"/out/{PREFIX}_report.json", "w"), indent=1)
print("DONE")
