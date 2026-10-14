import os, subprocess
from huggingface_hub import snapshot_download, hf_hub_download
R="/w/musetalk"
snapshot_download("TMElyralab/MuseTalk", local_dir=R, allow_patterns=["musetalkV15/*"])
snapshot_download("stabilityai/sd-vae-ft-mse", local_dir=R+"/sd-vae", allow_patterns=["config.json","diffusion_pytorch_model.bin"])
snapshot_download("openai/whisper-tiny", local_dir=R+"/whisper", allow_patterns=["config.json","pytorch_model.bin","preprocessor_config.json"])
os.makedirs(R+"/face-parse-bisent", exist_ok=True)
subprocess.run(["curl","-fsSL","https://download.pytorch.org/models/resnet18-5c106cde.pth","-o",R+"/face-parse-bisent/resnet18-5c106cde.pth"], check=False)
try:
    import gdown
    gdown.download(id="154JgKpzCPW82qINcVieuPH3fZ2e0P812", output=R+"/face-parse-bisent/79999_iter.pth", quiet=True)
except Exception as e:
    print("gdown failed", e)
print(subprocess.run(["bash","-c",f"find {R} -type f | xargs ls -la | awk '{{print $5, $9}}'"],capture_output=True,text=True).stdout)
