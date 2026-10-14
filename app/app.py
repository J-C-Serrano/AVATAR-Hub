"""AVATAR Hub — University of Vaasa voice & video tool (Streamlit, local, no login).
Run: app/run.sh  ->  http://localhost:8501"""
import json, os, re, subprocess, sys, time
import streamlit as st
import soundfile as sf
sys.path.insert(0, os.path.dirname(__file__))
import store, feedback
from engine import TONES, PACE, FORMATS, export

st.set_page_config(page_title="UVA Voice & Video Tool", page_icon="🎙️", layout="wide")
LANGS = {"en": "English", "fi": "Suomi (Finnish)", "sv": "Svenska (Swedish)"}
SCRIPT_MD = os.path.join(store.HUB, "docs", "voice_recording_script.md")

st.markdown("""
<style>
:root { --navy:#123a66; --accent:#f0a028; --ink:#e6ebf3; --muted:#9aa6bb; --card:#162033; --card2:#1c2940; --bg:#0e1420; --line:#26344d; }
.stApp { background: var(--bg); }
.hero { background: linear-gradient(120deg, #0b2a4a 0%, #164a7a 100%); color: #fff; border-radius: 18px;
        padding: 28px 34px; margin-bottom: 22px; border-bottom: 6px solid var(--accent); box-shadow: 0 6px 24px rgba(0,0,0,.35); }
.hero h1 { color:#fff; font-size: 2.2rem; margin: 0 0 6px 0; letter-spacing: -0.5px; }
.hero p { color:#c9d8ea; margin:0; font-size: 1.05rem; }
.tile { border-radius: 18px; padding: 26px 24px; background: var(--card); border: 1px solid var(--line);
        box-shadow: 0 4px 18px rgba(0,0,0,.30); min-height: 170px; }
.tile h3 { margin: 6px 0 6px 0; color: var(--ink); } .tile p { color: var(--muted); margin: 0; }
.tile.off { opacity: .38; filter: grayscale(1); }
.big { font-size: 2.4rem; }
.badge { display:inline-block; padding: 2px 10px; border-radius: 999px; font-size: .78rem; font-weight: 600; }
.b-ready { background:#14361f; color:#6fdc95; } .b-review { background:#3d2c0a; color:#f4c060; }
.b-building { background:#132c4d; color:#7fb2f0; } .b-recording { background:#262d3a; color:#b8c0cf; }
.vcard { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 14px 16px; margin-bottom: 8px; color: var(--ink); }
.note { color: var(--muted); font-size: .9rem; }
div[data-testid="stButton"] > button[kind="primary"] { background: var(--accent); border-color: var(--accent); color: #111; font-weight: 600; }
div[data-testid="stButton"] > button[kind="primary"]:hover { background: #ffb845; border-color: #ffb845; color: #111; }
</style>""", unsafe_allow_html=True)

ss = st.session_state
ss.setdefault("page", "home"); ss.setdefault("vview", "library"); ss.setdefault("vid", None)


def hero(sub="Voice and video tool"):
    st.markdown(f'<div class="hero"><h1>University of Vaasa · {sub}</h1>'
                '<p>Create your AI voice and avatar locally. Nothing leaves this computer.</p></div>', unsafe_allow_html=True)


@st.cache_resource(show_spinner="Loading the voice engine (first time ≈ 30 s)…")
def get_engine():
    from engine import Engine
    return Engine()


def run_with_progress(fn, label="Generating"):
    """Run fn(progress_cb) in a thread; animate a real progress bar with stage text and time left. Returns fn's result."""
    import threading
    st_ = {"f": 0.0, "msg": "Starting…", "res": None, "err": None}
    def cb(f, msg): st_["f"], st_["msg"] = f, msg
    def work():
        try: st_["res"] = fn(cb)
        except Exception as e: st_["err"] = e
    th = threading.Thread(target=work, daemon=True); t0 = time.time(); th.start()
    bar = st.progress(0.0, text=f"{label}…"); eta_s = None
    while th.is_alive():
        el = time.time() - t0; f = st_["f"]
        if f > 0.04:
            est = el * (1 - f) / f; eta_s = est if eta_s is None else 0.8 * eta_s + 0.2 * est
            left = f" · about {max(1, round(eta_s))} s left"
        else:
            left = " · estimating time…"
        bar.progress(min(f, 0.999), text=f"{f * 100:.0f}% · {st_['msg']}{left}")
        time.sleep(0.25)
    th.join()
    if st_["err"]: bar.progress(st_["f"], text=f"Stopped: {st_['err']}"); raise st_["err"]
    bar.progress(1.0, text=f"100% · Done in {time.time() - t0:.0f} s")
    return st_["res"]


