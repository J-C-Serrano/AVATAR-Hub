FROM nvcr.io/nvidia/pytorch:25.10-py3
# MuseTalk on aarch64/sm_121: no mmcv/mmpose (landmarks via face-alignment, see patches/musetalk_no_mmpose.patch).
RUN pip freeze | grep -iE '^(torch|torchvision|torchaudio|numpy)==' > /tmp/c.txt; \
    pip install --no-cache-dir -c /tmp/c.txt "diffusers==0.35.2" "transformers==4.57.1" accelerate omegaconf einops \
      librosa soundfile opencv-python-headless "imageio[ffmpeg]" ffmpeg-python moviepy face-alignment huggingface_hub gdown \
 && pip uninstall -y torchao opencv-python opencv-contrib-python && pip install --no-cache-dir --force-reinstall --no-deps opencv-python-headless
ENV PYTHONPATH=/app:/app/musetalk/utils
