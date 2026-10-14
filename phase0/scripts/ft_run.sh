#!/bin/bash
# usage: ft_run.sh <run name under out/ft> [ft_t3_lora.py args]   (dataset: samples/Julio Serrano/voices/dataset)
cd "$(dirname "$0")/.."
R=$1; shift; mkdir -p out/ft/$R
docker run --rm --device nvidia.com/gpu=all --ipc=host --user $(id -u):$(id -g) -e HOME=/tmp -e HF_HOME=/hf -e NUMBA_CACHE_DIR=/tmp/nb \
  -v "$PWD/hf_cache:/hf" -v "$PWD/scripts:/s:ro" -v "$PWD/../samples/Julio Serrano/voices:/v:ro" -v "$PWD/out/ft:/out" \
  avatar-tts-train:p0 python /s/ft_t3_lora.py --data /v/dataset --out /out/$R "$@"
