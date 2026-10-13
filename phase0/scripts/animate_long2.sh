#!/bin/bash
# Re-anchored long render: every 81-frame segment starts from the ORIGINAL image (no drift),
# segments advance 77 frames and overlap 4 frames, cross-faded with xfade.
# usage: animate_long2.sh <audio.wav in out/> <name> <seconds> <image in in/> <size>
# env: PROMPT NEG GS SEED
set -e
cd "$(dirname "$0")/.."; PWD=$(pwd)
AUDIO=$1; NAME=$2; DUR=$3; IMG=$4; SIZE=$5
W=out/$NAME; mkdir -p $W
STEP=3.08; SEG=3.24; OV=0.16
NSEG=$(python3 -c "import math;print(math.ceil(($DUR-$SEG)/$STEP)+1)")
for ((k=0;k<NSEG;k++)); do
  OUTF=$W/seg_$k/${IMG%.png}_output.mp4
  if [ ! -f $OUTF ]; then
    ffmpeg -v error -y -ss $(python3 -c "print(round($k*$STEP,3))") -t $SEG -i out/$AUDIO -ar 16000 -ac 1 $W/aud_$k.wav
    : > $W/log_$k.txt
    CANDS=""
    for sd in ${SEEDS:-21 43}; do
      C=$W/seg_$k/cand_$sd; [ -f $C/${IMG%.png}_output.mp4 ] || SEED=$sd IMAGE=/in/$IMG SIZE=$SIZE ./scripts/animate_test.sh /out/$NAME/aud_$k.wav /out/$NAME/seg_$k/cand_$sd 81 >> $W/log_$k.txt 2>&1
      CANDS="$CANDS /out/$NAME/seg_$k/cand_$sd/${IMG%.png}_output.mp4"
    done
    BEST=$(docker run --rm -v "$PWD/out:/out:ro" -v "$PWD/scripts:/s:ro" --user $(id -u):$(id -g) avatar-echomimic:p0 python /s/motion_metric.py --pick $CANDS 2>/dev/null | tail -1)
    cp "$PWD/${BEST#/}" $OUTF
    echo "seg $k picked $BEST"
  fi
  echo "seg $k done $(date +%T)"
done
# build xfade chain
INPUTS=""; FILT=""; PREV="[0:v]"; ACC=0
for ((k=0;k<NSEG;k++)); do INPUTS="$INPUTS -i $W/seg_$k/${IMG%.png}_output.mp4"; done
for ((k=1;k<NSEG;k++)); do
  OFF=$(python3 -c "print(round($k*$STEP,3))")
  FILT="$FILT${PREV}[$k:v]xfade=transition=fade:duration=$OV:offset=$OFF[x$k];"; PREV="[x$k]"
done
ffmpeg -v error -y $INPUTS -filter_complex "${FILT%;}" -map "$PREV" -an -c:v libx264 -pix_fmt yuv420p -crf 16 -r 25 $W/video_only.mp4
ffmpeg -v error -y -i $W/video_only.mp4 -i out/$AUDIO -t $DUR -map 0:v -map 1:a -c:v copy -c:a aac -movflags +faststart out/${NAME}_final.mp4
echo ALL_DONE
