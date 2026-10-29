"""Transcript per slide segment (each slide's stretch of the recording transcribed on its own, so long-file timestamp
drift cannot move words to the wrong slide). Output format of asr_long_words.py (absolute times, words spread
over Whisper segments).  usage (in avatar-hub-app:p0): python asr_slides.py <in.wav 16k> <segments.json> <out.json>"""
import json, sys, torch, librosa
from transformers import pipeline
import whisper_fast; whisper_fast.install()   # lossless: no per-tensor GPU syncs in word timestamps (whisper_fast.py)
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", device="cuda", dtype=torch.float16)
w, _ = librosa.load(sys.argv[1], sr=16000); segs = json.load(open(sys.argv[2])); words = []
for s in segs:
    a = w[int(s["t0"] * 16000):int(s["t1"] * 16000)]
    if len(a) < 16000: continue
    r = asr(a, return_timestamps=True, chunk_length_s=30, batch_size=8, generate_kwargs={"language": "en", "task": "transcribe"})
    for c in r["chunks"]:
        t0, t1 = c["timestamp"]; t1 = t1 if t1 is not None else len(a) / 16000
        ws = c["text"].split(); n = sum(len(x) + 1 for x in ws) or 1; acc = 0
        for x in ws:
            b = t0 + (t1 - t0) * acc / n; acc += len(x) + 1
            words.append({"w": x, "t0": round(s["t0"] + min(b, len(a) / 16000 - 0.05), 2), "t1": round(s["t0"] + min(t0 + (t1 - t0) * acc / n, len(a) / 16000), 2)})
json.dump(words, open(sys.argv[3], "w"), indent=0); print("DONE", len(words), "words")
