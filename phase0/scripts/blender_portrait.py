"""Portrait (chest-up) avatar render: closed mouth, head moving with the melody of the voice.
Run inside avatar-blender:p0:
  blender -b -P blender_portrait.py -- --glb a.glb --prosody p.json --out /out/dir [--res 480] [--samples 16] [--amp 1.0]
prosody.json from scripts/prosody.py (per-frame f0 in semitones, energy, onset, pause).
Mapping (Head bone, Blender Euler deg; x+ = nod down, x- = chin up, y = turn, z = tilt):
  pitch contour  -> chin up/down (higher pitch, chin slightly up)
  stressed syllables (onset peaks) -> short downward nod "beat"
  phrase starts (after pauses) -> new gaze/turn target, eased; slow tilt with intonation slope
  pauses -> settle toward neutral + blink."""
import bpy, json, math, sys, time
import numpy as np
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
def arg(k, d=None, t=str):
    return t(a[a.index(k) + 1]) if k in a else d
GLB, PROS, OUT = arg("--glb"), arg("--prosody"), arg("--out")
RES, SAMPLES, AMP = arg("--res", 480, int), arg("--samples", 16, int), arg("--amp", 1.0, float)
P = json.load(open(PROS)); FPS = int(P["fps"])
st = np.clip(np.array(P["f0_st"]), -6, 6); E = np.array(P["energy"]); ON = np.array(P["onset"]); PZ = np.array(P["pause"])
N = len(st); rng = np.random.default_rng(11)

def lp(x, sec):  # zero-phase smoothing (two-pass exponential)
    k = 1 - math.exp(-1 / (sec * FPS)); y = np.copy(x).astype(float)
    for seq in (range(1, len(y)), range(len(y) - 2, -1, -1)):
        for i in seq: y[i] = y[i - 1 if seq.start < seq.stop else i + 1] * (1 - k) + y[i] * k
    return y

# 1) melody: chin follows smoothed pitch (relative to a slow baseline so declination doesn't tilt the head forever)
melody = lp(st, 0.18) - lp(st, 1.5)
chin = -2.2 * melody                                   # deg, x- = chin up when pitch rises
# 2) beats: nods on stressed syllables (onset peaks with energy, min spacing 0.35 s)
beat = np.zeros(N); last = -99
for i in range(1, N - 1):
    if ON[i] > 0.45 and ON[i] >= ON[i - 1] and ON[i] >= ON[i + 1] and E[i] > 0.3 and i - last > 0.35 * FPS:
        beat[i] = ON[i] * min(E[i], 1.0); last = i
kern = np.array([math.sin(math.pi * j / 9) for j in range(10)])   # ~300 ms down-and-back
nod = np.convolve(beat, kern, "full")[:N] * 3.2      # deg, x+ = down
# 3) phrases: new turn/tilt target at each phrase start
starts = [0] + [i for i in range(1, N) if PZ[i - 1] > 0 and PZ[i] == 0]
yaw_t, roll_t = np.zeros(N), np.zeros(N); cur_y = 0
for j, s in enumerate(starts):
    e = starts[j + 1] if j + 1 < len(starts) else N
    cur_y = float(np.clip(-cur_y * 0.5 + rng.uniform(-6, 6), -7, 7))   # alternate sides, natural spread
    yaw_t[s:e] = cur_y; roll_t[s:e] = rng.uniform(-2.5, 2.5)
yaw = lp(yaw_t, 0.45); roll = lp(roll_t, 0.6) + 1.5 * lp(np.gradient(lp(st, 0.3)), 0.3) * FPS / 10
# 4) energy: slight lean-in when emphatic; pauses settle
lean = 1.5 * lp(E, 0.5); settle = 1 - 0.6 * lp(PZ, 0.3)
micro = lp(rng.standard_normal(N), 0.8) * 0.6          # tiny life noise
hx = AMP * (settle * (chin + nod) + micro + lean * 0.5)
hy = AMP * (yaw + micro * 0.8); hz = AMP * (roll * settle)
# blinks: random 2.5-5 s plus at phrase starts
blink = np.zeros(N); t = rng.uniform(0.5, 2)
bl = [int(t * FPS)]
while t < N / FPS: t += rng.uniform(2.5, 5.0); bl.append(int(t * FPS))
bl += [s + 2 for s in starts[1:]]
for f0 in bl:
    for d_, v in enumerate((0.6, 1.0, 1.0, 0.5)):
        if 0 <= f0 + d_ < N: blink[f0 + d_] = max(blink[f0 + d_], v)