def badge(status):
    label = {"ready": "Ready", "review": "Needs review", "building": "Building…", "recording": "Recording"}.get(status, status)
    return f'<span class="badge b-{status}">{label}</span>'


def dur(path):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True).stdout
        return float(out.strip())
    except Exception:
        return 0.0


# ------------------------------------------------------------------ home
def home():
    hero()
    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        st.markdown('<div class="tile"><div class="big">🎙️</div><h3>Voice</h3><p>Clone your voice from a short recording and turn any text into speech.</p></div>', unsafe_allow_html=True)
        if st.button("Open Voice", type="primary", use_container_width=True):
            ss.page, ss.vview = "voice", "library"; st.rerun()
    with c2:
        st.markdown('<div class="tile off"><div class="big">🧑‍💼</div><h3>AI Avatar</h3><p>Your animated portrait for lectures.</p></div>', unsafe_allow_html=True)
        st.button("Coming soon", disabled=True, use_container_width=True, key="b_av")
    with c3:
        st.markdown('<div class="tile off"><div class="big">🎬</div><h3>AI Studio</h3><p>Slides, voice and avatar combined into finished videos.</p></div>', unsafe_allow_html=True)
        st.button("Coming soon", disabled=True, use_container_width=True, key="b_st")


# ------------------------------------------------------------------ voice: library + speak
def library():
    voices = store.list_voices()
    top = st.columns([6, 1.4])
    top[0].subheader("Your voices")
    if top[1].button("➕ Create new voice", type="primary", use_container_width=True):
        ss.vview = "create"; ss.vid = None; st.rerun()
    if not voices:
        st.info("No voices yet. Create your first one."); return
    names = {v["id"]: v for v in voices}
    if ss.vid not in names: ss.vid = next((v["id"] for v in voices if v.get("ready")), voices[0]["id"])
    left, right = st.columns([1.1, 2.6], gap="large")
    with left:
        for v in voices:
            sel = v["id"] == ss.vid
            st.markdown(f'<div class="vcard"><b>{"▶ " if sel else ""}{v["name"]}</b> &nbsp; {badge(v["status"])}<br>'
                        f'<span class="note">{", ".join(LANGS.get(l, l) for l in v["languages"])}'
                        f'{" · " + str(v.get("minutes")) + " min recorded" if v.get("minutes") else ""}</span></div>', unsafe_allow_html=True)
            if st.button("Select" if not sel else "Selected", key=f"sel_{v['id']}", disabled=sel, use_container_width=True):
                ss.vid = v["id"]; st.rerun()
    with right:
        v = names[ss.vid]
        if v["status"] == "building":
            st.info("This voice is being built."); st.button("Show progress", on_click=lambda: ss.update(vview="build")); return
        if v["status"] == "review":
            st.warning("This voice is waiting for your review."); st.button("Continue review", type="primary", on_click=lambda: ss.update(vview="review")); return
        if v["status"] == "recording":
            st.info("Recordings in progress."); st.button("Continue recording", type="primary", on_click=lambda: ss.update(vview="record")); return
        speak_panel(v)


