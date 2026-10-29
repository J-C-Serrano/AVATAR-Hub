"""Where the time of one say_clean.py take goes (token generation, waveform, the two Whisper passes).
usage (in avatar-hub-app:p0): python take_profile.py <voice_id> [takes per sentence]"""
import json, os, sys, time
sys.path.insert(0, "/hub/app")
import numpy as np, torch, librosa
from engine import Engine
from transformers import pipeline
vid = sys.argv[1]; K = int(sys.argv[2]) if len(sys.argv) > 2 else 2
V = f"/hub/data/voices/{vid}"; s = json.load(open(f"{V}/profile.json"))["settings"]
eng = Engine(with_asr=False); eng.use(os.path.join(V, s["lora"]), s["lora_scale"]); eng.set_ref(os.path.join(V, s["ref"]), 0.35)
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", device="cuda", dtype=torch.float16, model_kwargs={"attn_implementation": "eager"})
PIDS = asr.tokenizer.get_prompt_ids("Umm, so, uh, I mean, hmm, eh, like, you know, ah, the the, erm, okay.", return_tensors="pt").to("cuda")
tts = eng.tts; T = {"t3": 0.0, "s3gen": 0.0, "asr_words": 0.0, "asr_disfl": 0.0}; n = 0; audio = 0.0
orig_t3, orig_s3 = tts.t3.inference, tts.s3gen.inference
def timed(f, key):
    def g(*a, **k):
        torch.cuda.synchronize(); t = time.time(); r = f(*a, **k); torch.cuda.synchronize(); T[key] += time.time() - t; return r
    return g
tts.t3.inference = timed(orig_t3, "t3"); tts.s3gen.inference = timed(orig_s3, "s3gen")
for text in ["And this is important.",
             "So what is the corollary of what I am saying? It is highly probable that one company will have multiple business models.",
             "After the first book was published, the authors realized that matching customers with offers was a bottleneck for many users."]:
    for k in range(K):
        torch.manual_seed(k); eng._clear_hooks()
        w = tts.generate(text, language_id="en", exaggeration=0.35, cfg_weight=s["cfg_weight"], temperature=0.6).squeeze().cpu().numpy()
        w16 = librosa.resample(w, orig_sr=eng.sr, target_sr=16000); audio += len(w16) / 16000; n += 1
        torch.cuda.synchronize(); t = time.time(); asr(w16, return_timestamps="word", generate_kwargs={"language": "en", "task": "transcribe"}); torch.cuda.synchronize(); T["asr_words"] += time.time() - t
        t = time.time(); asr(w16, generate_kwargs={"language": "en", "task": "transcribe", "prompt_ids": PIDS}); torch.cuda.synchronize(); T["asr_disfl"] += time.time() - t
tot = sum(T.values())
print(f"PROFILE {n} takes, {audio:.1f} s audio; per take: " + ", ".join(f"{k} {v / n:.1f}s ({100 * v / tot:.0f}%)" for k, v in T.items()) + f"; total {tot / n:.1f}s; t3 dtype {next(tts.t3.parameters()).dtype}")
