#!/bin/bash
# job_runner.sh <queue dir>: run GPU jobs so heavy and light jobs never overlap (unified memory: InfiniteTalk ~70 GB +
# several Chatterbox workers loading together ran the 119 GB machine out of memory and froze it).
#   <queue>/light/*.sh   voice / ASR jobs, up to LIGHT_MAX at once, only while no heavy job runs
#   <queue>/heavy/*.sh   InfiniteTalk renders, one at a time, only when no light job runs and >= $HEAVY_FREE_GB is free
#   <queue>/HOLD_HEAVY   while this file exists, heavy jobs wait (e.g. until every voice job is queued)
#   <queue>/LIGHT_MAX    optional: number of parallel light jobs, re-read every loop (default $LIGHT_MAX or 3)
# A job is a bash script; its line "# expect: <path>" names the file it must produce. A job whose exit code is not 0
# or whose file is missing is retried once, then moved to failed/ (never reported as done). Logs: <queue>/log/.
# Containers in jobs should also carry a --memory cap, so a runaway job is killed alone, not the machine.
# Restarting the runner is safe: jobs still running from the previous runner are adopted (judged by their output).
Q=$(realpath "$1"); LIGHT_MAX=${LIGHT_MAX:-3}; HEAVY_FREE_GB=${HEAVY_FREE_GB:-90}; LIGHT_FREE_GB=${LIGHT_FREE_GB:-20}
mkdir -p "$Q"/{light,heavy,running,done,failed,log}
exec 9>"$Q/runner.lock"; flock -n 9 || { echo "job_runner: another runner holds $Q/runner.lock (pid $(cat "$Q/runner.pid" 2>/dev/null))" >&2; exit 1; }
echo $$ > "$Q/runner.pid"   # restart: kill "$(cat <queue>/runner.pid)", wait for it to exit, start again (jobs are adopted)
declare -A PID KIND ADOPTED
free_gb() { awk '/MemAvailable/ {print int($2/1048576)}' /proc/meminfo; }
log() { echo "$(date '+%m-%d %H:%M:%S') $*" | tee -a "$Q/runner.log"; }
kind_of() { [[ $1 == *_intro_* ]] && echo heavy || echo light; }
start() {  # start <kind> <job file>
    local b; b=$(basename "$2" .sh); mv "$Q/$1/$2" "$Q/running/$2"
    bash "$Q/running/$2" > "$Q/log/$b.log" 2>&1 9>&- & PID[$2]=$!; KIND[$2]=$1; log "start $1 $b (free $(free_gb) GB)"   # 9>&-: jobs must not hold the lock
}
finish() {  # finish <job file> <exit code>
    local j=$1 rc=$2 b exp; b=$(basename "$j" .sh); exp=$(sed -n 's/^# expect: //p' "$Q/running/$j")
    if [ "$rc" = 0 ] && { [ -z "$exp" ] || [ -s "$exp" ]; }; then mv "$Q/running/$j" "$Q/done/"; log "done $b"
    elif [[ $j != *.retry.sh ]]; then mv "$Q/running/$j" "$Q/${KIND[$j]}/${j%.sh}.retry.sh"; log "FAILED $b (exit $rc, ${exp:-no expect}) -> retry once"
    else mv "$Q/running/$j" "$Q/failed/"; log "FAILED $b again -> failed/ (exit $rc, ${exp:-no expect})"; fi
    unset "PID[$j]" "KIND[$j]" "ADOPTED[$j]"
}
for f in $(ls "$Q/running" 2>/dev/null | grep '\.sh$'); do   # jobs left by a previous runner
    p=$(pgrep -f "bash $Q/running/$f" | head -1)
    if [ -n "$p" ]; then PID[$f]=$p; KIND[$f]=$(kind_of "$f"); ADOPTED[$f]=1; log "adopted running ${KIND[$f]} ${f%.sh} (pid $p)"
    else KIND[$f]=$(kind_of "$f"); finish "$f" 0; fi             # ended while no runner watched: judged by its output
done
log "runner up: light max $LIGHT_MAX, heavy needs $HEAVY_FREE_GB GB free"
while true; do
    [ -s "$Q/LIGHT_MAX" ] && LIGHT_MAX=$(tr -dc 0-9 < "$Q/LIGHT_MAX")
    for j in "${!PID[@]}"; do
        if ! kill -0 "${PID[$j]}" 2>/dev/null; then
            if [ -n "${ADOPTED[$j]}" ]; then finish "$j" 0; else wait "${PID[$j]}"; finish "$j" $?; fi
        fi
    done
    nl=0; nh=0; for j in "${!KIND[@]}"; do [ "${KIND[$j]}" = light ] && nl=$((nl+1)); [ "${KIND[$j]}" = heavy ] && nh=$((nh+1)); done
    # watchdog: GPU allocations of the voice containers are not charged to their --memory cap, so the runner itself
    # keeps $MIN_FREE_GB free: below it, the newest light job is stopped, requeued, and one light slot is given up
    if [ "$(free_gb)" -lt "${MIN_FREE_GB:-12}" ] && [ $nl -gt 0 ]; then
        j=$(for x in "${!KIND[@]}"; do [ "${KIND[$x]}" = light ] && echo "$x"; done | sort | tail -1)
        n=$(sed -n 's/.*--name \([^ ]*\).*/\1/p' "$Q/running/$j" | head -1); [ -n "$n" ] && docker kill "$n" >/dev/null 2>&1
        kill "${PID[$j]}" 2>/dev/null; sleep 5; mv "$Q/running/$j" "$Q/light/$j"; unset "PID[$j]" "KIND[$j]" "ADOPTED[$j]"
        LIGHT_MAX=$((nl - 1 > 1 ? nl - 1 : 1)); echo $LIGHT_MAX > "$Q/LIGHT_MAX"
        log "LOW MEMORY ($(free_gb) GB free): stopped and requeued ${j%.sh}, light max now $LIGHT_MAX"; sleep 30; continue
    fi
    nextl=$(ls "$Q/light" 2>/dev/null | grep '\.sh$' | sort | head -1); nexth=$(ls "$Q/heavy" 2>/dev/null | grep '\.sh$' | sort | head -1)
    if [ $nh -eq 0 ] && ! docker ps --format "{{.Image}}" | grep -q avatar-infinitetalk && [ -n "$nextl" ] && [ $nl -lt $LIGHT_MAX ] && [ "$(free_gb)" -ge $LIGHT_FREE_GB ]; then start light "$nextl"; sleep 45; continue; fi
    if [ $nh -eq 0 ] && [ $nl -eq 0 ] && [ -z "$nextl" ] && [ -n "$nexth" ] && [ ! -e "$Q/HOLD_HEAVY" ] \
       && ! docker ps --format '{{.Image}}' | grep -qE 'avatar-(hub-app|chatterbox|tts-train|infinitetalk)'; then
        if [ "$(free_gb)" -ge $HEAVY_FREE_GB ]; then start heavy "$nexth"; else log "heavy waits: only $(free_gb) GB free"; sleep 60; fi
    fi
    sleep 10
done