# --- scene ---
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
sc = bpy.context.scene; sc.render.fps = FPS
sc.render.engine = "BLENDER_EEVEE"; sc.eevee.taa_render_samples = SAMPLES
sc.render.resolution_x = sc.render.resolution_y = RES
sc.render.film_transparent = True
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
vt = [v.identifier for v in sc.view_settings.bl_rna.properties["view_transform"].enum_items]
sc.view_settings.view_transform = "AgX" if "AgX" in vt else "Standard"
arm = next(o for o in sc.objects if o.type == "ARMATURE"); pb = arm.pose.bones
for b in pb: b.rotation_mode = "XYZ"
for side, s in (("Right", 1), ("Left", -1)):           # arms down (outside frame anyway)
    pb[side + "Arm"].rotation_euler = (math.radians(6), math.radians(-66 * s), 0)
    pb[side + "ForeArm"].rotation_euler = (math.radians(-18), 0, 0)
meshes = [o for o in sc.objects if o.type == "MESH" and o.data.shape_keys]

head_w = arm.matrix_world @ pb["Head"].head
cd = bpy.data.cameras.new("cam"); cd.lens = 50
cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam); sc.camera = cam
target = head_w + Vector((0, 0, 0.0)); cam.location = target + Vector((0, -0.98, 0.03))
cam.rotation_euler = (math.radians(88), 0, 0)
def light(name, loc, energy, size, color):
    l = bpy.data.lights.new(name, "AREA"); l.energy = energy; l.color = color; l.size = size
    o = bpy.data.objects.new(name, l); o.location = loc; sc.collection.objects.link(o)
    o.rotation_euler = (target - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
light("key", target + Vector((-0.8, -1.0, 0.6)), 30, 1.2, (1.0, 0.96, 0.9))
light("fill", target + Vector((0.9, -0.9, 0.1)), 11, 1.5, (0.9, 0.95, 1.0))
light("rim", target + Vector((0.4, 0.8, 0.6)), 35, 0.8, (0.85, 0.9, 1.0))
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.55, 0.62, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.5

for f in range(N):
    fr = f + 1
    sk = {"eyeBlinkLeft": blink[f], "eyeBlinkRight": blink[f], "mouthSmileLeft": 0.18, "mouthSmileRight": 0.18,
          "mouthClose": 0.0, "browInnerUp": float(np.clip(0.35 * max(melody[f], 0) / 3, 0, 0.35)),
          "browOuterUpLeft": float(np.clip(0.15 * max(melody[f], 0) / 3, 0, 0.2)), "browOuterUpRight": float(np.clip(0.15 * max(melody[f], 0) / 3, 0, 0.2))}
    for o in meshes:
        kb = o.data.shape_keys.key_blocks
        for k, v in sk.items():
            if k in kb: kb[k].value = float(v); kb[k].keyframe_insert("value", frame=fr)
    for bn, share in (("Neck", 0.35), ("Head", 0.65)):
        pb[bn].rotation_euler = (math.radians(share * hx[f]), math.radians(share * hy[f]), math.radians(share * hz[f]))
        pb[bn].keyframe_insert("rotation_euler", frame=fr)
    pb["Spine2"].rotation_euler = (math.radians(0.8 * math.sin(2 * math.pi * f / FPS / 4.2) + 0.3 * lean[f]), math.radians(0.2 * hy[f]), 0)
    pb["Spine2"].keyframe_insert("rotation_euler", frame=fr)

sc.frame_start, sc.frame_end = 1, N
sc.render.filepath = f"{OUT}/frames/f_"
print(f"PHRASES={len(starts)} BEATS={int((beat > 0).sum())} head_x=({hx.min():.1f},{hx.max():.1f}) head_y=({hy.min():.1f},{hy.max():.1f})", flush=True)
t0 = time.time(); bpy.ops.render.render(animation=True)
print(f"RENDER_DONE frames={N} sec={time.time() - t0:.1f} per_frame={(time.time() - t0) / N:.3f}", flush=True)
