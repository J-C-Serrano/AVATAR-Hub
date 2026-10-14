# AVATAR Hub — Handover File

> **Purpose:** single source of truth for project history and context, so any CLI / AI model
> can pick up where the last one left off. **Read this first. Update it at the end of every
> working session** (revise Status / Decisions / Next steps, append to the Changelog).

Last updated: 2026-10-13 · Owner: Julio Serrano

> **Repo:** `git@github.com:J-C-Serrano/AVATAR-Hub.git` (**public**, own repo, branch `main`).
> **Rule: at the end of every session, update this file, then `git add -A && git commit && git push`.**
> The repo is public: never commit secrets, photos/voice samples, consent videos, generated videos or model weights (see `.gitignore`).

---

## 1. Project summary

Building software that creates a **talking-head video avatar** from ~10 studio photos of a
person, clones their voice from a ~30-minute audio/video recording, and renders **lip-synced
video offline/batch** (not real-time).

**Why:** internal tool, similar in spirit to HeyGen / Synthesia / D-ID but self-hosted and
open-source, run on hardware already owned rather than a SaaS API.

## 2. Hardware / environment

| Item | Detail |
|---|---|
| Machine | Dell workstation with NVIDIA GB10 "Spark" (DGX Spark) |
| Memory | 128 GB unified LPDDR5x shared CPU/GPU, only ~273 GB/s bandwidth (vs. 1 TB/s+ on discrete GPUs) |
| CPU / GPU arch | ARM64 CPU, Blackwell GPU, compute capability **sm_121** |
| OS | Linux 6.17.0-1008-nvidia |
| Project dir | `/home/julios/AI_Projects/AVATAR Hub` |
| Extra inference | Ollama cloud endpoint available if local isn't enough |

**Key constraint (research, Oct 2026):**
- GB10/sm_121 software support is still immature.
- flash-attention has no official sm_121 build → needs source-build workarounds inside
  NVIDIA's NGC PyTorch container (**25.10-py3 or later**).
- Plain pip PyTorch does **not** support sm_121 at all.
- Plenty of *capacity* (128 GB fits large models) but *bandwidth-bound* → good for
  batch/offline work, not real-time/low-latency generation.

## 3. Decisions made

| Date | Decision | Why |
|---|---|---|
| 2026-10-13 | 2D talking-head video, offline/batch | Scope; hardware is bandwidth-bound |
| 2026-10-13 | Context: **university**, Finland/EU; outputs internal and external; uses: lecture videos, announcements, paid online courses | Julio |
| 2026-10-13 | Production stack: permissive licenses only | Julio |
| 2026-10-13 | Consent = spoken phrase, recorded by **camera or uploaded file**; **remote enrollment allowed**; evidence stored in system | Julio (supersedes in-person-only) |
| 2026-10-13 | Enrollment accepts up to 30 min of audio from files (+ ~10 photos) | Julio |
| 2026-10-13 | **Anyone can render any avatar; consent on file unlocks it** | Julio |
| 2026-10-13 | Demo: **no login**, Streamlit UI; access campus + external | Julio |
| 2026-10-13 | Ollama cloud allowed; DPA assumed for all instances | Julio |
| 2026-10-13 | Disclosure: small "AI" corner mark + invisible C2PA/watermark (approved) | Julio |
| 2026-10-13 | This is a **demo / proof of concept**: enrollment-verification concerns deferred to production | Julio |
| 2026-10-13 | Deletion = plain "Delete avatar and data" button, no keys; **consent video is kept** after deletion; no retention limit | Julio (supersedes delete-key design) |
| 2026-10-13 | No script approval | Julio |
| 2026-10-13 | Languages: Finnish, English, Swedish; voice-quality problems fixed on the go | Julio |
| 2026-10-13 | **Voice must keep the speaker's own accent** (English must sound like Julio's accented English, not native/"perfect" English) | Julio |
| 2026-10-13 | **Visual realism:** no unnaturally white teeth; head movement must be more than a few cm (natural nods/tilts/turns) | Julio |
| 2026-10-13 | Demo target: ~30 s video | Julio |
| 2026-10-13 | Repo is public on GitHub, own repo, **Apache-2.0** license | Julio |

Architecture: `ARCHITECTURE.md` v0.3 (demo-first). Approved to start Phase 0.

## 4. Open questions

- [ ] Final consent texts fi/en/sv — university legal to review (must cover "anyone may render my likeness").
- [ ] Minimum audio duration for fine-tune vs zero-shot (Phase 0).
- [ ] Production phase (later): enrollment verification, access control, delete authorisation, counsel/DPO review.

## 5. Proposed pipeline

```
10 studio photos ──► best-frame selection/alignment ──► source portrait
30-min video/audio ──► extract + clean audio ──► voice-clone model (fine-tuned)
script/text ──► cloned-voice TTS ──► speech .wav
source portrait + speech .wav ──► talking-head animation model ──► lip-synced video
```

