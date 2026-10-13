#!/bin/bash
cd "$(dirname "$0")/.."
export PROMPT="An animated, energetic man talking to the camera. His head moves a lot: nodding clearly, tilting side to side, turning left and right, leaning forward and back, shoulders swaying. Natural slightly yellowish teeth."
export NEG="perfectly white teeth, bright white teeth, glowing teeth, static head, frozen head, motionless, still, stiff posture, rigid neck, blurry, distorted face."
export AGS=6.0 SEEDS="21 43"
exec ./scripts/animate_long2.sh demo_audio_32s.wav demo384 32 face_crop_384.png 384
