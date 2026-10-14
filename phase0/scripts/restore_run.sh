#!/bin/bash
# usage: restore_run.sh <in.mp4 under out/> <out.mp4 under out/> [weight] [strength]
cd "$(dirname "$0")/.."
docker run --rm --device nvidia.com/gpu=all --user $(id -u):$(id -g) -e HOME=/tmp -v "$PWD/weights/gfpgan:/w" -v "$PWD/scripts:/s:ro" -v "$PWD/out:/out" \
  avatar-restore:p0 python /s/restore_face.py /out/$1 /out/$2 ${3:-0.5} ${4:-0.8}
