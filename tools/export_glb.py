import bpy, os, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLEND = os.path.join(REPO, "source", "hagia_sophia_hill_v2.blend")
bpy.ops.wm.open_mainfile(filepath=BLEND)

# Convert curves to meshes (window frames, stair rails) so they export.
bpy.ops.object.select_all(action='DESELECT')
for o in list(bpy.data.objects):
    if o.type == 'CURVE':
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
if bpy.context.selected_objects:
    bpy.ops.object.convert(target='MESH')

# Remove the sea; Three.js gets its own water.
for name in ("Sea", "SeaFar"):
    o = bpy.data.objects.get(name)
    if o:
        bpy.data.objects.remove(o, do_unlink=True)

# Simple PBR materials keyed by original name.
colors = {
    "Stone_Limestone": ("#b08a5e", 0.86, 0.0, None, 0),
    "Stone_Trim": ("#d8c49f", 0.72, 0.0, None, 0),
    "Stone_Dark": ("#6d5a45", 0.9, 0.0, None, 0),
    "Marble": ("#e3d8c2", 0.45, 0.0, None, 0),
    "Marble_Red": ("#7a2d2a", 0.35, 0.0, None, 0),
    "Marble_Green": ("#2f5a42", 0.35, 0.0, None, 0),
    "Lead_Roof": ("#67727a", 0.42, 0.55, None, 0),
    "Lead_Ribs": ("#8b959b", 0.38, 0.5, None, 0),
    "Gold": ("#e0a63a", 0.25, 1.0, None, 0),
    "Iron": ("#2a2c2e", 0.5, 0.7, None, 0),
    "BoatWood": ("#4a2c18", 0.7, 0.0, None, 0),
    "Cypress": ("#1e3a26", 0.95, 0.0, None, 0),
    "Trunk": ("#3a2a1c", 0.95, 0.0, None, 0),
    "CityStone": ("#2f3236", 0.95, 0.0, None, 0),
    "Hills": ("#2a3340", 0.95, 0.0, None, 0),
    "RoofTile": ("#6f3024", 0.8, 0.0, None, 0),
    "Hillside": ("#526b39", 0.95, 0.0, None, 0),
    "Window_Warm": ("#120700", 0.4, 0.0, "#ff9a45", 3.0),
    "Window_Amber": ("#120800", 0.4, 0.0, "#ffb15e", 2.4),
    "Window_Dim": ("#0d0700", 0.4, 0.0, "#ff8a38", 1.2),
    "Window_Dark": ("#0b1118", 0.2, 0.2, None, 0),
    "LampGlow": ("#120700", 0.3, 0.0, "#ffd08a", 5.0),
    "PortalDoor": ("#2a1a10", 0.45, 0.0, None, 0),
    "Brass": ("#b8862e", 0.3, 1.0, None, 0),
    "Moon": ("#ffffff", 1.0, 0.0, None, 0),
}
cache = {}
def simple_mat(name):
    if name in cache:
        return cache[name]
    col, rough, metal, emit, estr = colors.get(name, ("#9a8a76", 0.8, 0.0, None, 0))
    m = bpy.data.materials.new("S_" + name)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    def hexrgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16)/255.0 for i in (0, 2, 4))
    c = hexrgb(col)
    p.inputs["Base Color"].default_value = (*c, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if emit:
        e = hexrgb(emit)
        p.inputs["Emission Color"].default_value = (*e, 1)
        p.inputs["Emission Strength"].default_value = estr
    cache[name] = m
    return m

# Replace each mesh's material slots by a simple material with a stable name.
for o in bpy.data.objects:
    if o.type != 'MESH' or not o.data.materials:
        continue
    for i, mat in enumerate(o.data.materials):
        if mat is None:
            continue
        o.data.materials[i] = simple_mat(mat.name)

# Select only meshes for export.
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:
    if o.type == 'MESH' and o.name not in ("Sea", "SeaFar"):
        o.select_set(True)
bpy.context.view_layer.objects.active = next(iter(bpy.context.selected_objects), None)

out = os.path.join(REPO, "public", "assets", "hagia_sophia.glb")
os.makedirs(os.path.dirname(out), exist_ok=True)
t = time.time()
bpy.ops.export_scene.gltf(
    filepath=out,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
    export_cameras=False,
    export_lights=False,
    export_materials='EXPORT',
    export_texcoords=True,
    export_normals=True,
    export_tangents=False,
    export_yup=True,
)
print("EXPORTED", out, round(time.time()-t, 1), "s", os.path.getsize(out)/1e6, "MB")
