"""Render a talking 3D avatar in Blender from ARKit-52 blendshape JSON (LAM Audio2Expression output) + audio.
Run inside avatar-blender:p0:
  blender -b -P blender_avatar.py -- --glb avatar.glb --bs bs.json --wav speech.wav --out /out/dir
        [--start 0 --end N] [--res 1080] [--samples 32] [--mouth_gain 1.4]
Writes PNG frames to <out>/frames/; mux with ffmpeg afterwards.
Head/neck motion is procedural (speech energy + smooth noise); blinks come from the blendshape stream."""
import bpy, json, math, sys, time, wave, struct, random
import numpy as np
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
def arg(k, d=None, t=str):
    return t(a[a.index(k) + 1]) if k in a else d
GLB, BS, WAV, OUT = arg("--glb"), arg("--bs"), arg("--wav"), arg("--out")
RES, SAMPLES, GAIN = arg("--res", 1080, int), arg("--samples", 32, int), arg("--mouth_gain", 1.4, float)

d = json.load(open(BS)); names = d["names"]; fps = d["metadata"]["fps"]
W = np.array([f["weights"] for f in d["frames"]], dtype=np.float32)
N = len(W); START, END = arg("--start", 0, int), arg("--end", N - 1, int)
mouth = [i for i, n in enumerate(names) if n.startswith(("jaw", "mouth"))]
W[:, mouth] = np.clip(W[:, mouth] * GAIN, 0, 1)

# speech energy per frame from the wav (16-bit mono)
wf = wave.open(WAV); sr = wf.getframerate(); raw = wf.readframes(wf.getnframes())
x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
hop = int(sr / fps); E = np.array([np.sqrt(np.mean(x[i * hop:(i + 1) * hop] ** 2) + 1e-9) for i in range(N)])
E = E / (np.percentile(E, 95) + 1e-6); E = np.convolve(np.clip(E, 0, 1.5), np.ones(5) / 5, "same")

# --- scene ---
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
sc = bpy.context.scene; sc.render.fps = int(fps)
sc.render.engine = "BLENDER_EEVEE"; sc.eevee.taa_render_samples = SAMPLES
sc.render.resolution_x = sc.render.resolution_y = RES
vt = [v.identifier for v in sc.view_settings.bl_rna.properties["view_transform"].enum_items]
sc.view_settings.view_transform = "AgX" if "AgX" in vt else ("Filmic" if "Filmic" in vt else "Standard")
sc.eevee.use_gtao = True; sc.eevee.use_soft_shadows = True

arm = next(o for o in sc.objects if o.type == "ARMATURE")
meshes = [o for o in sc.objects if o.type == "MESH" and o.data.shape_keys]
pb = arm.pose.bones
bpy.context.view_layer.update()

# camera framing head & shoulders
head_w = arm.matrix_world @ pb["Head"].head
cam_d = bpy.data.cameras.new("cam"); cam_d.lens = 85
cam = bpy.data.objects.new("cam", cam_d); sc.collection.objects.link(cam); sc.camera = cam
target = head_w + Vector((0, 0, 0.0))
cam.location = target + Vector((0, -1.6, 0.03))
cam.rotation_euler = (math.radians(90), 0, 0)
# lights: key, fill, rim
def light(name, typ, loc, energy, size=1.0, color=(1, 1, 1)):
    l = bpy.data.lights.new(name, typ); l.energy = energy; l.color = color
    if typ == "AREA": l.size = size
    o = bpy.data.objects.new(name, l); o.location = loc; sc.collection.objects.link(o)
    o.rotation_euler = (target - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); return o
light("key", "AREA", target + Vector((-0.9, -1.0, 0.6)), 35, 1.2, (1.0, 0.96, 0.9))
light("fill", "AREA", target + Vector((1.0, -0.9, 0.1)), 12, 1.5, (0.9, 0.95, 1.0))
light("rim", "AREA", target + Vector((0.4, 0.9, 0.7)), 40, 0.8, (0.85, 0.9, 1.0))
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.32, 0.42, 0.55, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.6

# --- animation: blendshapes ---
for o in meshes:
    kb = o.data.shape_keys.key_blocks
    idx = [(names.index(k.name), k) for k in kb if k.name in names]
    for f in range(START, END + 1):
        for i, k in idx:
            k.value = float(W[f, i]); k.keyframe_insert("value", frame=f - START + 1)

# --- procedural head/neck motion: smooth noise + energy-driven nods ---
rng = np.random.default_rng(7)
def smooth_noise(n, cutoff_frames):
    k = np.hanning(cutoff_frames * 2 + 1); k /= k.sum()
    return np.convolve(rng.standard_normal(n + len(k)), k, "same")[:n]
T = N
yaw = smooth_noise(T, 45) * 0.9; pitch = smooth_noise(T, 30) * 0.6; roll = smooth_noise(T, 60) * 0.5
yaw /= np.abs(yaw).max() + 1e-6; pitch /= np.abs(pitch).max() + 1e-6; roll /= np.abs(roll).max() + 1e-6
dE = np.clip(np.diff(E, prepend=E[0]), 0, None); nod = np.convolve(dE, np.hanning(9), "same")
nod = nod / (nod.max() + 1e-6)
for bn, share in (("Neck", 0.4), ("Head", 0.6)):
    if bn not in pb: continue
    b = pb[bn]; b.rotation_mode = "XYZ"
    for f in range(START, END + 1):
        b.rotation_euler = (math.radians(share * (4.0 * pitch[f] + 5.0 * nod[f] * E[f])),
                            math.radians(share * 7.0 * yaw[f]),
                            math.radians(share * 3.0 * roll[f]))
        b.keyframe_insert("rotation_euler", frame=f - START + 1)
# subtle breathing on Spine2
if "Spine2" in pb:
    b = pb["Spine2"]; b.rotation_mode = "XYZ"
    for f in range(START, END + 1, 3):
        b.rotation_euler = (math.radians(0.8 * math.sin(2 * math.pi * f / (fps * 4.2))), 0, 0)
        b.keyframe_insert("rotation_euler", frame=f - START + 1)

sc.frame_start, sc.frame_end = 1, END - START + 1
sc.render.filepath = f"{OUT}/frames/f_"
sc.render.image_settings.file_format = "PNG"
t = time.time(); bpy.ops.render.render(animation=True)
n = END - START + 1; dt = time.time() - t
print(f"RENDER_DONE frames={n} sec={dt:.1f} per_frame={dt / n:.3f}", flush=True)