The 10 photos don't need full 3D reconstruction for a 2D talking head — they are used to
pick/curate the cleanest frontal reference, and optionally to build a multi-image identity
anchor (PhotoMaker / InstantID / ConsistentID) if generating stylized avatar variants later.

## 6. Model shortlist (researched 2026-10-13)

### Talking-head animation (photo + audio → lip-synced video)

| Model | License | VRAM | Notes |
|---|---|---|---|
| **EchoMimicV3 (Flash)** — recommended start | Apache-2.0 | ~12 GB | AntGroup, AAAI 2026, actively maintained, no face-mask needed, 768×768 |
| LivePortrait (+ audio-driven fork) | MIT, but InsightFace buffalo_l dep is non-commercial | 8–16 GB | Fast iteration/testing; license caveat if commercial |
| Ditto | Apache-2.0 | moderate | Motion-space diffusion, real-time capable |
| daVinci-MagiHuman (15B) | Apache-2.0 | ~80 GB class (H100 ref) | Highest fidelity; "quality ceiling" once env is proven |
| SadTalker | permissive | low | Simple smoke-test for the environment |

### Voice cloning (30-min recording → clonable voice)

| Model | License | VRAM | Notes |
|---|---|---|---|
| **Chatterbox (Resemble AI)** — recommended | MIT | ~6–7 GB | Clean commercial rights, fine-tunable |
| **CosyVoice2** — recommended alt | Apache-2.0 | moderate | Alibaba, strong multilingual, commercial-safe |
| XTTS-v2 (Coqui) | Coqui Public Model License — non-commercial | ~4–6 GB | Very good quality, blocked for commercial use |
| F5-TTS | code MIT, weights CC-BY-NC | ~4–8 GB | Same commercial caveat |
| Fish-Speech | commercial use needs paid license | — | Rule out unless licensed |

30 min of audio is far above the ~5–10 s these models need for zero-shot cloning; the real
value is **fine-tuning** (Chatterbox and CosyVoice2 both support it) for better fidelity.

## 7. Legal & compliance (summary — detail in ARCHITECTURE.md §8; needs counsel/DPO review)

Not legal advice. Finland/EU (GDPR, EU AI Act).

- **Licenses:** permissive only; audit weights + transitive deps; exclude InsightFace buffalo_l, XTTS-v2, F5-TTS weights, Fish-Speech.
- **Consent:** recorded phrase (camera/file), versioned text, hashed, append-only; consent video survives avatar deletion.
- **Remote enrollment has no identity verification in the demo** (deferred to production).
- **Disclosure:** corner "AI" mark + C2PA + invisible watermark.
- **Data:** on-prem, encrypted; Ollama cloud allowed for text (DPA assumed). `client_ref` (IP/session) is personal data.
- **Deletion:** plain delete-avatar button; consent video kept; no retention limit.

## 8. Architecture (summary — full: `ARCHITECTURE.md` v0.4)

Streamlit demo UI -> Python service layer (consent gate, jobs, delete, audit) -> Postgres (metadata + queue) ->
NGC-PyTorch worker containers (ingest/verify, voice, animate, post), one GPU job at a time -> encrypted storage.
Primary stack: Whisper + Chatterbox (voice) + EchoMimicV3 (animation). Phases 0-5.

## 9. Status

