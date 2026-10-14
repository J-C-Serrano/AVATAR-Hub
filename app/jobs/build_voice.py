"""Background job: recordings -> dataset -> LoRA fine-tune -> pick reference clips -> 3 audition versions.
usage: python build_voice.py <voice_id>     (writes data/voices/<id>/job.json and job.log; also registers in
the terminal progress view phase0/progress via pg.py)"""
import json, os, subprocess, sys, time, glob, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import store

vid = sys.argv[1]; V = store.vdir(vid); HUB = store.HUB
S = os.path.join(HUB, "phase0", "scripts")
LOG = os.path.join(V, "job.log")
STAGES = [("convert", 0.03), ("dataset", 0.12), ("train", 0.45), ("refs", 0.05), ("audition", 0.35)]
pg_name = f"Voice build: {vid}"


def status(stage, frac, msg, state="running"):
    base = sum(w for s, w in STAGES[:[s for s, _ in STAGES].index(stage)]) if stage in dict(STAGES) else 1.0
    tot = min(1.0, base + dict(STAGES).get(stage, 0) * frac)
    json.dump({"state": state, "stage": stage, "progress": round(tot, 3), "message": msg, "time": time.time()},
              open(os.path.join(V, "job.json"), "w"))
    subprocess.run([sys.executable, os.path.join(S, "pg.py"), "manual", pg_name, f"{tot * 100:.0f}", "100", msg],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run(cmd, stage, parse=None):
    with open(LOG, "a") as lf:
        lf.write(f"\n$ {' '.join(cmd)}\n"); lf.flush()
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in p.stdout:
            lf.write(line); lf.flush()
            if parse:
                r = parse(line)
                if r: status(stage, *r)
        if p.wait() != 0: raise RuntimeError(f"{stage} failed (see job.log)")


try:
    prof = store.load_profile(vid); prof["status"] = "building"; store.save_profile(prof)
    # 1. convert all recordings to 48 kHz mono WAV (zip files are unpacked)
    status("convert", 0, "Converting recordings")
    raw, wav = os.path.join(V, "recordings"), os.path.join(V, "work", "wav48")
    os.makedirs(wav, exist_ok=True)
    for z in glob.glob(os.path.join(raw, "*.zip")):
        subprocess.run(["unzip", "-o", "-q", z, "-d", os.path.join(V, "work", "unzipped")], check=True)
    srcs = [f for f in glob.glob(os.path.join(raw, "*")) + glob.glob(os.path.join(V, "work", "unzipped", "**", "*"), recursive=True)
            if os.path.isfile(f) and not f.endswith(".zip") and not os.path.basename(f).startswith(".")]
    for i, f in enumerate(srcs):
        out = os.path.join(wav, re.sub(r"[^A-Za-z0-9_ -]+", "_", os.path.splitext(os.path.basename(f))[0]) + ".wav")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", f, "-ac", "1", "-ar", "48000", out], check=True)
        status("convert", (i + 1) / len(srcs), f"Converted {i + 1}/{len(srcs)} files")
    # 2. dataset (silence split + batched Whisper)
    status("dataset", 0, "Cutting clips and transcribing")
    ds = os.path.join(V, "dataset")
    run([sys.executable, os.path.join(S, "prep_voice_dataset.py"), wav, ds], "dataset",
        lambda l: ((int(m.group(1)) / int(m.group(2))), f"Transcribed {m.group(1)}/{m.group(2)} files") if (m := re.match(r"(\d+)/(\d+) \[", l)) else None)
    clips = json.load(open(os.path.join(ds, "clips.json")))
    minutes = sum(c["dur"] for c in clips) / 60
    # 3. LoRA fine-tune (settings validated on Julio's 17 min: r8, lr 1e-4, dropout 0.1, best epoch kept)
    status("train", 0, f"Fine-tuning on {minutes:.1f} min of speech")
    epochs = 8 if minutes >= 10 else 12
    run([sys.executable, os.path.join(S, "ft_t3_lora.py"), "--data", ds, "--out", os.path.join(V, "train"), "--epochs", str(epochs),
         "--r", "8", "--alpha", "16", "--lr", "1e-4", "--dropout", "0.1"], "train",
        lambda l: ((int(m.group(1)) / int(m.group(2))), f"Training round {m.group(1)}/{m.group(2)}") if (m := re.match(r"epoch (\d+)/(\d+) \[", l)) else None)
    os.replace(os.path.join(V, "train", "lora_best"), os.path.join(V, "train", "lora_balanced"))
    # 4 + 5. pick clean reference clips and render 3 audition versions (in-process engine)
    status("refs", 0, "Choosing reference clips")
    from engine import Engine
    import numpy as np, torch, librosa
    eng = Engine()
    split = json.load(open(os.path.join(V, "train", "split.json")))
    pool = [c for c in clips if c["clip"] in set(split["train"]) and 6.0 <= c["dur"] <= 9.8 and c["lang"] == prof["languages"][0]] \
        or sorted(clips, key=lambda c: -c["dur"])[:10]
    wavs = [librosa.load(os.path.join(ds, "wavs", c["clip"] + ".wav"), sr=16000)[0] for c in pool]
    emb = torch.from_numpy(eng.tts.ve.embeds_from_wavs(wavs, sample_rate=16000))
    cen = emb.mean(0, keepdim=True)
    sims = torch.nn.functional.cosine_similarity(emb, cen).numpy()
    order = list(np.argsort(-sims))[:5]
    refs = [os.path.join("dataset", "wavs", pool[i]["clip"] + ".wav") for i in order]
    status("refs", 1, f"Picked {len(refs)} reference clips")
    lang = prof["languages"][0]
    texts = {"en": "Hello, my name is {n}. Welcome to today's lecture. We will look at how companies create value with services, and why this matters for all of us.",
             "fi": "Hei, olen {n}. Tervetuloa luennolle. Tänään puhumme siitä, miten yritykset luovat arvoa palveluilla.",
             "sv": "Hej, jag heter {n}. Välkommen till dagens föreläsning. Idag pratar vi om hur företag skapar värde med tjänster."}
    text = texts.get(lang, texts["en"]).format(n=prof["name"].split()[0])
    base = dict(store.DEFAULT_SETTINGS, ref=refs[0], lora="train/lora_balanced")
    versions = [("A", dict(base, lora=None), "Natural: base model with your clean reference (no fine-tuning)"),
                ("B", dict(base, lora_scale=1.0), "Balanced: fine-tuned on your recordings"),
                ("C", dict(base, lora_scale=1.5), "Strong: fine-tuning amplified (more accent / personal style)")]
    rdir = os.path.join(V, "candidates", "r1"); os.makedirs(rdir, exist_ok=True)
    import soundfile as sf
    for i, (tag, s, label) in enumerate(versions):
        status("audition", i / 3, f"Rendering version {tag}")
        a, rep = eng.speak(text, lang, os.path.join(V, s["ref"]), os.path.join(V, s["lora"]) if s["lora"] else None, s["lora_scale"],
                           s["exaggeration"], s["cfg_weight"], s["temperature"], s["speed"], takes=2)
        sf.write(os.path.join(rdir, f"{tag}.wav"), a, eng.sr)
        json.dump({"tag": tag, "settings": s, "label": label, "text": text, "qc": rep}, open(os.path.join(rdir, f"{tag}.json"), "w"), indent=1, ensure_ascii=False)
    prof = store.load_profile(vid)
    prof.update(status="review", refs=refs, minutes=round(minutes, 1), clips=len(clips), test_text=text)
    prof["rounds"] = [{"round": 1, "feedback": None, "notes": ["first audition"], "dir": "candidates/r1"}]
    store.save_profile(prof)
    status("audition", 1, "Ready: listen to the 3 versions", state="done")
except Exception as e:
    status(json.load(open(os.path.join(V, "job.json")))["stage"] if os.path.exists(os.path.join(V, "job.json")) else "convert", 0, f"Error: {e}", state="error")
    with open(LOG, "a") as lf: lf.write(f"\nERROR: {e}\n")
    raise
finally:
    subprocess.run([sys.executable, os.path.join(S, "pg.py"), "rm", pg_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
