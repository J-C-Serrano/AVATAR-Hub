#!/bin/bash
# usage: animate_test.sh <audio.wav> <out_dir> [video_length]
set -e
P=/home/julios/AI_Projects/AVATAR\ Hub/phase0
AUDIO=$1; OUT=$2; LEN=${3:-81}
docker run --rm --device nvidia.com/gpu=all --ipc=host --ulimit memlock=-1 --ulimit stack=67108864 \
  --user $(id -u):$(id -g) -e HOME=/tmp -e HF_HOME=/tmp/hf \
  -v "$P/echomimic_v3:/app" -v "$P/weights:/w:ro" -v "$P/in:/in:ro" -v "$P/out:/out" -w /app \
  avatar-echomimic:p0 python infer_flash.py \
    --image_path "${IMAGE:-/in/face_768.png}" --audio_path "$AUDIO" \
    --prompt "${PROMPT:-A person is speaking.}" --num_inference_steps 8 --config_path config/config.yaml \
    --model_name /w/Wan2.1-Fun-V1.1-1.3B-InP \
    --ckpt_idx 50000 --transformer_path /w/echomimicv3/echomimicv3-flash-pro/diffusion_pytorch_model.safetensors \
    --save_path "$OUT" --wav2vec_model_dir /w/chinese-wav2vec2-base \
    --sampler_name Flow_Unipc --video_length $LEN --guidance_scale ${GS:-6.0} --audio_guidance_scale ${AGS:-3.0} \
    --audio_scale ${AS:-1.0} --neg_scale 1.0 --neg_steps 0 --seed ${SEED:-43} --enable_teacache --teacache_threshold ${TC:-0.1} \
    --num_skip_start_steps 5 --riflex_k 6 --ulysses_degree 1 --ring_degree 1 --weight_dtype bfloat16 \
    --sample_size ${SIZE:-768} ${SIZE:-768} --fps 25 --add_prompt "" --negative_prompt "${NEG:-}" --shift 5.0
