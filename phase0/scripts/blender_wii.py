"""Wii-style avatar render: simple volume-driven mouth, script-cued arm gestures, procedural head/blinks.
Run inside avatar-blender:p0:
  blender -b -P blender_wii.py -- --glb a.glb --wav speech.wav --words words.json --cues cues.json --out /out/dir
        [--res 480] [--fps 30] [--engine BLENDER_EEVEE] [--samples 16]
words.json: [{"w","t0","t1"}] (scripts/asr_words.py); cues.json: [{"word","gesture","hold"}] in script order.
Writes RGBA PNG frames (transparent background) to <out>/frames/ for compositing over slides."""
import bpy, json, math, sys, time, wave, re
import numpy as np
from mathutils import Vector
sys.path.insert(0, "/s"); import gestures as G

a = sys.argv[sys.argv.index("--") + 1:]
def arg(k, d=None, t=str):
    return t(a[a.index(k) + 1]) if k in a else d
GLB, WAV, WORDS, CUES, OUT = arg("--glb"), arg("--wav"), arg("--words"), arg("--cues"), arg("--out")
RES, FPS, ENGINE, SAMPLES = arg("--res", 480, int), arg("--fps", 30, int), arg("--engine", "BLENDER_EEVEE"), arg("--samples", 16, int)

# --- audio energy per frame ---
wf = wave.open(WAV); sr = wf.getframerate()
x = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768
N = int(len(x) / sr * FPS); hop = sr / FPS
E = np.array([np.sqrt(np.mean(x[int(i * hop):int((i + 1) * hop)] ** 2) + 1e-9) for i in range(N)])
E = np.clip(E / (np.percentile(E, 90) + 1e-6), 0, 1.3)
Es = np.convolve(E, np.ones(3) / 3, "same")

# --- gesture timeline from cues anchored on words ---
words = json.load(open(WORDS)); cues = json.load(open(CUES))
norm = lambda s: re.sub(r"[^a-z]", "", s.lower())
timeline, wi = [], 0
for c in cues:
    while wi < len(words) and norm(words[wi]["w"]) != norm(c["word"]): wi += 1
    if wi == len(words): print("CUE NOT FOUND", c["word"]); wi = 0; continue
    t = max(0.0, words[wi]["t0"] - 0.25)  # gesture stroke slightly leads the word
    timeline.append((t, t + c["hold"], c["gesture"])); wi += 1
print("TIMELINE", [(round(s, 2), g) for s, e, g in timeline])
RAMP_IN, RAMP_OUT = 0.35, 0.5
def ease(u): return 0.5 - 0.5 * math.cos(math.pi * min(max(u, 0), 1))

def arm_pose(t):
    """Blend idle with active gesture(s) at time t -> {bone: euler deg}."""
    idle = G.pose(None); out = dict(idle); w_best, g_best = 0, None
    for s, e, g in timeline:
        if s - 0.01 <= t <= e + RAMP_OUT:
            w = ease((t - s) / RAMP_IN) if t < s + RAMP_IN else (1 - ease((t - e) / RAMP_OUT) if t > e else 1)
            if w > w_best: w_best, g_best = w, g
    if g_best:
        gp = G.pose(g_best)
        out = {b: tuple((1 - w_best) * idle[b][i] + w_best * gp[b][i] for i in range(3)) for b in idle}
        if g_best in G.WIGGLE:
            side, bone, ax, amp, hz = G.WIGGLE[g_best]
            bn = ("Right" if side == "R" else "Left") + bone
            e = list(out[bn]); e[ax] += w_best * amp * math.sin(2 * math.pi * hz * t); out[bn] = tuple(e)
    return out

# --- scene ---
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
sc = bpy.context.scene; sc.render.fps = FPS
sc.render.engine = ENGINE; sc.eevee.taa_render_samples = SAMPLES
sc.render.resolution_x = sc.render.resolution_y = RES
sc.render.film_transparent = True
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
vt = [v.identifier for v in sc.view_settings.bl_rna.properties["view_transform"].enum_items]
sc.view_settings.view_transform = "AgX" if "AgX" in vt else "Standard"
arm = next(o for o in sc.objects if o.type == "ARMATURE"); pb = arm.pose.bones
for b in pb: b.rotation_mode = "XYZ"
meshes = [o for o in sc.objects if o.type == "MESH" and o.data.shape_keys]

