FROM nvcr.io/nvidia/pytorch:25.10-py3
# Never let pip replace NGC torch. tensorflow/retina-face/mmgp/decord skipped (unused by infer_flash.py; decord has no aarch64 wheel).
RUN pip freeze | grep -iE '^(torch|torchvision|torchaudio|numpy)==' > /tmp/c.txt; \
    pip install --no-cache-dir -c /tmp/c.txt einops safetensors timm torchdiffeq torchsde scikit-image \
      omegaconf SentencePiece ftfy func_timeout accelerate "diffusers==0.35.2" "transformers==4.57.1" \
      "moviepy==2.2.1" librosa pyloudnorm "imageio[ffmpeg]" huggingface_hub opencv-python-headless \
 && mkdir -p /opt/stubs/decord && echo "# stub: unused by infer_flash.py" > /opt/stubs/decord/__init__.py
ENV PYTHONPATH=/opt/stubs
# NGC torchao is out of sync with diffusers/transformers quantizer imports; unused here.
RUN pip uninstall -y torchao
