#!/bin/bash
# waits for demo32 render, then times 81 frames at 512 and 384 on a tight head+shoulders crop
cd "$(dirname "$0")/.."
while [ ! -f out/demo32_final.mp4 ]; do sleep 20; done
python3 - <<'PY'
from PIL import Image
im = Image.open("in/face_768.png"); W,H = im.size
side = int(0.86*W); x0 = int(0.07*W); y0 = int(0.17*H)
c = im.crop((x0, y0, x0+side, y0+side))
for s in (512, 384): c.resize((s,s), Image.LANCZOS).save(f"in/face_crop_{s}.png")
print("source", W, H, "crop", side)
PY
export PROMPT="A man speaking naturally and expressively to the camera, lively head movements, turning and tilting his head, nodding while he talks, shoulders moving slightly, natural slightly yellowish teeth."
export NEG="perfectly white teeth, bright white teeth, glowing teeth, static head, frozen head, motionless, stiff posture, blurry, distorted face."
for S in 512 384; do
  t0=$(date +%s)
  IMAGE=/in/face_crop_$S.png SIZE=$S ./scripts/animate_test.sh /out/long_en_a_cfg0.wav /out/res_$S 81 > out/res_$S.log 2>&1
  echo "$S: total wall $(( $(date +%s) - t0 ))s | $(tr '\r' '\n' < out/res_$S.log | grep -oE '8/8 \[[^]]*\]' | tail -1)" | tee -a out/res_summary.txt
done
echo RES_DONE >> out/res_summary.txt
