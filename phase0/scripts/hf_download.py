from huggingface_hub import snapshot_download
snapshot_download("BadToBest/EchoMimicV3", local_dir="/w/echomimicv3", allow_patterns=["echomimicv3-flash-pro/*"])
snapshot_download("alibaba-pai/Wan2.1-Fun-V1.1-1.3B-InP", local_dir="/w/Wan2.1-Fun-V1.1-1.3B-InP")
snapshot_download("TencentGameMate/chinese-wav2vec2-base", local_dir="/w/chinese-wav2vec2-base", ignore_patterns=["*fairseq*"])
print("DOWNLOAD_DONE")
