import bpy, math, sys
sys.path.insert(0, "/s"); import gestures as G
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath="/in/poc_mpfb.glb")
sc = bpy.context.scene; sc.render.engine = "BLENDER_WORKBENCH"; sc.render.resolution_x = sc.render.resolution_y = 400
sc.display.shading.color_type = "TEXTURE"
arm = next(o for o in sc.objects if o.type == "ARMATURE"); pb = arm.pose.bones
cd = bpy.data.cameras.new("c"); cd.lens = 50; cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); sc.camera = cam
h = arm.matrix_world @ pb["Head"].head; t = h + Vector((0, 0, -0.32)); cam.location = t + Vector((0, -2.3, 0.05)); cam.rotation_euler = (math.radians(90), 0, 0)
for name in [None] + list(G.GESTURES):
    for b in pb: b.rotation_mode = "XYZ"; b.rotation_euler = (0, 0, 0)
    for bn, e in G.pose(name).items(): pb[bn].rotation_euler = [math.radians(v) for v in e]
    sc.render.filepath = f"/out/gest/{name or 'idle'}.png"; bpy.ops.render.render(write_still=True)