def speak_panel(v):
    st.markdown(f"### Speak with **{v['name']}**")
    text = st.text_area("Text", height=150, placeholder="Type or paste the text you want this voice to say…", key=f"txt_{v['id']}")
    c = st.columns([1.2, 1.2, 1.2, 1.6])
    lang = c[0].selectbox("Language", v["languages"], format_func=lambda l: LANGS.get(l, l))
    with st.expander("Optional: tone, pace and file formats"):
        oc = st.columns(3)
        tone = oc[0].radio("Tone", list(TONES), horizontal=False)
        pace = oc[1].radio("Pace", list(PACE), index=1)
        oc[2].markdown("**File formats**")
        fmts = [f for f in FORMATS if oc[2].checkbox(f, value=(f in ("WAV", "MP3")), key=f"fmt_{f}")]
        adv = st.toggle("Fine control (advanced)")
        s = dict(v["settings"]); s.update(TONES[tone]); s["speed"] = round(s.get("speed", 1.0) * PACE[pace], 3)
        if adv:
            ac = st.columns(4)
            s["exaggeration"] = ac[0].slider("Expressiveness", 0.25, 1.3, float(s["exaggeration"]), 0.05)
            s["temperature"] = ac[1].slider("Variation", 0.5, 1.0, float(s["temperature"]), 0.05)
            s["speed"] = ac[2].slider("Speed", 0.8, 1.25, float(s["speed"]), 0.01)
            if s.get("lora"): s["lora_scale"] = ac[3].slider("Personal style strength", 0.0, 2.0, float(s["lora_scale"]), 0.1)
    if not fmts: fmts = ["WAV"]
    if st.button("🔊 Create speech", type="primary", disabled=not text.strip()):
        eng = get_engine()
        V = store.vdir(v["id"]); seed = int(time.time()) % 10000
        a, rep = run_with_progress(lambda cb: eng.speak(text, lang, os.path.join(V, s["ref"]), os.path.join(V, s["lora"]) if s.get("lora") else None,
                           s.get("lora_scale", 1.0), s["exaggeration"], s["cfg_weight"], s["temperature"], s.get("speed", 1.0),
                           takes=3, seed=seed, progress=cb), "Creating speech")
        d = store.new_generation_dir(v["id"], text)
        paths = export(a, eng.sr, os.path.join(d, "speech"), fmts)
        meta = {"text": text, "language": lang, "tone": tone, "pace": pace, "settings": s, "formats": fmts,
                "files": {k: os.path.basename(p) for k, p in paths.items()}, "duration_s": round(len(a) / eng.sr, 1),
                "created": time.strftime("%Y-%m-%d %H:%M:%S"), "qc": rep}
        json.dump(meta, open(os.path.join(d, "meta.json"), "w"), indent=1, ensure_ascii=False)
        st.success(f"Done: {meta['duration_s']} s of speech, saved under {v['name']}.")
        st.audio(paths.get("WAV") or paths.get("_wav"))
    history(v)


def history(v):
    gens = store.generations(v["id"])
    if not gens: return
    st.markdown("#### Everything made with this voice")
    for g in gens[:30]:
        with st.container(border=True):
            st.markdown(f"**{g['created']}** · {LANGS.get(g['language'], g['language'])} · {g['tone']} · {g['pace']} · {g['duration_s']} s")
            st.caption(g["text"][:300] + ("…" if len(g["text"]) > 300 else ""))
            wav = os.path.join(g["dir"], g["files"].get("WAV") or g["files"].get("_wav", "speech.wav"))
            if os.path.exists(wav): st.audio(wav)
            cols = st.columns(max(1, len(g["formats"])))
            for i, f in enumerate(g["formats"]):
                p = os.path.join(g["dir"], g["files"][f])
                if os.path.exists(p):
                    mime = {"WAV": "audio/wav", "MP3": "audio/mpeg", "M4A": "audio/mp4", "OGG": "audio/ogg", "FLAC": "audio/flac"}[f]
                    cols[i].download_button(f"⬇ {f}", open(p, "rb").read(), file_name=f"{v['id']}_{os.path.basename(g['dir'])}.{FORMATS[f]}",
                                            mime=mime, key=f"dl_{g['dir']}_{f}", use_container_width=True)


# ------------------------------------------------------------------ voice: create (consent + recording)
def create():
    st.subheader("Create a new voice")
    with st.form("new_voice"):
        name = st.text_input("Voice name", placeholder="e.g. Julio Serrano")
        langs = st.multiselect("Languages this voice will speak (first = main)", list(LANGS), default=["en"], format_func=lambda l: LANGS[l])
        st.markdown("**Consent**")
        who = st.text_input("Full name of the person whose voice this is")
        statement = f"I agree that my voice is recorded and used to create a synthetic voice for University of Vaasa teaching material. I can ask for it to be deleted at any time."
        ok = st.checkbox(statement)
        if st.form_submit_button("Continue to recording", type="primary"):
            if not (name.strip() and langs and who.strip() and ok):
                st.error("Please fill in the name, languages and consent.")
            else:
                prof = store.create_voice(name.strip(), langs, who.strip(), statement)
                ss.vid, ss.vview = prof["id"], "record"; st.rerun()


def script_sections():
    md = open(SCRIPT_MD, encoding="utf-8").read()
    parts = re.split(r"\n(?=## )", md)
    tips = next((p for p in parts if p.startswith("## Before you start")), "")
    secs = [(m.group(1), p) for p in parts if (m := re.match(r"## (?:Optional )?Section ([A-F])", p))]
    return tips, secs


