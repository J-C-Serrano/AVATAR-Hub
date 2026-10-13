# AVATAR Hub

Self-hosted **talking-head video avatar** generator: ~10 photos + ~30 min of audio of a person
become a **cloned voice** and an **offline, lip-synced video** of that person speaking any script.
Think HeyGen / Synthesia / D-ID, but open-source and running on hardware you own.

> **Status: proof of concept (Phase 0).** Voice cloning and lip-sync animation both run on the
> target machine. Not production software. See [`HANDOVER.md`](HANDOVER.md) for the live status.

## How it works

```
photos ──► best frame / head crop ──► source portrait ──┐
30 min audio ──► voice-clone model ──► TTS (fi / en / sv) ──► speech.wav ──┴─► talking-head model ──► lip-synced video
```

| Stage | Model | License |
|---|---|---|
| Voice clone + TTS (fi/en/sv) | [Chatterbox multilingual](https://github.com/resemble-ai/chatterbox) | MIT |
| ASR check (WER) | Whisper large-v3-turbo | MIT |
| Lip-sync animation | [EchoMimicV3-Flash](https://github.com/antgroup/echomimic_v3) on Wan2.1-Fun-1.3B | Apache-2.0 |
| Audio encoder | chinese-wav2vec2-base | MIT |

Only permissively licensed components are used. Chatterbox outputs carry a built-in PerTh watermark.

## Target hardware

NVIDIA **DGX Spark / GB10** (ARM64, Blackwell sm_121, 128 GB unified memory, ~273 GB/s).
Everything runs inside NVIDIA's NGC PyTorch container (`nvcr.io/nvidia/pytorch:25.10-py3`),
because plain pip PyTorch does not support sm_121. Generation is offline/batch, not real-time.

Measured so far (81 frames ≈ 3.2 s of video, 8 sampling steps):

| Output size | Sampling time |
|---|---|
| 656×880 | ~150 s |
| 512×512 | ~53 s |
| 384×384 | ~27 s |

## Reproduce Phase 0

Requires Docker with the NVIDIA container toolkit (CDI) and about 60 GB of free disk.

```bash
# 1. Voice: build the image and run zero-shot TTS (see HANDOVER.md §13)
docker build -t avatar-chatterbox:p0 phase0/docker/chatterbox

# 2. Animation: clone upstream at the pinned commit, build, download weights
git clone https://github.com/antgroup/echomimic_v3 phase0/echomimic_v3
git -C phase0/echomimic_v3 checkout 7e89489
docker build -t avatar-echomimic:p0 phase0/docker/echomimic
mkdir -p phase0/weights && docker run --rm -v "$PWD/phase0/weights:/w" -v "$PWD/phase0/scripts:/s:ro" \
  --user $(id -u):$(id -g) -e HOME=/tmp avatar-echomimic:p0 python /s/hf_download.py

# 3. Put your own inputs in phase0/in/ (face_768.png, voice_24k.wav), then:
./phase0/scripts/animate_test.sh /out/your_speech.wav /out/my_clip 81
```

Inputs, outputs, weights and caches are git-ignored. Details and gotchas (pinned library
versions, aarch64 workarounds) are in [`HANDOVER.md`](HANDOVER.md) §13–§14.

## Repository layout

| Path | Contents |
|---|---|
| `HANDOVER.md` | Source of truth: decisions, status, next steps, changelog. **Read first.** |
| `ARCHITECTURE.md` | Demo-first system design (UI, service layer, workers, compliance) |
| `phase0/docker/` | Dockerfiles for the Chatterbox and EchoMimic images |
| `phase0/scripts/` | TTS, animation, long-render, progress and motion-measurement scripts |

## Consent and responsible use

This tool clones a real person's face and voice. Design rules (details in `ARCHITECTURE.md`):

- **Consent first:** enrollment requires a recorded consent phrase, stored with the avatar.
- **Disclosure:** outputs carry an "AI" mark and invisible watermark/C2PA metadata.
- **Deletion:** the subject can delete their avatar and data.
- Context: a university in Finland/EU (GDPR, EU AI Act). This is not legal advice; production
  use needs counsel/DPO review. Do not use it to impersonate anyone without their consent.

## License

[Apache-2.0](LICENSE) for this repository's code. Model weights and upstream projects keep
their own licenses (see the table above).