- [x] Research, scope, pipeline, shortlist
- [x] Legal posture and product decisions (see §3)
- [x] Architecture v0.3 (`ARCHITECTURE.md`) — approved to start Phase 0
- [x] Disk freed: 20 GB -> 236 GB free (74% used) after model cleanup
- [x] GPU in Docker verified: `docker run --device nvidia.com/gpu=all nvcr.io/nvidia/pytorch:25.10-py3` (CDI; torch 2.9.0a0 nv25.10, CUDA 13.0, GB10 cc 12.1, bf16 matmul OK, flash_attn 2.7.4 importable). NGC image pulled (~18 GB).
- [x] Host ffmpeg 6.1.1 installed
- [x] Phase 0: Chatterbox multilingual runs on GB10 (zero-shot clone from Julio's 48 s sample); fi/sv/en intelligible (Whisper WER 0.00 / 0.04 / 0.00); RTF ~0.55. **Julio must still listen** to `phase0/out/tts_{en,fi,sv}.wav` for voice likeness + Finnish/Swedish accent
- [x] Phase 0: voice likeness + fi/sv accent approved by Julio (2026-10-13)
- [x] Phase 0: animation smoke test: EchoMimicV3-Flash runs on GB10 (81 frames / 3.2 s clip in ~2.5 min incl. 8 steps; output 656x880 25fps with audio). **Julio must still watch** `phase0/out/anim_en/face_768_output.mp4` for lip-sync/quality
- [ ] Phase 0: license/SBOM audit (not started) (repo itself is Apache-2.0, see `LICENSE`)
- [ ] Phases 1-5 (see ARCHITECTURE.md §11)

## 10. Next steps

1. Julio watches `phase0/out/anim_en/face_768_output.mp4` (lip-sync, identity, artefacts).
2. Longer clip + fi/sv audio through animation; measure s-of-compute per s-of-video and peak memory; try 768x768 crop vs. full portrait.
3. License/SBOM audit (Phase 0 last item).
4. Julio answers the open questions in §4 (none block Phase 0).

## 11. Changelog

- **2026-10-13 (16)** — Julio rejected segmented EchoMimic output (seams, bad head movement). Built MuseTalk pipeline (§16) on his webcam base clip with a new Spanish-accented voice clone; result `out/mt_A_final.mp4`, continuous 37.4 s. Remaining backlog (C-J) not started.

- **2026-10-13 (15)** — 384 demo finished and QC'd (see §15 A). New voice sample extracted from Julio's webcam clip (`samples/.../2026-10-13-154745 new.webm`, 47.6 s, 2048x1536 15 fps, -15.7 LUFS) -> `phase0/in/voice_video_{24k,48k}.wav` (git-ignored); not yet cloned.

- **2026-10-13 (14)** — Landscape research (similar GitHub projects) and experiment backlog A-J added as §15. Julio: try everything; wait for the running 384 render to finish before starting new GPU experiments.

- **2026-10-13 (13)** — Added `README.md` (public project overview, reproduction steps, consent policy).

- **2026-10-13 (12)** — AVATAR Hub made its own git repo (was an untracked folder inside the 7 GB `AI_Projects` repo), public on GitHub as `J-C-Serrano/AVATAR-Hub`, branch `main`; Apache-2.0 `LICENSE` added; `.gitignore` excludes samples, inputs, outputs, weights (28 GB), and the upstream `echomimic_v3` clone. Policy: update HANDOVER + commit + push every session. Also: motion study at 384 (seed and audio-guidance are the levers; text prompt and text guidance barely matter), 384x384 head-crop render `scripts/run_demo384.sh` (re-anchored to original photo, best-of-2 seeds, xfade joins) in progress.

- **2026-10-13 (11)** — Julio's requirement changes (accent preserved, natural teeth, bigger head motion, 30 s demo; see §3). Accent: 3 Chatterbox variants of a 37 s script in `phase0/out/long_en_{a_cfg0,b_cfg0_ex7,c_default}.wav` (cfg_weight 0 lowers pull toward the model's native accent; default is cfg 0.5) - **Julio to pick**. Motion/teeth: via EchoMimic text prompt + negative prompt (see `animate_test.sh` env PROMPT/NEG); head tilt/shift visibly larger than the first run. 30 s demo: chained 81-frame segments (`scripts/animate_long.sh`, last frame seeds next segment) -> `phase0/out/demo32_final.mp4`.

- **2026-10-13 (10)** — Voice approved by Julio. Animation smoke test: cloned `antgroup/echomimic_v3` (commit 7e89489) into `phase0/echomimic_v3`, built `avatar-echomimic:p0` (`phase0/docker/echomimic/`), downloaded weights (23 GB in `phase0/weights/`: EchoMimicV3 flash-pro Apache-2.0, Wan2.1-Fun-1.3B-InP Apache-2.0, chinese-wav2vec2-base MIT). First run OK: tts_en.wav + face_768.png -> `phase0/out/anim_en/face_768_output.mp4`, 81 frames, ~18 s/step at 8 steps (~2.5 min), TeaCache on. Run via `phase0/scripts/animate_test.sh <audio> <out_dir> [frames]`.

