#!/bin/bash
# usage: animate_long.sh <audio.wav in out/> <name> <seconds>   (chained 81-frame segments, 1-frame overlap)
set -e
cd "$(dirname "$0")/.."
AUDIO=$1; NAME=$2; DUR=$3
W=out/$NAME; mkdir -p $W
NSEG=$(python3 -c "import math;print(math.ceil(($DUR*25-1)/80))")
cp in/face_768.png $W/start_0.png
for ((k=0;k<NSEG;k++)); do
  [ -f $W/seg_$k/start_${k}_output.mp4 ] && { echo "seg $k exists"; } || {
    ffmpeg -v error -y -ss $(python3 -c "print($k*80/25)") -t 3.24 -i out/$AUDIO -ar 16000 -ac 1 $W/aud_$k.wav
    IMAGE=/out/$NAME/start_$k.png ./scripts/animate_test.sh /out/$NAME/aud_$k.wav /out/$NAME/seg_$k 81 > $W/log_$k.txt 2>&1
  }
  # last frame -> next start image
  ffmpeg -v error -y -sseof -0.1 -i $W/seg_$k/start_${k}_output.mp4 -update 1 -frames:v 1 $W/start_$((k+1)).png
  echo "seg $k done $(date +%T)"
done
# concat video: drop first frame of segments k>=1; take full original audio
: > $W/list.txt
for ((k=0;k<NSEG;k++)); do
  if [ $k -eq 0 ]; then S=0; else S=0.04; fi
  ffmpeg -v error -y -ss $S -i $W/seg_$k/start_${k}_output.mp4 -an -c:v libx264 -pix_fmt yuv420p -crf 16 -r 25 $W/v_$k.mp4
  echo "file v_$k.mp4" >> $W/list.txt
done
ffmpeg -v error -y -f concat -safe 0 -i $W/list.txt -c copy $W/video_only.mp4
ffmpeg -v error -y -i $W/video_only.mp4 -t $DUR -i out/$AUDIO -map 0:v -map 1:a -c:v copy -c:a aac -shortest -movflags +faststart out/${NAME}_final.mp4
echo ALL_DONE
