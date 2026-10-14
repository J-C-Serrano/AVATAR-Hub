#!/bin/bash
# LAM Audio2Expression: wav (path under phase0/in) -> ARKit-52 blendshape JSON at 30 fps
# usage: a2e_run.sh <wav in phase0/in> <out json name under out/poc3d>
cd "$(dirname "$0")/.."
docker run --rm --device nvidia.com/gpu=all --user $(id -u):$(id -g) -e HOME=/tmp -e USER=julios -e HF_HOME=/tmp/hf \
  -v "$PWD/poc3d/LAM_Audio2Expression:/app" -v "$PWD/weights/lam_a2e/pretrained_models:/app/pretrained_models:ro" \
  -v "$PWD/in:/in:ro" -v "$PWD/out/poc3d:/out" -w /app avatar-chatterbox:p0 bash -c '
  pip install -q --user addict yapf termcolor omegaconf 2>/dev/null
  python inference.py --config-file configs/lam_audio2exp_config_streaming.py --options save_path=/tmp/exp \
    weight=pretrained_models/lam_audio2exp_streaming.tar audio_input=/in/'"$1"' save_json_path=/out/'"$2"
