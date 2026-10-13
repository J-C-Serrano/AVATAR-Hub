import sys, torch, librosa
from transformers import pipeline
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", device="cuda", torch_dtype=torch.float16)
a, sr = librosa.load(sys.argv[1], sr=16000)
r = asr(a, return_timestamps=True, generate_kwargs={"task": "transcribe"})
print("TEXT:", r["text"].strip())
for c in r["chunks"]: print("  %5.1f-%5.1f %s" % (c["timestamp"][0], c["timestamp"][1] or 0, c["text"].strip()))
