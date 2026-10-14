#!/bin/bash
# Start the AVATAR Hub web app on http://localhost:8501 (GPU, local only). Stop: docker rm -f avatar-hub-app
cd "$(dirname "$0")/.."
HUB="$PWD"
docker rm -f avatar-hub-app >/dev/null 2>&1
docker run -d --name avatar-hub-app --device nvidia.com/gpu=all --ipc=host --user $(id -u):$(id -g) \
  -e HOME=/tmp -e USER=$(id -un) -e HF_HOME=/hub/phase0/hf_cache -e HUB_DIR=/hub -e NUMBA_CACHE_DIR=/tmp/nb -e MPLCONFIGDIR=/tmp/mpl \
  -v "$HUB:/hub" -p 127.0.0.1:8501:8501 -w /hub/app avatar-hub-app:p0 \
  streamlit run /hub/app/app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true --server.maxUploadSize 1024 >/dev/null
echo "AVATAR Hub running at http://localhost:8501   (logs: docker logs -f avatar-hub-app)"
