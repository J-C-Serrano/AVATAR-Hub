#!/bin/bash
# usage: blender_run.sh <glb in phase0/in> <bs json in out/poc3d> <wav in phase0/in> <out dir name under out/poc3d> [extra args]
cd "$(dirname "$0")/.."
G=$1; B=$2; A=$3; O=$4; shift 4
docker run --rm --device nvidia.com/gpu=all --user $(id -u):$(id -g) -e HOME=/tmp \
  -v "$PWD/scripts:/s:ro" -v "$PWD/in:/in:ro" -v "$PWD/out/poc3d:/out" avatar-blender:p0 \
  blender -b -noaudio -P /s/blender_avatar.py -- --glb /in/$G --bs /out/$B --wav /in/$A --out /out/$O "$@"
