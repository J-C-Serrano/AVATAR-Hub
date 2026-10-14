import bpy, math
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath="/in/poc_mpfb.glb")
sc = bpy.context.scene; sc.render.engine = "BLENDER_WORKBENCH"; sc.render.resolution_x = sc.render.resolution_y = 300
sc.display.shading.color_type = "TEXTURE"
arm = next(o for o in sc.objects if o.type == "ARMATURE"); pb = arm.pose.bones
cd = bpy.data.cameras.new("c"); cd.lens = 50; cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); sc.camera = cam
h = arm.matrix_world @ pb["Head"].head; cam.location = h + Vector((-0.55, -0.6, 0.0)); cam.rotation_euler = (math.radians(90), 0, math.radians(-42))
for n, e in {"x+": (25,0,0), "x-": (-25,0,0), "y+": (0,25,0), "z+": (0,0,25)}.items():
    pb["Head"].rotation_mode = "XYZ"; pb["Head"].rotation_euler = [math.radians(v) for v in e]
    sc.render.filepath = f"/out/headax/{n}.png"; bpy.ops.render.render(write_still=True)
