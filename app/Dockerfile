FROM avatar-tts-train:p0
# AVATAR Hub Streamlit front end (voice tool). Chatterbox multilingual + LoRA, Whisper QC, ffmpeg.
RUN pip freeze | grep -iE '^(torch|torchaudio|numpy|transformers)==' > /tmp/c.txt; pip install --no-cache-dir -c /tmp/c.txt "streamlit==1.65.0" 2>&1 | tail -1
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
WORKDIR /app
