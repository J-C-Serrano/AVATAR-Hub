FROM nvcr.io/nvidia/pytorch:25.10-py3
COPY constraints.txt /tmp/constraints.txt
# chatterbox pins torch==2.6.0; install it without deps so NVIDIA's sm_121-capable torch is kept
RUN pip install --no-cache-dir --no-deps chatterbox-tts==0.1.7 \
 && pip install --no-cache-dir -c /tmp/constraints.txt \
      s3tokenizer "transformers==5.2.0" "diffusers==0.29.0" resemble-perth conformer==0.3.2 \
      pykakasi==2.3.0 spacy-pkuseg pyloudnorm omegaconf "librosa==0.11.0" \
 && python -c "import torch;print('torch kept:',torch.__version__)"
# torchaudio must match torch 2.9 (dep resolution pulled 2.11, which fails to load)
RUN pip install --no-cache-dir --no-deps --force-reinstall torchaudio==2.9.0 && python -c "import torchaudio, perth; print('torchaudio', torchaudio.__version__, 'perth ok')"
RUN apt-get update -qq && apt-get install -y -qq ffmpeg libsndfile1 >/dev/null && rm -rf /var/lib/apt/lists/*
