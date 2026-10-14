import sys, time, re, numpy as np, soundfile as sf, torch
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
TEXT = ("Hello, I am Julio Serrano. Today I want to talk about servitization. "
 "Manufacturing companies no longer win only by selling machines. They win by selling outcomes, like uptime, performance, and reliable service over many years. "
 "This changes how we organise, how we price, and how we build trust with customers. "
 "In this short video, my digital avatar is presenting the idea, using my own voice and my own face, with my consent.")
VARIANTS = {  # name: (exaggeration, cfg_weight, temperature)
  "a_cfg0":   (0.5, 0.0, 0.8),
  "b_cfg0_ex7": (0.7, 0.0, 0.8),
  "c_default": (0.5, 0.5, 0.8),
}
m = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
sents = re.split(r"(?<=[.!?])\s+", TEXT.strip())
for name,(ex,cfg,temp) in VARIANTS.items():
    torch.manual_seed(7); t=time.time(); parts=[]
    for s in sents:
        w = m.generate(s, language_id="en", audio_prompt_path="/in/voice_24k.wav", exaggeration=ex, cfg_weight=cfg, temperature=temp)
        parts += [w.squeeze().cpu().numpy(), np.zeros(int(0.25*m.sr), dtype=np.float32)]
    a = np.concatenate(parts); sf.write(f"/out/long_en_{name}.wav", a, m.sr)
    print(name, "%.1fs audio, %.0fs compute"%(len(a)/m.sr, time.time()-t), flush=True)
