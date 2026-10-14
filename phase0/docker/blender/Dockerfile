FROM ubuntu:24.04
# Blender from Ubuntu arm64 archive (no official aarch64 Linux build); headless EEVEE via NVIDIA EGL
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends blender python3-numpy ffmpeg libegl1 libgl1 libglvnd0 && rm -rf /var/lib/apt/lists/*
ENV NVIDIA_DRIVER_CAPABILITIES=all
