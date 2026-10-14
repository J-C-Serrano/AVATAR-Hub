"""Compare voices: base vs fine-tuned (LoRA) Chatterbox multilingual, with webcam vs clean reference.
Per condition and sentence: best-of-N takes (same QC as production: Whisper WER + stray sound), then report
mean WER, stray seconds and speaker similarity (VoiceEncoder cosine vs held-out real clips).
usage: python ft_eval.py --lora /out/ft/<run>/lora_best --clean_ref /v/dataset/wavs/<clip>.wav --out /out/ft/eval_<name> [--takes 2]"""
import argparse, json, os, re, sys
import numpy as np, soundfile as sf, torch, librosa
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
from transformers import pipeline
from peft import PeftModel
sys.path.insert(0, "/s")
ap = argparse.ArgumentParser()
ap.add_argument("--lora"); ap.add_argument("--clean_ref"); ap.add_argument("--webcam_ref", default="/in/ref_vid_A.wav")
ap.add_argument("--out"); ap.add_argument("--takes", type=int, default=2); ap.add_argument("--split", default="")
A = ap.parse_args(); os.makedirs(A.out, exist_ok=True)
EN = ["Hello, I am Hulio Serrano.", "Today I want to talk about servitization.",
      "Manufacturing companies no longer win only by selling machines.",
      "They win by selling outcomes, like uptime, performance, and reliable service over many years.",
      "This changes how we organise, how we price, and how we build trust with customers.",
      "In this short video, my digital avatar is presenting the idea, using my own voice and my own face, with my consent."]
FI = ["Tänään puhumme palveluistamisesta ja siitä, miksi se muuttaa teollisuutta."]
tts = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", device="cuda", torch_dtype=torch.float16)
norm = lambda s: re.sub(r"[^a-zäöå ]", "", s.lower().replace("hulio", "julio").replace("giulio", "julio")).split()
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
# reference embedding: held-out real clips of Julio (never trained on)
val = json.load(open(A.split))["val"] if A.split else []
real = [librosa.load(f"/v/dataset/wavs/{n}.wav", sr=16000)[0] for n in val if "finnish" not in n]
real_emb = torch.from_numpy(tts.ve.embeds_from_wavs(real, sample_rate=16000)).mean(0)
cos = lambda e: float(torch.nn.functional.cosine_similarity(torch.from_numpy(e).float(), real_emb.float(), dim=0))

# snapshot pristine base weights BEFORE loading the adapter (merge_and_unload modifies modules in place)
base_state = {k: v.detach().clone() for k, v in tts.t3.tfmr.state_dict().items()}
lora_state = None
if A.lora:
    merged = PeftModel.from_pretrained(tts.t3.tfmr, A.lora).merge_and_unload()
    tts.t3.tfmr = merged
    lora_state = {k: v.detach().clone() for k, v in merged.state_dict().items()}
    diff = sum(float((lora_state[k].float() - base_state[k].float()).abs().sum()) for k in base_state if k in lora_state)
    print(f"LoRA merged: total |delta| = {diff:.1f} over {len(lora_state)} tensors", flush=True)
    assert diff > 0, "adapter had no effect"
conds = {"1_base_webcamref": (None, A.webcam_ref), "2_base_cleanref": (None, A.clean_ref), "3_finetuned_cleanref": ("lora", A.clean_ref)}
report = {}
for cname, (which, ref) in conds.items():
    if A.lora: tts.t3.tfmr.load_state_dict(lora_state if which == "lora" else base_state)
    parts, rows = [], []
    for lang, sents in (("en", EN), ("fi", FI)):
        for si, s in enumerate(sents):
            best = None
            for k in range(A.takes):
                torch.manual_seed(1000 * si + k + (500 if lang == "fi" else 0))
                w = tts.generate(s, language_id=lang, audio_prompt_path=ref, exaggeration=0.5, cfg_weight=0.0, temperature=0.8).squeeze().cpu().numpy()
                w16 = librosa.resample(w, orig_sr=tts.sr, target_sr=16000)
                r = asr(w16, return_timestamps="word", generate_kwargs={"language": lang, "task": "transcribe"})
                e = wer(s, r["text"]); st = stray(w16, r["chunks"]); sim = cos(tts.ve.embeds_from_wavs([w16], sample_rate=16000)[0])
                sc = 3 * e + 2 * st - sim
                if best is None or sc < best[0]: best = (sc, w, dict(lang=lang, wer=round(e, 3), stray=round(st, 2), sim=round(sim, 3), text=r["text"].strip()))
            parts += [best[1], np.zeros(int(0.3 * tts.sr), dtype=np.float32)]; rows.append(best[2])
            print(cname, lang, si, best[2], flush=True)
    sf.write(f"{A.out}/{cname}.wav", np.concatenate(parts), tts.sr)
    en = [r for r in rows if r["lang"] == "en"]
    report[cname] = {"wer_en": round(float(np.mean([r["wer"] for r in en])), 3), "stray_s": round(float(sum(r["stray"] for r in rows)), 2),
                     "similarity": round(float(np.mean([r["sim"] for r in rows])), 3), "fi_text": rows[-1]["text"], "rows": rows}
json.dump(report, open(f"{A.out}/report.json", "w"), indent=1, ensure_ascii=False)
for k, v in report.items(): print("SUMMARY", k, {x: v[x] for x in ("wer_en", "stray_s", "similarity")}, "| fi:", v["fi_text"][:70])
print("EVAL_DONE")
