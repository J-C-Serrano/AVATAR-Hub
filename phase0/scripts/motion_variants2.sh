#!/bin/bash
cd "$(dirname "$0")/.."
export IMAGE=/in/face_crop_384.png SIZE=384
export NEG="perfectly white teeth, bright white teeth, glowing teeth, static head, frozen head, motionless, still, stiff posture, rigid neck, blurry, distorted face."
export PROMPT="An animated, energetic man talking to the camera. His head moves a lot: nodding clearly, tilting side to side, turning left and right, leaning forward and back, shoulders swaying. Natural slightly yellowish teeth."
run(){ n=$1; shift; env "$@" ./scripts/animate_test.sh /out/long_en_a_cfg0.wav /out/mv_$n 81 > out/mv_$n.log 2>&1; }
run w1 AGS=6.0 SEED=43
run w2 AS=1.6 SEED=43
run w3 TC=0.0 SEED=43
run w4 SEED=11
run w5 SEED=21
echo done > out/mv2_done.txt