def record():
    v = store.load_profile(ss.vid); V = store.vdir(v["id"])
    st.subheader(f"Record: {v['name']}")
    tips, secs = script_sections()
    with st.expander("Before you start: room, microphone and level (read once)"):
        st.markdown(tips.replace("## Before you start", "", 1))
    st.markdown("Read each section aloud. **Record directly here** or **upload** files you recorded elsewhere. "
                "Mistakes are fine: everything is transcribed automatically.")
    for letter, body in secs:
        title = body.splitlines()[0].replace("## ", "")
        with st.expander(title):
            st.markdown("\n".join(body.splitlines()[1:]))
            lang_tag = ""
            if letter == "F":
                extra = [l for l in v["languages"] if l != "en"]
                if not extra: st.caption("Only needed if this voice also speaks Finnish or Swedish."); continue
                lang_tag = "_" + {"fi": "finnish", "sv": "swedish"}[st.radio("Language of this recording", extra, format_func=lambda l: LANGS[l], key=f"lg_{letter}", horizontal=True)]
            rec = st.audio_input(f"Record section {letter}", key=f"rec_{v['id']}_{letter}{lang_tag}")
            if rec is not None:
                fn = f"section_{letter}{lang_tag}_{time.strftime('%H%M%S')}.wav"
                if ss.get(f"saved_{letter}{lang_tag}") != rec.file_id:
                    store.save_recording(v["id"], fn, rec.getvalue()); ss[f"saved_{letter}{lang_tag}"] = rec.file_id
                    st.success(f"Saved {fn}")
    st.markdown("#### Or upload recordings")
    ups = st.file_uploader("Audio files or a .zip (wav, mp3, m4a, ogg, flac, webm). Name Finnish/Swedish files with 'finnish'/'swedish'.",
                           type=["wav", "mp3", "m4a", "ogg", "flac", "webm", "aac", "zip"], accept_multiple_files=True)
    for u in ups or []:
        if ss.get(f"up_{u.file_id}") is None:
            store.save_recording(v["id"], u.name, u.getvalue()); ss[f"up_{u.file_id}"] = True
    recs = store.recordings(v["id"])
    total = sum(dur(os.path.join(V, "recordings", r)) for r in recs if not r.endswith(".zip"))
    st.markdown("#### Collected")
    if recs:
        st.write(", ".join(recs))
    has_zip = any(r.endswith(".zip") for r in recs)
    target = 15 * 60
    st.progress(min(1.0, total / target), text=f"{total / 60:.1f} min recorded{' (+ zip, measured during build)' if has_zip else ''} · recommended ≈ 15–25 min, minimum 5")
    ok = total >= 5 * 60 or has_zip
    if st.button("🚀 Build my voice", type="primary", disabled=not ok):
        prof = store.load_profile(v["id"]); prof["status"] = "building"; store.save_profile(prof)
        json.dump({"state": "running", "stage": "convert", "progress": 0, "message": "Starting", "time": time.time()}, open(os.path.join(V, "job.json"), "w"))
        subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), "jobs", "build_voice.py"), v["id"]],
                         stdout=open(os.path.join(V, "job.stdout"), "w"), stderr=subprocess.STDOUT, start_new_session=True)
        ss.vview = "build"; st.rerun()


# ------------------------------------------------------------------ voice: build progress
STAGE_NAMES = {"convert": "Converting recordings", "dataset": "Cutting clips + transcribing", "train": "Fine-tuning the voice",
               "refs": "Choosing reference clips", "audition": "Rendering 3 versions"}


@st.fragment(run_every=2)
def build_progress(vid):
    j = store.job_status(vid) or {}
    st.progress(float(j.get("progress", 0)), text=f"{j.get('progress', 0) * 100:.0f}% · {j.get('message', '')}")
    cur = j.get("stage")
    order = list(STAGE_NAMES)
    for s in order:
        done = j.get("state") == "done" or (cur in order and order.index(s) < order.index(cur))
        icon = "✅" if done else ("⏳" if s == cur else "⬜")
        st.markdown(f"{icon} {STAGE_NAMES[s]}")
    if j.get("state") == "done":
        st.success("Your voice is ready to review.")
        if st.button("Listen to the 3 versions", type="primary"):
            ss.vview = "review"; st.rerun(scope="app")
    elif j.get("state") == "error":
        st.error(j.get("message")); st.code(open(store.vdir(vid, "job.log")).read()[-3000:] if os.path.exists(store.vdir(vid, "job.log")) else "")


