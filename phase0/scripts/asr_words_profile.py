"""Profile one Whisper word-timestamp call (the say_clean.py QC pass) to find its hotspot.
usage (in avatar-hub-app:p0): python asr_words_profile.py <wav>"""
import cProfile, pstats, sys, time, io
import torch, librosa
from transformers import pipeline
w = librosa.load(sys.argv[1], sr=16000)[0][:16000 * 8]
for impl in ("eager", "sdpa"):
    asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", device="cuda", dtype=torch.float16, model_kwargs={"attn_implementation": impl})
    asr(w, return_timestamps="word", generate_kwargs={"language": "en", "task": "transcribe"})      # warm-up
    torch.cuda.synchronize(); t = time.time(); asr(w, generate_kwargs={"language": "en", "task": "transcribe"}); torch.cuda.synchronize()
    print(f"PROF {impl}: plain transcription {time.time() - t:.2f}s", flush=True)
    pr = cProfile.Profile(); t = time.time(); pr.enable()
    r = asr(w, return_timestamps="word", generate_kwargs={"language": "en", "task": "transcribe"}); torch.cuda.synchronize()
    pr.disable(); print(f"PROF {impl}: word timestamps {time.time() - t:.2f}s, {len(r['chunks'])} words", flush=True)
    s = io.StringIO(); pstats.Stats(pr, stream=s).sort_stats("tottime").print_stats(12)
    print("\n".join("PROF   " + l for l in s.getvalue().splitlines() if l.strip())[:4000], flush=True)
    del asr; torch.cuda.empty_cache()
