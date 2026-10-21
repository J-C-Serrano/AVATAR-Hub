"""Try spellings of one sentence with the fine-tuned voice: tts_try.py <out dir> <variant> [<variant> ...]
Writes <out>/v<i>_t<k>.wav (3 takes each) and prints what Whisper hears."""
import sys, os, numpy as np, soundfile as sf, torch, librosa
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
from transformers import pipeline
from peft import PeftModel
O, V = sys.argv[1], sys.argv[2:]
tts = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
tts.t3.tfmr = PeftModel.from_pretrained(tts.t3.tfmr, "/ft/r8_lr1e4/lora_best").merge_and_unload()
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", device="cuda", torch_dtype=torch.float16)
tts.prepare_conditionals("/v/dataset/wavs/section_c_044.wav", exaggeration=0.5)
for i, s in enumerate(V):
    for k in range(int(os.environ.get("TAKES", 3))):
        torch.manual_seed(7000 + 10 * i + k)
        w = tts.generate(s, language_id="en", exaggeration=0.5, cfg_weight=0.0, temperature=0.8).squeeze().cpu().numpy()
        sf.write(os.path.join(O, f"v{i}_t{k}.wav"), w, tts.sr)
        h = asr(librosa.resample(w, orig_sr=tts.sr, target_sr=16000), generate_kwargs={"language": "en"})["text"].strip()
        print(f"v{i} t{k} {len(w) / tts.sr:4.1f}s | {s!r} -> {h!r}", flush=True)