def build():
    v = store.load_profile(ss.vid)
    st.subheader(f"Building: {v['name']}")
    st.caption("You can leave this page; the job keeps running. Typical time for 15–20 min of recordings: 5–8 minutes.")
    build_progress(v["id"])


# ------------------------------------------------------------------ voice: review + feedback loop
def review():
    v = store.load_profile(ss.vid); V = store.vdir(v["id"])
    st.subheader(f"Review: {v['name']}")
    rnd = v["rounds"][-1]; rdir = os.path.join(V, rnd["dir"])
    st.caption(f"Round {rnd['round']}" + (f" · your feedback: “{rnd['feedback']}”" if rnd.get("feedback") else "")
               + (" · " + "; ".join(rnd["notes"]) if rnd.get("notes") else ""))
    cands = []
    for tag in ("A", "B", "C"):
        m = os.path.join(rdir, f"{tag}.json")
        if os.path.exists(m): cands.append(json.load(open(m)))
    cols = st.columns(3, gap="large")
    for c, col in zip(cands, cols):
        with col, st.container(border=True):
            st.markdown(f"### Version {c['tag']}"); st.caption(c["label"])
            st.audio(os.path.join(rdir, f"{c['tag']}.wav"))
    pick = st.radio("Which version is closest to what you want?", [c["tag"] for c in cands], horizontal=True, key=f"pick_{rnd['round']}")
    chosen = next(c for c in cands if c["tag"] == pick)
    st.markdown("**Not quite right?** Describe what to improve, e.g. *“more accent”, “more expressive”, “slower”, “sounds robotic”*.")
    fb = st.text_area("Feedback", key=f"fb_{rnd['round']}", height=80)
    b1, b2 = st.columns([1, 1])
    if b1.button("🔁 Try again with this feedback", disabled=not fb.strip()):
        var, notes = feedback.variants(chosen["settings"], fb, n_refs=len(v.get("refs", [])), seed=rnd["round"])
        eng = get_engine(); new = rnd["round"] + 1; nd = os.path.join(V, "candidates", f"r{new}"); os.makedirs(nd, exist_ok=True)
        def render_all(cb):
          for i, (tag, s, label) in enumerate(var):
            if "ref_index" in s and v.get("refs"): s["ref"] = v["refs"][s.pop("ref_index") % len(v["refs"])]
            a, rep = eng.speak(v.get("test_text", chosen["text"]), v["languages"][0], os.path.join(V, s["ref"]),
                               os.path.join(V, s["lora"]) if s.get("lora") else None, s.get("lora_scale", 1.0), s["exaggeration"],
                               s["cfg_weight"], s["temperature"], s.get("speed", 1.0), takes=2, seed=s.pop("seed", 0),
                               progress=lambda f, m, i=i, tag=tag: cb((i + f) / 3, f"Version {tag} of A/B/C · {m}"))
            sf.write(os.path.join(nd, f"{tag}.wav"), a, eng.sr)
            json.dump({"tag": tag, "settings": s, "label": f"Based on {pick}: {label}", "text": chosen["text"], "qc": rep},
                      open(os.path.join(nd, f"{tag}.json"), "w"), indent=1, ensure_ascii=False)
        run_with_progress(render_all, "Rendering 3 new versions")
        v["rounds"].append({"round": new, "feedback": fb, "based_on": f"r{rnd['round']}:{pick}", "notes": notes, "dir": f"candidates/r{new}"})
        store.save_profile(v); st.rerun()
    if b2.button(f"✅ Save version {pick} as my voice profile", type="primary"):
        v["settings"] = dict(chosen["settings"]); v["status"] = "ready"; v["ready"] = True
        v["chosen"] = {"round": rnd["round"], "tag": pick}; store.save_profile(v)
        ss.vview = "library"; st.toast("Voice profile saved"); st.rerun()
    if len(v["rounds"]) > 1 and st.button("↩ Back to the previous round"):
        v["rounds"].pop(); store.save_profile(v); st.rerun()


# ------------------------------------------------------------------ router
def voice():
    hero("Voice")
    nav = st.columns([1, 1, 6])
    if nav[0].button("⟵ Home"): ss.page = "home"; st.rerun()
    if ss.vview != "library" and nav[1].button("Voices"): ss.vview = "library"; st.rerun()
    {"library": library, "create": create, "record": record, "build": build, "review": review}[ss.vview]()


{"home": home, "voice": voice}[ss.page]()
