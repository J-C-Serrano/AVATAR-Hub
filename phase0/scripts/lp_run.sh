#!/bin/bash
# usage: lp_run.sh <img in in/> <prosody json in in/> <out dir under out/> [extra args]  (env PS/YS/RS = axis signs)
cd "$(dirname "$0")/.."
I=$1; P=$2; O=$3; shift 3; mkdir -p out/$O
docker run --rm --device nvidia.com/gpu=all --user $(id -u):$(id -g) -e HOME=/tmp -e TORCH_HOME=/tmp/torch -e PS=${PS:-1} -e YS=${YS:-1} -e RS=${RS:-1} \
  -v "$PWD/poc3d/liveportrait:/lp:ro" -v "$PWD/weights/liveportrait/liveportrait:/w/liveportrait:ro" -v "$PWD/scripts:/s:ro" -v "$PWD/in:/in:ro" -v "$PWD/out:/out" \
  avatar-liveportrait:p0 python /s/lp_head.py --img /in/$I --prosody /in/$P --out /out/$O "$@"
