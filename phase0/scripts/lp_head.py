"""Photo avatar: one still of the person, head re-posed per frame by prosody-driven motion (LivePortrait, MIT).
No mouth animation (lips kept closed), blinks via eye retargeting. InsightFace is NOT used: the one-time crop
uses face-alignment 68-pt landmarks; LivePortrait's own landmark.onnx gives the 203 points for eye ratios.
usage (inside container, LivePortrait repo at /lp):
  python lp_head.py --img /in/src.png --prosody /in/p.json --out /out/dir [--amp 1.0] [--debug]
Writes /out/dir/frames/f_%04d.png (512x512)."""
import argparse, json, os, sys
import numpy as np, cv2, torch
sys.path.insert(0, "/lp"); sys.path.insert(0, "/s")
import head_motion as HM
from src.config.inference_config import InferenceConfig
from src.live_portrait_wrapper import LivePortraitWrapper
from src.utils.camera import get_rotation_matrix
from src.utils.crop import crop_image
from src.utils.human_landmark_runner import LandmarkRunner
from src.utils.retargeting_utils import calc_eye_close_ratio

ap = argparse.ArgumentParser()
ap.add_argument("--img"); ap.add_argument("--prosody"); ap.add_argument("--out")
ap.add_argument("--amp", type=float, default=1.0); ap.add_argument("--debug", action="store_true")
ap.add_argument("--loop", type=float, default=0, help="seconds: render a seamless idle loop instead of prosody-driven motion")
ap.add_argument("--fps", type=int, default=30); ap.add_argument("--seed", type=int, default=5)
ap.add_argument("--scale", type=float, default=2.6); ap.add_argument("--eye_open", type=float, default=0.0)
A = ap.parse_args()
W = "/w/liveportrait"
cfg = InferenceConfig(checkpoint_F=f"{W}/base_models/appearance_feature_extractor.pth", checkpoint_M=f"{W}/base_models/motion_extractor.pth",
                      checkpoint_G=f"{W}/base_models/spade_generator.pth", checkpoint_W=f"{W}/base_models/warping_module.pth",
                      checkpoint_S=f"{W}/retargeting_models/stitching_retargeting_module.pth")
lpw = LivePortraitWrapper(cfg)

# --- one-time source crop (face-alignment 68 pts -> LivePortrait crop) ---
img = cv2.cvtColor(cv2.imread(A.img), cv2.COLOR_BGR2RGB)
import face_alignment
fa = face_alignment.FaceAlignment(face_alignment.LandmarksType.TWO_D, device="cuda")
lmk68 = fa.get_landmarks(img)[0]
crop = crop_image(img, lmk68, dsize=512, scale=A.scale, vy_ratio=-0.10)
src = crop["img_crop"]
lr = LandmarkRunner(ckpt_path=f"{W}/landmark.onnx", onnx_provider="cpu")
lmk_c = crop_image(img, lmk68, dsize=512, scale=A.scale, vy_ratio=-0.10)["pt_crop"]
lmk203 = lr.run(src, lmk_c)
cv2.imwrite(os.path.join(A.out, "source_crop.png"), cv2.cvtColor(src, cv2.COLOR_RGB2BGR))

with torch.no_grad():
    I_s = lpw.prepare_source(src)
    x_s_info = lpw.get_kp_info(I_s)
    f_s = lpw.extract_feature_3d(I_s)
    x_s = lpw.transform_keypoint(x_s_info)
    R_s = get_rotation_matrix(x_s_info["pitch"], x_s_info["yaw"], x_s_info["roll"])
    eye0 = float(calc_eye_close_ratio(lmk203[None]).mean())
    print(f"source pose pitch={float(x_s_info['pitch']):.1f} yaw={float(x_s_info['yaw']):.1f} roll={float(x_s_info['roll']):.1f} eye_ratio={eye0:.3f}")

    def render(dp, dy, dr, blink):
        R_d = get_rotation_matrix(x_s_info["pitch"] + dp, x_s_info["yaw"] + dy, x_s_info["roll"] + dr)
        R_new = (R_d @ R_s.permute(0, 2, 1)) @ R_s
        x_d = x_s_info["scale"] * (x_s_info["kp"] @ R_new + x_s_info["exp"]) + x_s_info["t"]
        if blink > 0.02:
            target = eye0 * (1 - blink) + 0.0 * blink
            ratio = lpw.calc_combined_eye_ratio([[target]], lmk203)
            x_d = x_d + lpw.retarget_eye(x_s, ratio)
        x_d = lpw.stitching(x_s, x_d)
        out = lpw.warp_decode(f_s, x_s, x_d)
        return lpw.parse_output(out["out"])[0]

    os.makedirs(os.path.join(A.out, "frames"), exist_ok=True)
    if A.debug:
        for name, args in {"p+": (12, 0, 0, 0), "p-": (-12, 0, 0, 0), "y+": (0, 12, 0, 0), "r+": (0, 0, 10, 0), "blink": (0, 0, 0, 1)}.items():
            cv2.imwrite(os.path.join(A.out, f"dbg_{name}.png"), cv2.cvtColor(render(*args), cv2.COLOR_RGB2BGR))
        sys.exit()
    M = HM.loop(A.loop, A.fps, A.amp, A.seed) if A.loop > 0 else HM.compute(json.load(open(A.prosody)), A.amp)
    # head_motion pitch: + = nod down. LivePortrait sign mapped by PITCH_SIGN (set after debug check)
    PITCH_SIGN, YAW_SIGN, ROLL_SIGN = float(os.environ.get("PS", 1)), float(os.environ.get("YS", 1)), float(os.environ.get("RS", 1))
    import time; t0 = time.time()
    for f in range(M["n"]):
        fr = render(PITCH_SIGN * M["pitch"][f], YAW_SIGN * M["yaw"][f], ROLL_SIGN * M["roll"][f], float(M["blink"][f]))
        cv2.imwrite(os.path.join(A.out, "frames", f"f_{f + 1:04d}.png"), cv2.cvtColor(fr, cv2.COLOR_RGB2BGR))
        if f % 100 == 0: print(f"{f}/{M['n']} [", flush=True)
    print(f"RENDER_DONE frames={M['n']} sec={time.time() - t0:.1f} per_frame={(time.time() - t0) / M['n']:.3f}")
