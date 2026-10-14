FROM avatar-musetalk:p0
# GFPGAN v1.4 (Apache-2.0) face restoration for post-processing lip-synced output
RUN pip install --no-cache-dir --no-deps gfpgan facexlib basicsr lmdb yapf addict && \
    sed -i 's/from torchvision.transforms.functional_tensor import rgb_to_grayscale/from torchvision.transforms.functional import rgb_to_grayscale/' \
      "$(pip show basicsr | sed -n 's/^Location: //p')/basicsr/data/degradations.py"
