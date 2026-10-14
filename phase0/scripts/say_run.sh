#!/bin/bash
# usage: say_run.sh "<text>" <out name (.wav) under out/messages> [say.py args]   -- fine-tuned Julio voice
cd "$(dirname "$0")/.."
T=$1; O=$2; shift 2
docker run --rm --device nvidia.com/gpu=all --ipc=host --user $(id -u):$(id -g) -e HOME=/tmp -e HF_HOME=/hf -e NUMBA_CACHE_DIR=/tmp/nb \
  -v "$PWD/hf_cache:/hf" -v "$PWD/scripts:/s:ro" -v "$PWD/../samples/Julio Serrano/voices:/v:ro" -v "$PWD/out/ft:/ft:ro" -v "$PWD/out/messages:/out" \
  avatar-tts-train:p0 python /s/say.py --text "$T" --out /out/$O "$@"
