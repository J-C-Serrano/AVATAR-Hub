"""Synthesize text with the fine-tuned voice (LoRA merged) + clean reference, best-of-N takes per sentence with QC.
usage: python say.py --text "..." --out /out/name.wav [--lora /out/ft/r8_lr1e4/lora_best] [--ref /v/dataset/wavs/section_c_044.wav]
       [--lang en] [--takes 3] [--pause 0.35]"""
import argparse, re, numpy as np, soundfile as sf, torch, librosa
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
from transformers import pipeline
from peft import PeftModel
ap = argparse.ArgumentParser()
ap.add_argument("--text"); ap.add_argument("--out"); ap.add_argument("--lang", default="en")
ap.add_argument("--lora", default="/ft/r8_lr1e4/lora_best"); ap.add_argument("--ref", default="/v/dataset/wavs/section_c_044.wav")
ap.add_argument("--takes", type=int, default=3); ap.add_argument("--pause", type=float, default=0.35)
A = ap.parse_args()
tts = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
if A.lora: tts.t3.tfmr = PeftModel.from_pretrained(tts.t3.tfmr, A.lora).merge_and_unload()
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", device="cuda", torch_dtype=torch.float16)
tts.prepare_conditionals(A.ref, exaggeration=0.5)
norm = lambda s: re.sub(r"[^a-zäöå0-9 ]", "", re.sub(r"\bay eye\b|\ba\.i\.", "ai", s.lower())).split()   # "ay eye" = spelling that makes the voice say A-I
def wer(r, h):
    r, h = norm(r), norm(h); d = np.arange(len(h) + 1)
    for i in range(1, len(r) + 1):
        prev, d[0] = d.copy(), i
        for j in range(1, len(h) + 1): d[j] = min(prev[j] + 1, d[j - 1] + 1, prev[j - 1] + (r[i - 1] != h[j - 1]))
    return d[len(h)] / max(len(r), 1)
def stray(w16, chunks):
    rms = librosa.feature.rms(y=w16, frame_length=640, hop_length=320)[0]; ref = np.percentile(rms, 95) + 1e-9
    t = np.arange(len(rms)) * 0.02; inw = (t < 0.12) | (t > t[-1] - 0.12)
    for c in chunks:
        a, b = c["timestamp"]; inw |= (t >= (a or 0) - 0.05) & (t <= (b or t[-1]) + 0.05)
    return float(((rms > 0.15 * ref) & ~inw).sum() * 0.02)
sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", A.text.strip()) if s.strip()]
parts = []
for si, s in enumerate(sents):
    best = None
    for k in range(A.takes):
        torch.manual_seed(7000 + 10 * si + k)
        w = tts.generate(s, language_id=A.lang, exaggeration=0.5, cfg_weight=0.0, temperature=0.8).squeeze().cpu().numpy()
        w16 = librosa.resample(w, orig_sr=tts.sr, target_sr=16000)
        r = asr(w16, return_timestamps=True, generate_kwargs={"language": A.lang, "task": "transcribe"})
        sc = 3 * wer(s, r["text"]) + 2 * stray(w16, r["chunks"])
        if best is None or sc < best[0]: best = (sc, w, r["text"].strip())
        if sc == 0: break
    print(f"{si + 1}/{len(sents)} [ score={best[0]:.2f} heard: {best[2]}", flush=True)
    parts += [best[1], np.zeros(int(A.pause * tts.sr), dtype=np.float32)]
a = np.concatenate(parts); a = a / (np.abs(a).max() + 1e-9) * 0.89
sf.write(A.out, a, tts.sr); print(f"WROTE {A.out} {len(a) / tts.sr:.1f}s")