head_w = arm.matrix_world @ pb["Head"].head
cd = bpy.data.cameras.new("cam"); cd.lens = 50
cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam); sc.camera = cam
target = head_w + Vector((0, 0, -0.24)); cam.location = target + Vector((0, -1.85, 0.08))
cam.rotation_euler = (math.radians(88), 0, 0)
def light(name, loc, energy, size, color):
    l = bpy.data.lights.new(name, "AREA"); l.energy = energy; l.color = color; l.size = size
    o = bpy.data.objects.new(name, l); o.location = loc; sc.collection.objects.link(o)
    o.rotation_euler = (target - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
light("key", target + Vector((-1.0, -1.3, 0.8)), 60, 1.5, (1.0, 0.96, 0.9))
light("fill", target + Vector((1.2, -1.1, 0.2)), 22, 2.0, (0.9, 0.95, 1.0))
light("rim", target + Vector((0.5, 1.0, 0.9)), 60, 1.0, (0.85, 0.9, 1.0))
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.55, 0.62, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.5

# --- keys ---
rng = np.random.default_rng(3)
blinks = set()
t = 1.0
while t < N / FPS:
    f0 = int(t * FPS); blinks.update({f0: 0.6, f0 + 1: 1.0, f0 + 2: 1.0, f0 + 3: 0.5}.items()); t += rng.uniform(2.5, 5.0)
blink = dict(blinks)
def smooth_noise(n, c):
    k = np.hanning(2 * c + 1); k /= k.sum(); v = np.convolve(rng.standard_normal(n + len(k)), k, "same")[:n]
    return v / (np.abs(v).max() + 1e-6)
yaw, pitch, roll = smooth_noise(N, 40), smooth_noise(N, 28), smooth_noise(N, 55)
dE = np.clip(np.diff(Es, prepend=Es[0]), 0, None); nod = np.convolve(dE, np.hanning(9), "same"); nod /= nod.max() + 1e-6
alt = smooth_noise(N, 4)  # mouth shape variation

for f in range(N):
    fr = f + 1; t = f / FPS
    jaw = float(np.clip(0.55 * Es[f], 0, 0.6)); shape = alt[f]
    sk = {"jawOpen": jaw, "mouthFunnel": max(0, shape) * 0.5 * jaw / 0.6, "mouthStretchLeft": max(0, -shape) * 0.3 * jaw / 0.6,
          "mouthStretchRight": max(0, -shape) * 0.3 * jaw / 0.6, "mouthClose": 0.0,
          "eyeBlinkLeft": blink.get(f, 0.0), "eyeBlinkRight": blink.get(f, 0.0),
          "mouthSmileLeft": 0.25, "mouthSmileRight": 0.25, "browInnerUp": 0.25 * float(nod[f])}
    for o in meshes:
        kb = o.data.shape_keys.key_blocks
        for k, v in sk.items():
            if k in kb: kb[k].value = v; kb[k].keyframe_insert("value", frame=fr)
    for bn, e in arm_pose(t).items():
        if bn in pb: pb[bn].rotation_euler = [math.radians(v) for v in e]; pb[bn].keyframe_insert("rotation_euler", frame=fr)
    for bn, share in (("Neck", 0.4), ("Head", 0.6)):
        pb[bn].rotation_euler = (math.radians(share * (4 * pitch[f] + 6 * nod[f] * Es[f])), math.radians(share * 8 * yaw[f]), math.radians(share * 3 * roll[f]))
        pb[bn].keyframe_insert("rotation_euler", frame=fr)
    pb["Spine2"].rotation_euler = (math.radians(0.8 * math.sin(2 * math.pi * t / 4.2)), math.radians(1.5 * yaw[f]), 0)
    pb["Spine2"].keyframe_insert("rotation_euler", frame=fr)

sc.frame_start, sc.frame_end = 1, N
sc.render.filepath = f"{OUT}/frames/f_"
t0 = time.time(); bpy.ops.render.render(animation=True)
print(f"RENDER_DONE frames={N} sec={time.time() - t0:.1f} per_frame={(time.time() - t0) / N:.3f}", flush=True)
