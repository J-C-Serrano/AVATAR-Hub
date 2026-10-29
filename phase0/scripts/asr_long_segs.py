"""Fast long-recording transcript: Whisper turbo segment timestamps (no word DTW, ~5x faster), words given times
spread over their segment by character count. Same output format as asr_long_words.py (good enough for slide
splits and cue placement, not for word-level QC).
usage (in avatar-hub-app:p0): python asr_long_segs.py <in.wav 16k> <out.json>"""
import json, sys, torch, librosa
from transformers import pipeline
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", device="cuda", dtype=torch.float16)
w, _ = librosa.load(sys.argv[1], sr=16000)
r = asr(w, return_timestamps=True, chunk_length_s=30, batch_size=8, generate_kwargs={"language": "en", "task": "transcribe"})
words = []
for c in r["chunks"]:
    t0, t1 = c["timestamp"]; t1 = t1 if t1 is not None else t0 + 2.0
    ws = c["text"].split(); n = sum(len(x) + 1 for x in ws) or 1; acc = 0
    for x in ws:
        a = t0 + (t1 - t0) * acc / n; acc += len(x) + 1
        words.append({"w": x, "t0": round(a, 2), "t1": round(t0 + (t1 - t0) * acc / n, 2)})
json.dump(words, open(sys.argv[2], "w"), indent=0); print("DONE", len(words), "words")
