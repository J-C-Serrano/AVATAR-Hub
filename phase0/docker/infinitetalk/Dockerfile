FROM nvcr.io/nvidia/pytorch:25.10-py3
# InfiniteTalk (Apache-2.0) on aarch64/sm_121; code patched via patches/infinitetalk_aarch64.patch (no xfuser/xformers/quanto).
RUN pip freeze | grep -iE '^(torch|torchvision|torchaudio|numpy)==' > /tmp/c.txt; \
    pip install --no-cache-dir -c /tmp/c.txt "diffusers==0.35.2" "transformers==4.57.1" accelerate einops easydict ftfy \
      librosa soundfile pyloudnorm "imageio[ffmpeg]" loguru scikit-image scenedetect safetensors tqdm omegaconf \
 && pip uninstall -y torchao opencv-python opencv-contrib-python; pip install --no-cache-dir --no-deps opencv-python-headless
WORKDIR /app
RUN pip install --no-cache-dir --no-deps optimum-quanto==0.2.6 && pip install --no-cache-dir -c /tmp/c.txt ninja huggingface_hub
RUN pip install --no-cache-dir --no-deps moviepy==1.0.3 proglog decorator
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
