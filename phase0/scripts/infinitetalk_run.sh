#!/bin/bash
# usage: infinitetalk_run.sh <input.json in phase0/in> <out name> [extra args]   (paths inside json use /in/..)
cd "$(dirname "$0")/.."
J=$1; N=$2; shift 2
docker run --rm --device nvidia.com/gpu=all --ipc=host --user $(id -u):$(id -g) -e HOME=/tmp -e USER=julios -e LOGNAME=julios -e TORCHINDUCTOR_CACHE_DIR=/tmp/ind -e MPLCONFIGDIR=/tmp/mpl \
  -v "$PWD/infinitetalk:/app" -v "$PWD/weights:/w:ro" -v "$PWD/in:/in:ro" -v "$PWD/out:/out" -w /app \
  avatar-infinitetalk:p0 python generate_infinitetalk.py \
    --ckpt_dir /w/Wan2.1-I2V-14B-480P --wav2vec_dir /w/chinese-wav2vec2-base \
    --infinitetalk_dir /w/infinitetalk/single/infinitetalk.safetensors \
    --input_json /in/$J --size infinitetalk-480 --sample_steps 40 --mode streaming \
    --motion_frame 9 --save_file /out/$N --audio_save_dir /tmp/audio "$@"
