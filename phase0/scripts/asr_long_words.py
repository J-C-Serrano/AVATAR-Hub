"""Word timestamps for a long recording (Whisper turbo, eager attention, 30 s chunks).
usage (in avatar-hub-app:p0): python asr_long_words.py <in.wav 16k> <out.json>"""
import json, sys, torch, librosa
from transformers import pipeline
import whisper_fast; whisper_fast.install()   # lossless: no per-tensor GPU syncs in word timestamps (whisper_fast.py)
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", device="cuda", dtype=torch.float16,
               model_kwargs={"attn_implementation": "eager"})
w, _ = librosa.load(sys.argv[1], sr=16000)
r = asr(w, return_timestamps="word", chunk_length_s=30, batch_size=4, generate_kwargs={"language": "en", "task": "transcribe"})
words = [{"w": c["text"].strip(), "t0": c["timestamp"][0], "t1": c["timestamp"][1]} for c in r["chunks"]]
json.dump(words, open(sys.argv[2], "w"), indent=0); print("DONE", len(words), "words")
