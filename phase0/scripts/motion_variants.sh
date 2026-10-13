#!/bin/bash
cd "$(dirname "$0")/.."
export IMAGE=/in/face_crop_384.png SIZE=384
NEG="perfectly white teeth, bright white teeth, glowing teeth, static head, frozen head, motionless, still, stiff posture, rigid neck, blurry, distorted face."
P0="A man speaking naturally and expressively to the camera, lively head movements, turning and tilting his head, nodding while he talks, shoulders moving slightly, natural slightly yellowish teeth."
P1="An animated, energetic man talking to the camera. His head moves a lot: nodding clearly, tilting side to side, turning left and right, leaning forward and back, shoulders swaying, big natural gestures of the head. Natural slightly yellowish teeth."
for v in "v0 $P0 6.0" ; do :; done
run(){ PROMPT="$2" NEG="$NEG" GS=$3 SEED=$4 ./scripts/animate_test.sh /out/long_en_a_cfg0.wav /out/mv_$1 81 > out/mv_$1.log 2>&1; }
run v0 "$P0" 6.0 43
run v1 "$P1" 6.0 43
run v2 "$P1" 8.0 43
run v3 "$P1" 6.0 7
echo MV_DONE > out/mv_done.txt
