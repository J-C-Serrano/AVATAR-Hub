import time, numpy as np, soundfile as sf, torch
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
T = {"fi": ["Hei, olen Julio Serrano. Tänään haluan puhua palveluistamisesta.",
            "Valmistavat yritykset eivät enää voita pelkästään myymällä koneita. Ne myyvät tuloksia, kuten käytettävyyttä ja luotettavaa palvelua vuosien ajan.",
            "Tässä lyhyessä videossa digitaalinen avatarini esittelee ajatuksen omalla äänelläni ja kasvoillani, suostumuksellani."],
     "sv": ["Hej, jag är Julio Serrano. Idag vill jag prata om servicefiering.",
            "Tillverkande företag vinner inte längre bara genom att sälja maskiner. De säljer resultat, som tillgänglighet och pålitlig service under många år.",
            "I den här korta videon presenterar min digitala avatar idén med min egen röst och mitt eget ansikte, med mitt samtycke."]}
m = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
for lang, sents in T.items():
    torch.manual_seed(7); parts=[]
    for s in sents:
        w = m.generate(s, language_id=lang, audio_prompt_path="/in/ref_vid_A.wav", exaggeration=0.5, cfg_weight=0.0, temperature=0.8)
        parts += [w.squeeze().cpu().numpy(), np.zeros(int(0.25*m.sr), dtype=np.float32)]
    sf.write(f"/out/clone_{lang}_vA.wav", np.concatenate(parts), m.sr); print(lang, "done", flush=True)
