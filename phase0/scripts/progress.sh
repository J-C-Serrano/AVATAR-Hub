#!/bin/bash
# Live progress bar for animate_long.sh. usage: progress.sh [name=demo32] [total_segments=10]
cd "$(dirname "$0")/../out"
NAME=${1:-demo32}; TOTAL=${2:-10}; START=$(date +%s)
while true; do
  DONE=$(ls $NAME/seg_*/start_*_output.mp4 2>/dev/null | wc -l)
  # current segment's sampling step (0-8) from newest log
  LOG=$(ls -t $NAME/log_*.txt 2>/dev/null | head -1)
  STEP=$(tr '\r' '\n' < "$LOG" 2>/dev/null | grep -oE '[0-9]+/8 \[' | tail -1 | cut -d/ -f1)
  STEP=${STEP:-0}
  [ -f final_check ] || true
  if [ -f ${NAME}_final.mp4 ]; then DONE=$TOTAL; STEP=0; fi
  # a finished segment's log shows 8/8: don't double count
  if [ "$STEP" = 8 ]; then STEP=0; fi
  FRAC=$(python3 -c "print(min(1.0,($DONE+$STEP/8*0.6)/$TOTAL))")
  # ETA from first-segment-timestamps: use mtime span of finished segments
  FIRST=$(ls -tr $NAME/seg_*/start_*_output.mp4 2>/dev/null | head -1)
  LAST=$(ls -t $NAME/seg_*/start_*_output.mp4 2>/dev/null | head -1)
  ETA="--"
  if [ "$DONE" -ge 2 ] && [ -n "$FIRST" ]; then
    SPAN=$(( $(stat -c %Y "$LAST") - $(stat -c %Y "$FIRST") ))
    PER=$(( SPAN / (DONE-1) )); REM=$(( PER * (TOTAL-DONE) ))
    ETA=$(printf "%dm%02ds" $((REM/60)) $((REM%60)))
  fi
  python3 - "$FRAC" "$DONE" "$TOTAL" "$STEP" "$ETA" <<'PY'
import sys
f,d,t,s,e=float(sys.argv[1]),sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5]
n=int(40*f)
print(f"\r\033[K[{'█'*n}{'░'*(40-n)}] {f*100:3.0f}%  seg {d}/{t} done, step {s}/8  ETA {e}", end="", flush=True)
PY
  [ -f ${NAME}_final.mp4 ] && { echo; echo "DONE: out/${NAME}_final.mp4"; exit 0; }
  sleep 2
done
