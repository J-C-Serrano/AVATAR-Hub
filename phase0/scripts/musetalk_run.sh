#!/bin/bash
# usage: musetalk_run.sh <task.yaml in phase0/in> <result_dir name> [extra args]
cd "$(dirname "$0")/.."
Y=$1; R=$2; shift 2
docker run --rm --device nvidia.com/gpu=all --ipc=host --user $(id -u):$(id -g) -e HOME=/tmp -e TORCH_HOME=/tmp/torch -e MPLCONFIGDIR=/tmp/mpl \
  -v "$PWD/musetalk:/app" -v "$PWD/weights/musetalk:/app/models:ro" -v "$PWD/in:/in:ro" -v "$PWD/out:/out" -w /app \
  avatar-musetalk:p0 bash -c '
    mkdir -p /tmp/ff && ln -sf "$(python -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")" /tmp/ff/ffmpeg && export PATH=/tmp/ff:$PATH
    python -m scripts.inference --inference_config /in/'"$Y"' --result_dir /out/'"$R"' \
      --unet_model_path models/musetalkV15/unet.pth --unet_config models/musetalkV15/musetalk.json \
      --whisper_dir models/whisper --version v15 --ffmpeg_path /tmp/ff --use_float16 '"$*"'
  '
