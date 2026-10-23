"""Try spelling variants of an acronym in a voice; report how often Whisper hears it right.
usage (in avatar-hub-app:p0): python spell_test.py <voice_id> <json: [{"name","template","variants":[..],"expect":regex}]> [takes]
template contains {X}, replaced by each variant."""
import json, os, re, sys
sys.path.insert(0, "/hub/app")
import torch, librosa
from engine import Engine
vid, cases = sys.argv[1], json.load(open(sys.argv[2])); takes = int(sys.argv[3]) if len(sys.argv) > 3 else 4
V = f"/hub/data/voices/{vid}"; s = json.load(open(f"{V}/profile.json"))["settings"]
eng = Engine(); eng.use(os.path.join(V, s["lora"]), s["lora_scale"]); eng.set_ref(os.path.join(V, s["ref"]), 0.35)
for c in cases:
    for v in c["variants"]:
        text = c["template"].replace("{X}", v); ok = 0; heard = []
        for k in range(takes):
            torch.manual_seed(7 + k); eng._clear_hooks()
            w = eng.tts.generate(text, language_id="en", exaggeration=0.35, cfg_weight=0.0, temperature=0.6).squeeze().cpu().numpy()
            h = eng.asr(librosa.resample(w, orig_sr=eng.sr, target_sr=16000), generate_kwargs={"language": "en"})["text"].strip()
            ok += bool(re.search(c["expect"], h)); heard.append(h)
        print(f"{c['name']} | {v!r}: {ok}/{takes} | " + " || ".join(heard[:2]), flush=True)
