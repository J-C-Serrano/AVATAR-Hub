#!/bin/bash
# usage: blender_wii_run.sh <glb in in/> <wav in in/> <words json in in/> <cues json in in/> <out dir under out/poc3d> [extra]
cd "$(dirname "$0")/.."
G=$1; A=$2; W=$3; C=$4; O=$5; shift 5
docker run --rm --device nvidia.com/gpu=all --user $(id -u):$(id -g) -e HOME=/tmp \
  -v "$PWD/scripts:/s:ro" -v "$PWD/in:/in:ro" -v "$PWD/out/poc3d:/out" avatar-blender:p0 \
  blender -b -noaudio -P /s/blender_wii.py -- --glb /in/$G --wav /in/$A --words /in/$W --cues /in/$C --out /out/$O "$@"
