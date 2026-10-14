from huggingface_hub import snapshot_download
snapshot_download("MeiGen-AI/InfiniteTalk", allow_patterns=["single/*"], local_dir="weights/infinitetalk")
snapshot_download("Wan-AI/Wan2.1-I2V-14B-480P", ignore_patterns=["assets/*","examples/*","*.md"], local_dir="weights/Wan2.1-I2V-14B-480P")
print("IT_DL_DONE")
