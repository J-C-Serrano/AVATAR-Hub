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
sys.path.insert(0, "/s"); import head_motion as HM
M = HM.compute(P, AMP); N = M["n"]
hx, hy, hz, blink, melody, lean, starts = M["pitch"], M["yaw"], M["roll"], M["blink"], M["melody"], M["lean"], M["starts"]

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
DIST = arg("--dist", 0.98, float); target = head_w + Vector((0, 0, arg("--dz", 0.0, float))); cam.location = target + Vector((0, -DIST, 0.03))
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
print(f"PHRASES={len(starts)} BEATS={M["beats"]} head_x=({hx.min():.1f},{hx.max():.1f}) head_y=({hy.min():.1f},{hy.max():.1f})", flush=True)
t0 = time.time(); bpy.ops.render.render(animation=True)
print(f"RENDER_DONE frames={N} sec={time.time() - t0:.1f} per_frame={(time.time() - t0) / N:.3f}", flush=True)
