# Debug: render arm-bone rotations about local X/Y/Z to learn rig axes
import bpy, math, sys
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath="/in/poc_mpfb.glb")
sc = bpy.context.scene; sc.render.engine = "BLENDER_WORKBENCH"; sc.render.resolution_x = sc.render.resolution_y = 400
arm = next(o for o in sc.objects if o.type == "ARMATURE"); pb = arm.pose.bones
print("BONES", [b.name for b in pb if "Arm" in b.name or "Shoulder" in b.name or "Hand" == b.name[-4:]])
for n in ("RightArm","RightForeArm","RightShoulder"):
    b = arm.data.bones[n]; print(n, "head", tuple(round(v,3) for v in b.head_local), "tail", tuple(round(v,3) for v in b.tail_local))
cd = bpy.data.cameras.new("c"); cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); sc.camera = cam
h = arm.matrix_world @ pb["Head"].head; cam.location = h + Vector((0, -3.2, -0.5)); cam.rotation_euler = (math.radians(90), 0, 0)
cam.location = h + Vector((-1.6, -2.4, -0.4)); cam.rotation_euler = (math.radians(90), 0, math.radians(-33))
def reset():
    for b in pb: b.rotation_mode = "XYZ"; b.rotation_euler = (0, 0, 0)
tests = {"L_y+": {"LeftArm": (0, 55, 0)}, "L_y-": {"LeftArm": (0, -55, 0)}}
for ax in range(3):
    for sgn in (1, -1):
        e = [0, 0, 0]; e[ax] = sgn * 75
        tests[f"Rfore_{'xyz'[ax]}{'+' if sgn>0 else '-'}"] = {"RightArm": (0, -55, 0), "RightForeArm": tuple(e)}
for k, t in tests.items():
    reset()
    for bn, e in t.items(): pb[bn].rotation_euler = [math.radians(v) for v in e]
    sc.render.filepath = f"/out/axes2/{k}.png"; bpy.ops.render.render(write_still=True)
