"""Word-level timestamps with Whisper: asr_words.py in.wav out.json"""
import sys, json, torch, librosa
from transformers import pipeline
import whisper_fast; whisper_fast.install()   # lossless: no per-tensor GPU syncs in word timestamps (whisper_fast.py)
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", device="cuda", torch_dtype=torch.float16)
a, sr = librosa.load(sys.argv[1], sr=16000)
r = asr(a, return_timestamps="word", generate_kwargs={"task": "transcribe"})
words = [{"w": c["text"].strip(), "t0": c["timestamp"][0], "t1": c["timestamp"][1]} for c in r["chunks"]]
json.dump(words, open(sys.argv[2], "w"), indent=0); print(len(words), "words;", " ".join(w["w"] for w in words))
