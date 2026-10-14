from huggingface_hub import HfApi
a = HfApi()
import sys
for r in sys.argv[1:]:
    try:
        info = a.model_info(r, files_metadata=True)
        print(r, "license:", info.card_data.get("license") if info.card_data else None)
        for s in info.siblings:
            print("   %8.1f MB  %s" % ((s.size or 0)/1e6, s.rfilename))
    except Exception as e:
        print(r, "ERR", type(e).__name__, str(e)[:100])