- **2026-10-13 (9)** — Samples received (`samples/Julio Serrano/`: face.jpeg, Voice.m4a 48 s; Julio's own voice/face). Built `avatar-chatterbox:p0` (NGC pytorch:25.10 + chatterbox-tts 0.1.7 `--no-deps`, constraints pin NVIDIA torch; torchaudio forced to 2.9.0 because dep resolution pulled 2.11 which fails to load). Ran Chatterbox multilingual en/fi/sv zero-shot: works, Whisper-large-v3-turbo WER 0.00/0.00/0.04, RTF 0.55 (first call 1.4 incl. warmup), model load ~57 s. Chatterbox has built-in PerTh audio watermark. Forced-EOS warnings appeared (repetition/long tail) but output was complete. Files in `phase0/` (in/, out/, scripts/, docker/chatterbox/, hf_cache/ ~3+ GB).

- **2026-10-13 (8)** — Host ffmpeg 6.1.1 installed by Julio. Phase 0 prerequisites complete; next: SadTalker + Chatterbox (fi/sv/en) smoke tests, license audit.

- **2026-10-13 (7)** — GPU-in-Docker verified via CDI (`--device nvidia.com/gpu=all`); NGC pytorch:25.10-py3 pulled; torch sees GB10 (12,1), arch list sm_80..sm_120 + compute_120 (runs via sm_120 compat). flash_attn 2.7.4 imports (kernels not yet tested on real model). Disk 218 GB free.

- **2026-10-13 (6)** — Julio-approved cleanup: removed Ollama gpt-oss:120b, qwen2.5vl:72b, qwen3.5:35b, ministral-3:14b and LM Studio gpt-oss-120b-GGUF, Qwen3.5-35B-A3B-GGUF. Disk now 236 GB free.

- **2026-10-13 (5)** — Demo/PoC simplifications: no enrollment verification, no delete keys; delete button keeps consent video. `ARCHITECTURE.md` -> v0.4. Model inventory of the Spark taken (see §12); nothing deleted yet.

- **2026-10-13 (4)** — Julio's answers folded in: remote consent/enrollment from files, anyone can render, no login (Streamlit demo), fi/en/sv, user-only deletion, no retention. `ARCHITECTURE.md` rewritten as v0.3. Env check on the Spark (aarch64, GB10 cc 12.1, driver 580, Docker 29.1.3, 119 GB RAM): disk 98% full (20 GB free), docker shows only runc runtime, ffmpeg/psql missing on host.

- **2026-10-13 (3)** — Julio's decisions recorded (in-person consent video, Ollama OK, corner AI mark, admin-only deletion, no script approval, Finland/EU, internal+external). Wrote `ARCHITECTURE.md` v0.2. Flagged Finnish TTS quality as top risk.

- **2026-10-13 (2)** — University context set: must be legal and defensible. Added legal & compliance outline (§7) and draft architecture (§8). Policy: permissive licenses only, consent-first, on-prem, disclosed/watermarked outputs.

- **2026-10-13** — Project started. Research on GB10 constraints and candidate models; chose
  2D talking-head + offline rendering; drafted pipeline and shortlist. Created `HANDOVER.md`
  (merged from original Avatar Maker md).

---

## 15. Landscape research and experiment backlog (2026-10-13)

Sources: [PunithVT/ai-avatar-system](https://github.com/PunithVT/ai-avatar-system) (MIT; Whisper->LLM->Chatterbox->MuseTalk, Celery/Redis, persistent worker, fallbacks, **no consent step**),
[InfiniteTalk](https://github.com/MeiGen-AI/InfiniteTalk) (Apache-2.0; Wan2.1-14B; streaming mode with context frames; head/body aligned to audio; video-to-video; colour shift beyond ~1 min),
[MultiTalk](https://github.com/meigen-ai/multitalk) (APG against colour error accumulation),
[EchoMimicV3 paper](https://arxiv.org/html/2507.03905v4) (windows show colour/identity inconsistency; Long Video CFG for >138 frames),
[NVIDIA forum: Wan on Spark](https://forums.developer.nvidia.com/t/image-to-video-generation-using-the-spark-vs-pc/370077) (anecdotal: 14B-class models are slow on GB10).
Caveat: speeds/VRAM are from READMEs/blogs/forums, not reproducible benchmarks; MuseTalk dependency licenses unverified.

**Own measurements (384x384 head crop, EchoMimicV3-Flash):** sampling 27 s per 81 frames (656x880: ~150 s; 512: ~53 s). Head motion is controlled by **seed** and **audio_guidance_scale**; text prompt and text guidance_scale have ~no effect (Flash is distilled); TeaCache off and audio_scale gave no gain. Chaining segments from the last frame causes colour/contrast drift (visible by ~20 s); re-anchoring each segment to the original photo avoids it.

**Backlog (all to be tried; status in checkboxes):**
- [x] A. 384 demo done (`phase0/out/demo384_final.mp4`, 32 s, 384x384, 11 segments x 2 seeds, ~50 min wall). Result: **no colour drift** (brightness 143-145, contrast 68-69, saturation 48-50 flat over 32 s, `scripts/video_qc.py`); head motion clearly larger (best seed: x 12.5% / y 13% of width/height over 3.2 s); teeth natural off-white; joins show mild jumps (frame diff up to 2.7x average at 4-frame xfades) -> improve with longer windows / overlap blending. Seeds picked: 21 for 8/11 segments. Julio must still judge lip-sync, accent, naturalness.
- [x] B. Base-video approach via **MuseTalk v1.5** (MIT) on Julio's webcam clip: works on GB10. Output `phase0/out/mt_A_final.mp4` (768x768, 25 fps, 37.4 s, one continuous take, no segment seams, real head motion). Weaknesses: webcam clip is dark/yellow, mouth patch is soft (256 px native), moustache not preserved around lips, occasional jitter. Julio must judge lip-sync, accent, naturalness. See §16.
- [ ] C. InfiniteTalk audio-only on GB10 (14B; try fp8, `--mode streaming`, 480P) as quality ceiling; record speed and drift.
- [ ] D. EchoMimic Long Video CFG with longer windows (e.g. 161+ frames) vs. 81-frame re-anchored.
- [ ] E. Persistent worker (load weights once, loop segments); ~40% of wall time is model load today.
- [ ] F. Fallbacks (TTS/animation/seed) instead of hard failure.
- [ ] G. Objective evals: SyncNet LSE-C/D (lip-sync), identity similarity (not InsightFace: licence), per-second colour drift, head-motion metric (`scripts/motion_metric.py`).
- [ ] H. Accent: compare CosyVoice2 and Chatterbox cfg_weight 0 / fine-tune on the 30-min recording (no public Chatterbox accent-fine-tune recipe found; own R&D).
- [ ] I. SBOM/licence audit incl. MuseTalk deps, InfiniteTalk, SyncNet.
- [ ] J. Remove runtime network dependency (spacy-pkuseg model fetched from GitHub on first run).

---

## Notes for any AI picking this up

- Re-verify named models/repos still exist and match the specs above; this space moves fast.
- Don't lock a final model stack before licensing is confirmed.
- Never put secrets/passwords in this file.
- After meaningful work, update §3, §4, §7-§10 and append to §11.

---

## 12. Spark model/disk inventory (2026-10-13, read-only scan; nothing deleted)

Disk: 925 GB, 859 GB used, ~20 GB free. Avatar models (TTS/animation/ASR) installed: **none**.

| Location | Size | Notes |
|---|---|---|
| `~/.lmstudio/models` | ~329 GB | 11 GGUF LLMs (Qwen3.5-122B, Nemotron-3-Super-120B, gpt-oss-120b, gemma-4-26B, etc.) |
| Ollama (`/usr/share/ollama`) | ~208 GB | 7 local models + 6 cloud stubs (cloud = no disk) |
| `~/Desktop` | ~186 GB | not models; unscanned |
| `~/AI_Projects` | ~48 GB | incl. 7 GB `.git`, several Rhizomatic copies (~5.5 GB each) |
| Docker | ~12 GB images | 96% reclaimable |
| `~/.cache` | ~6 GB | pip 3.3 GB, huggingface 1.7 GB |

Duplicates across LM Studio and Ollama: gpt-oss-120b, Qwen3.5-35B, Ministral-3-14B.

**Update after cleanup (2026-10-13):** removed the models above; kept LM Studio Ministral-3-14B, Qwen3.5-122B, Qwen3.5-27B, gpt-oss-20b, Nemotron, gemma, Mistral. Ollama still has llama4:scout (67 GB), llama3.2-vision, nomic-embed-text.

---

## 13. Phase 0 reproduction notes

- Image: `phase0/docker/chatterbox/Dockerfile` -> `docker build -t avatar-chatterbox:p0 .`
- Run flags: `--device nvidia.com/gpu=all --ipc=host --ulimit memlock=-1 --ulimit stack=67108864 --user $(id -u):$(id -g) -e HF_HOME=/hf -e HOME=/tmp`
- Scripts: `phase0/scripts/tts_test.py` (TTS en/fi/sv), `phase0/scripts/asr_check.py` (Whisper WER check).
- Gotchas: chatterbox pins torch==2.6.0 (never let pip replace NGC torch); torchaudio must be 2.9.0; spacy-pkuseg downloads a model from GitHub at first run (unneeded Chinese segmenter, but a runtime network dependency to remove/vendor); HF downloads are unauthenticated (set HF_TOKEN if rate-limited).
- To audit: licenses of resemble-perth, s3tokenizer, conformer, spacy-pkuseg, pykakasi, diffusers/transformers pins.

## 14. Phase 0 animation reproduction notes

- Image: `phase0/docker/echomimic/Dockerfile` -> `docker build -t avatar-echomimic:p0 .` (NGC 25.10 base).
- Skipped from upstream requirements: tensorflow, retina-face, mmgp (unused by `infer_flash.py`); `decord` is import-only and stubbed in `/opt/stubs` (no aarch64 wheel).
- Pins that matter: diffusers==0.35.2, transformers==4.57.1; NGC `torchao` must be uninstalled (breaks both libraries' quantizer imports). Latest diffusers/transformers (0.41/5.x) failed.
- Harmless warning: `low_cpu_mem_usage ... load_model_dict_into_meta` (diffusers version drift); weights load with 0 missing/unexpected keys.
- Weights: `phase0/weights/` (not in git; ~23 GB). Download script `phase0/scripts/hf_download.py`.
- To audit: LICENSE of Wan2.1-Fun (Apache-2.0 per HF card), echomimic_v3 repo (Apache-2.0), chinese-wav2vec2-base (MIT), imageio-ffmpeg/moviepy deps.

## 16. MuseTalk base-video pipeline (2026-10-13)

Why: Julio rejected the EchoMimic segment approach (different head position at each segment start, poor movement). The base-video approach keeps **his real head motion** and only re-syncs the mouth to the new speech.

- Upstream: `TMElyralab/MuseTalk` commit `0a89dec` cloned to `phase0/musetalk` (git-ignored). Patch: `phase0/patches/musetalk_no_mmpose.patch` (apply with `git apply`): replaces mmpose/DWPose (no aarch64 build) with `face-alignment` 68-pt landmarks, and loads the legacy resnet18 checkpoint with `weights_only=False` (file from download.pytorch.org).
- Image: `phase0/docker/musetalk/Dockerfile` -> `avatar-musetalk:p0` (NGC 25.10, diffusers 0.35.2, transformers 4.57.1, torchao and non-headless opencv removed).
- Weights: `phase0/scripts/mt_download.py` -> `phase0/weights/musetalk` (3.8 GB: MuseTalk v1.5 unet, sd-vae-ft-mse, whisper-tiny, face-parse-bisent 79999_iter.pth from Google Drive id `154JgKpz...`, resnet18). face-alignment fetches S3FD + 2DFAN4 from adrianbulat.com at first run (runtime network dependency). **Licence audit pending** for face-parse-bisent and S3FD/FAN weights.
- Base video: webcam clip 2048x1536 15 fps -> `crop=1100:1100:330:0`, scale 768, `minterpolate` to 25 fps (`phase0/in/base_768_25fps.mp4`, first 39 s).
- Run: `phase0/scripts/musetalk_run.sh <task.yaml in phase0/in> <result_dir>`; yaml has `video_path` and `audio_path` (16 kHz wav) under `task_0`.
- Voice: new reference from the webcam clip (Julio speaks English with a **Spanish accent**; he said this accent is wanted). Chatterbox clones with `scripts/tts_clone.py`: `phase0/out/clone_{vA_cfg0,vA_cfg3,vB_cfg0,vB_cfg3}.wav` (refs: 0-15 s and 20-35 s of the clip; cfg_weight 0 / 0.3). MuseTalk run used `vA_cfg0`. **Julio to choose the best-sounding variant.**

## 17. Session 2026-10-14: lip fix, grading, fi/sv

- **Julio's verdict:** MuseTalk base-video result is the right approach (continuous), but "only the lips are very bad"; voice variant `vA_cfg0` is the best of the four; a longer reference (up to 30 min) may improve the voice later (not yet provided; task H).
- **Diagnosis (frame zoom):** MuseTalk's 256 px mouth patch is smooth and hairless (no moustache/beard texture), pinker than the dark webcam face; looks pasted.
- **Fix:** GFPGAN v1.4 (Apache-2.0) face restoration as post-process (`phase0/scripts/restore_face.py`, `restore_run.sh`, image `avatar-restore:p0` from `docker/restore/Dockerfile`, weights `weights/gfpgan/GFPGANv1.4.pth`, weight 0.5, 80 % blend) + ffmpeg grade (gamma 1.3, sat 0.9, slight blue, unsharp). Lips and nose are visibly crisper and the image is brighter. Remaining limits: still somewhat plastic skin, source webcam is low quality, moustache not fully restored. ~3.5 min per 37 s on GB10.
- **Outputs (`phase0/out/`, git-ignored):** `mt_A_v2_graded30.mp4` (30 s, en), `mt_fi_v2.mp4`, `mt_sv_v2.mp4` (~20 s each; clones `clone_{fi,sv}_vA.wav`, Whisper-verified intelligible; script `scripts/tts_multi.py`, task `in/mt_task_fisv.yaml`).
- **Not done:** InfiniteTalk v2v test (large download, backlog C), accent fine-tune on 30 min (H, needs Julio's recording), licence audit of GFPGAN/facexlib deps (I): GFPGAN code Apache-2.0, facexlib MIT, basicsr Apache-2.0; weights licence to confirm.

## 18. Session 2026-10-14 (cont.): InfiniteTalk on GB10, universal progress bar

- **Julio's verdict on §17:** GFPGAN-restored MuseTalk video is "shit"; voice is fine. Test InfiniteTalk. New, better source clip: `samples/Julio Serrano/2026-10-14-090944.webm` (22.9 s, 2048x1536 15 fps, daylight office, glasses, beard). Use it for tests.
- **Progress bar rule (Julio):** every long job must show up in ONE fixed command he keeps open in a terminal:
  `cd "/home/julios/AI_Projects/AVATAR Hub" && ./phase0/scripts/progress_all.py`
  It reads `phase0/progress/*.json` (git-ignored). Register jobs with `phase0/scripts/pg.py` (`dir` = download size, `log` = tqdm regex in a log, `count`, `manual`; `rm` when done). Also lists running containers.
- **InfiniteTalk setup:** repo `MeiGen-AI/InfiniteTalk` commit `50aa0a9` in `phase0/infinitetalk` (sparse checkout without assets/examples; git-ignored), patch `phase0/patches/infinitetalk_aarch64.patch` (xfuser/xformers/quanto/decord/kokoro optional; xformers attention → SDPA; wav2vec eager attention; drop `inspect.ArgSpec`). Image `avatar-infinitetalk:p0` (`phase0/docker/infinitetalk/Dockerfile`, includes apt ffmpeg). Runner `phase0/scripts/infinitetalk_run.sh <json in phase0/in> <outname> [args]`. Weights (Apache-2.0): `weights/Wan2.1-I2V-14B-480P` (83 GB), `weights/infinitetalk/single/infinitetalk.safetensors` (10 GB), `weights/chinese-wav2vec2-base`, `weights/lightx2v/loras/Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank64.safetensors` (Apache-2.0, step+CFG distill).
- **Speed on GB10 (480 bucket, 640x640, 81-frame chunks):** model load ~9 min. Full recipe (40 steps, 3 CFG passes) ~130-145 s/step → ~1.5 h per 3 s chunk: unusable. Do NOT pass `--num_persistent_param_in_dit 0` (forces offload). With lightx2v LoRA: `--lora_scale 1.0 --sample_text_guide_scale 1.0 --sample_audio_guide_scale 2.0 --sample_steps 6 --sample_shift 2 --offload_model False` → ~86 s/step (2 passes), ~9.5 min per chunk (~2.9 s new video) ≈ 3.3 min compute per second of video.
- **Quality (`out/it_lx3.mp4`, 4 s, image→video):** far better than MuseTalk/EchoMimic: natural head motion, beard/glasses kept, mouth opens with teeth. Defect: hallucinated waving hand in first frames (image mode). Next: video→video mode on the real clip (`in/it_v2v20.json`, `in/it_src640.mp4` = crop 900x900+563+330, 25 fps, audio `in/it_a20.wav` = first 20 s of clone vA) → `out/it_v2v20.mp4`.
- **Speed-up ideas not yet tried:** 4 steps instead of 6; persistent worker (avoid 9 min reload); fp8 weights; smaller bucket; TeaCache with LoRA.

## 19. Idea 2026-10-14: stylized 3D ("Toy Story") avatar instead of video generation

**Why:** 20 h of lectures; InfiniteTalk needs ~3.5 Spark-min per second of video (5 min/lecture ≈ 17.5 h/lecture ≈ 2-3 weeks total). A rigged 3D character driven by blendshapes renders in (near) real time, never drifts, lip-syncs any language, and is editable.

**Pipeline (proposal):**
1. Character (one-time): photo → stylized concept art (permissive image model, e.g. Qwen-Image-Edit / FLUX.1-schnell, licence to verify) → image-to-3D TRELLIS.2 (MIT) → retopology (needed for facial deformation) → rig (Rigify in Blender, or UniRig MIT code) → 52 ARKit shape keys (ARKit Creator Blender add-on (open source) or paid ShapeKeyGen/Faceit). Realistic fallback: commission a 3D artist for a Pixar-style Julio with ARKit 52 (~€300-1500, assumption).
2. Voice: Chatterbox clone (existing; 20 h ≈ 11 h on Spark).
3. Face from audio → ARKit blendshape curves: NVIDIA Audio2Face-3D (SDK MIT, models NVIDIA Open Model License: commercial OK but not OSI; aarch64 unverified) or LAM Audio2Expression (Apache-2.0 badge, ARKit 52). Fallback: Rhubarb Lip Sync visemes (MIT). TalkingHead (met4citizen, MIT, three.js) has built-in Finnish/English lip-sync.
4. Body: library of idle/talk/gesture clips (Mixamo, Adobe terms) + procedural head sway, blinks, saccades. Avoid EMAGE/SMPL-X/FLAME-based models (non-commercial licences) unless licence checked.
5. Render: Blender EEVEE scripted (offline, ~0.2-0.5 s/frame est.) or three.js/TalkingHead headless capture (real time, parallel instances). Compose slides + avatar + subtitles with ffmpeg; modular segments.

**Avoid:** Hunyuan3D (licence excludes EU/UK/KR); Ready Player Me (shut down 31 Jan 2026); SMPL-X/FLAME weights (non-commercial).
**GitHub precedents:** met4citizen/TalkingHead; semperai/amica (MIT, VRM); pixiv/ChatVRM; asanchezyali/talking-avatar-with-ai (Rhubarb + RPM + R3F); HumanAIGC-Engineering/OpenAvatarChat + aigc3d/LAM (Gaussian head + Audio2Expression); 0xGF/avatar-3d (photo → Pixar-style image → TRELLIS GLB via paid Replicate APIs).
**Status:** brainstorm; awaiting Julio's decisions (style, artist budget, bust vs full body, on screen always vs clips).

## 20. Decision + proof of concept 2026-10-14: stylized 3D avatar

- **Decision (Julio):** stylized/cartoon, NOT semi-realistic: "it is an avatar we want to be obvious that is ai".
- **PoC pipeline (works end to end on the Spark):** cloned voice wav → **LAM Audio2Expression** (Apache-2.0; repo `aigc3d/LAM_Audio2Expression` commit in `phase0/poc3d/` (git-ignored), weights `weights/lam_a2e` from HF `3DAIGC/LAM_audio2exp`, patch `phase0/patches/lam_a2e_eager.patch`; runs in `avatar-chatterbox:p0` because it needs torchaudio) → ARKit-52 JSON @30 fps (`scripts/a2e_run.sh`; **37 s audio in 0.7 s**) → **Blender 4.0.2** (Ubuntu arm64 apt package in image `avatar-blender:p0`, `docker/blender/Dockerfile`; no official aarch64 Linux build) with `scripts/blender_avatar.py` / `scripts/blender_run.sh`: imports GLB, keys shape keys (mouth gain 1.4), procedural neck/head motion (smooth noise + speech-energy nods), breathing, 3-point lights, EEVEE 1080x1080 → ffmpeg mux.
- **Speed:** ~0.2 s/frame at 1080x1080 EEVEE alone (0.42 s/frame while InfiniteTalk shared the GPU). 20 h at 30 fps = 2.16 M frames ≈ 5 days at 0.2 s (less at lower res / corner overlay; parallel instances possible).
- **Test character:** `mpfb.glb` from met4citizen/TalkingHead (CC0, MakeHuman/MPFB, ARKit + Oculus visemes). Realistic, used only to test lip-sync + speed. Output `out/poc3d/poc_mpfb_37s.mp4`.
- **Note:** LAM-A2E blendshapes are tuned to FLAME topology; jawOpen subdued (max ~0.39) → gain applied. No head rotation in its output (procedural instead).
- **Next:** stylized Julio character: photo → stylized concept images (Julio picks) → TRELLIS.2 → retopo/rig/ARKit-52 (or artist) → same pipeline. Compare NVIDIA Audio2Face-3D and Rhubarb for lip quality. Add eye saccades, gestures (Mixamo-style clips), slide compositing.
- **InfiniteTalk v2v 20 s result (`out/it_v2v20.mp4`, 640x640, 25 fps):** best realistic result so far: continuous, natural head motion and hand movement from the source clip, beard/glasses kept, mouth opens with teeth. Faces a bit red/saturated. Took ~70 min (slowed while Blender shared the GPU). Render-speed benchmarks for the 3D route (150 frames, GPU shared): EEVEE 480² 0.14 s/frame, Workbench 480² 0.077 s/frame, Workbench 1080² 0.19 s/frame.

## 21. Wii-style lecture test 2026-10-14 (Julio: "go for the test")

- **Concept (Julio):** avatar does not need real lip-sync; simple mouth + head + hand gestures synchronised to the text, like a Wii character; 480x480 squares.
- **Pipeline:** cloned voice → Whisper word timestamps (`scripts/asr_words.py`, in `avatar-chatterbox:p0`) → gesture cue sheet anchored on words (`in/poc_cues.json`; in production an LLM tags the script) → `scripts/blender_wii.py` (+ `scripts/gestures.py` library: idle, wave, hand_chest, open_palms, shrug, count, point_slide; ease in/out + wiggle; volume-driven jaw + mouth-shape variation; procedural blinks, head nods from speech energy, breathing; RGBA transparent 480x480 EEVEE 16 samples) via `scripts/blender_wii_run.sh` → `scripts/compose_lecture.py` (PIL slide 1920x1080 from `in/poc_slide.json`, avatar panel bottom-right with "AI avatar" badge, ASS word-timed captions, ffmpeg).
- **Rig axes (MPFB/Mixamo names, Blender pose Euler):** Arm y- lowers arm, x- raises sideways; with arm lowered ForeArm x- lifts hand forward/up, z- crosses body; Left = mirror (y, z negated). Debug: `scripts/blender_axes.py`, `scripts/blender_gesture_preview.py`.
- **Speed:** 37 s rendered in 71 s (0.063 s/frame, ~2x faster than real time, single process). 20 h ≈ 38 h single process; LAM/A2E not needed. Voice 20 h ≈ 11 h.
- **Output:** `out/poc3d/wii_lecture_demo.mp4` (1920x1080, 37 s).
- **Next:** Julio's stylized character (photo → concept art → 3D → rig, only ~6 mouth shapes needed); LLM gesture tagging; more gestures; parallel renders; batch pipeline per lecture.

## 22. Portrait mode 2026-10-14 (Julio: "i dont need mouth moving just head synchronized melodically with the voice and just a portrait shot chest up")

- **New default look:** chest-up portrait, mouth closed (slight smile), no arm gestures; head moves with the voice's melody.
- **Pipeline:** `scripts/prosody.py` (librosa pYIN pitch in semitones vs speaker median, RMS energy, onset strength, pauses >250 ms; runs in `avatar-chatterbox:p0`) → `scripts/blender_portrait.py`: chin follows pitch contour (high-pass vs 1.5 s baseline, -2.2°/semitone, x- = chin up), stressed-syllable beats → ~300 ms nods (onset peaks with energy, ≥0.35 s apart), new turn/tilt target per phrase (eased), tilt from intonation slope, settle in pauses, blinks random + at phrase starts, brows lift on high pitch, breathing. Head bone axes: x+ nod down, x- chin up, y turn, z tilt (`scripts/blender_headaxes.py`). Compose with `scripts/compose_lecture.py`.
- **Result:** `out/poc3d/portrait_lecture_demo.mp4` (37 s): 19 phrases, 41 beats, head range about ±7°. Render 0.066 s/frame at 480x480 (37 s in 74 s).
- **Character work now simpler:** no mouth shapes needed at all; only rig (neck/head) + optional blink/brow shapes.
- **Update (Julio: 1/3 size, circle):** avatar now a 160 px circle bottom-right (orange ring, "AI avatar" badge above), rendered at 320x320 (`--res 320 --dist 0.68 --dz 0.04`, head-and-shoulders) and downscaled; `compose_lecture.py` masks it with a circle (disc + alphamerge). 0.052 s/frame at 320² → 20 h ≈ 1.3 days single process. Output `out/poc3d/portrait160_circle_demo.mp4`.
