from huggingface_hub import HfApi
a = HfApi()
for r in ["BadToBest/EchoMimicV3", "alibaba-pai/Wan2.1-Fun-V1.1-1.3B-InP", "TencentGameMate/chinese-wav2vec2-base"]:
    try:
        info = a.model_info(r, files_metadata=True)
        print(r, "license:", info.card_data.get("license") if info.card_data else None)
        for s in info.siblings:
            print("   %8.1f MB  %s" % ((s.size or 0)/1e6, s.rfilename))
    except Exception as e:
        print(r, "ERR", type(e).__name__, str(e)[:100])
