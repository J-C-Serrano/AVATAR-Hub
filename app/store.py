"""Voice library on disk: data/voices/<voice_id>/
  profile.json        name, languages, status, active settings, chosen candidate, history of feedback rounds
  consent.json        who consented, when, statement
  recordings/         raw uploads / browser recordings (any format)
  dataset/            clips + metadata.csv (built by the job)
  train/              LoRA checkpoints (lora_balanced, lora_strong)
  candidates/rN/      audition samples per feedback round (A/B/C wav + params.json)
  generations/        everything produced with the voice (one folder per generation)
  job.json / job.log  background job status"""
import json, os, re, shutil, time
from datetime import datetime

HUB = os.environ.get("HUB_DIR", "/hub")
VOICES = os.path.join(HUB, "data", "voices")
os.makedirs(VOICES, exist_ok=True)

DEFAULT_SETTINGS = {"lora": None, "lora_scale": 1.0, "ref": None, "exaggeration": 0.5, "cfg_weight": 0.0,
                    "temperature": 0.8, "speed": 1.0}


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or f"voice-{int(time.time())}"


def vdir(vid, *p):
    return os.path.join(VOICES, vid, *p)


def list_voices():
    out = []
    for vid in sorted(os.listdir(VOICES)):
        p = vdir(vid, "profile.json")
        if os.path.exists(p):
            out.append(load_profile(vid))
    return out


def load_profile(vid):
    return json.load(open(vdir(vid, "profile.json")))


def save_profile(prof):
    prof["updated"] = datetime.now().isoformat(timespec="seconds")
    json.dump(prof, open(vdir(prof["id"], "profile.json"), "w"), indent=1, ensure_ascii=False)


def create_voice(name, languages, consent_by, statement):
    vid = slug(name)
    base, i = vid, 2
    while os.path.exists(vdir(vid)):
        vid = f"{base}-{i}"; i += 1
    for sub in ("recordings", "dataset", "train", "candidates", "generations"):
        os.makedirs(vdir(vid, sub), exist_ok=True)
    now = datetime.now().isoformat(timespec="seconds")
    json.dump({"name": consent_by, "statement": statement, "time": now}, open(vdir(vid, "consent.json"), "w"), indent=1, ensure_ascii=False)
    prof = {"id": vid, "name": name, "languages": languages, "status": "recording", "created": now,
            "settings": dict(DEFAULT_SETTINGS), "rounds": [], "ready": False}
    save_profile(prof)
    return prof


def recordings(vid):
    d = vdir(vid, "recordings")
    return sorted(f for f in os.listdir(d) if not f.startswith(".")) if os.path.isdir(d) else []


def save_recording(vid, filename, data):
    safe = re.sub(r"[^A-Za-z0-9._ -]+", "_", filename)
    path = vdir(vid, "recordings", safe)
    with open(path, "wb") as f: f.write(data)
    return path


def job_status(vid):
    p = vdir(vid, "job.json")
    return json.load(open(p)) if os.path.exists(p) else None


def generations(vid):
    d = vdir(vid, "generations")
    out = []
    for g in sorted(os.listdir(d), reverse=True) if os.path.isdir(d) else []:
        m = os.path.join(d, g, "meta.json")
        if os.path.exists(m):
            meta = json.load(open(m)); meta["dir"] = os.path.join(d, g); out.append(meta)
    return out


def new_generation_dir(vid, text):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    words = "-".join(re.sub(r"[^a-z0-9 ]", "", text.lower()).split()[:5]) or "speech"
    d = vdir(vid, "generations", f"{stamp}_{words}")
    os.makedirs(d, exist_ok=True)
    return d


def import_existing(name, vid, lora_src, ref_src, languages, settings_over=None):
    """Register an already trained voice (used once for Julio's first voice)."""
    if os.path.exists(vdir(vid, "profile.json")): return load_profile(vid)
    for sub in ("recordings", "dataset", "train", "candidates", "generations"):
        os.makedirs(vdir(vid, sub), exist_ok=True)
    shutil.copytree(lora_src, vdir(vid, "train", "lora_balanced"), dirs_exist_ok=True)
    shutil.copy(ref_src, vdir(vid, "train", "ref.wav"))
    s = dict(DEFAULT_SETTINGS, lora="train/lora_balanced", ref="train/ref.wav", **(settings_over or {}))
    now = datetime.now().isoformat(timespec="seconds")
    prof = {"id": vid, "name": name, "languages": languages, "status": "ready", "created": now, "settings": s,
            "rounds": [], "ready": True, "note": "Imported from phase0 fine-tune (r8, lr 1e-4, best epoch 6)."}
    json.dump({"name": name, "statement": "Recorded by the person for this project (see HANDOVER).", "time": now},
              open(vdir(vid, "consent.json"), "w"), indent=1)
    save_profile(prof)
    return prof
