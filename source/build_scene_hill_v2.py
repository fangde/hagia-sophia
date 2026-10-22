"""
Hagia Sophia by the sea - procedural Blender scene (Blender 5.2, Cycles).
No external assets: geometry, materials, sky and lighting are all scripted.

Run:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
      --python build_scene.py
"""

import bpy
import bmesh
import os
import math
import random
from mathutils import Vector, Matrix

# ----------------------------------------------------------------------------
# constants (metres)
# ----------------------------------------------------------------------------
BASE_Z = 2.0
LOW_W, LOW_D, LOW_H = 76.0, 64.0, 22.0
UP_W, UP_D = 68.0, 56.0
ATTIC = 44.0
ROOF_Z = BASE_Z + LOW_H + 9.0                   # 33
DRUM_R = 19.0
DRUM_BOT, DRUM_TOP = 35.0, 47.0
DOME_ZS = 0.82
DOME_TOP = DRUM_TOP + DRUM_R * DOME_ZS          # 63.56
SEA_Z = -14.0
WATER_Y = -92.0
CREST_Y = -44.0
STAIR_LAMPS = []
HOUSE_LIGHTS = []
QUAY_Z = 2.0
FRONT_Y = -LOW_D / 2.0                          # -32

random.seed(7)
HERE = os.path.dirname(os.path.abspath(__file__))
RENDERS = os.path.join(HERE, "renders")

# ----------------------------------------------------------------------------
# reset
# ----------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"


def make_coll(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c


C_BUILD = make_coll("HagiaSophia")
C_DETAIL = make_coll("Details")
C_ENV = make_coll("SeaAndShore")
C_CITY = make_coll("City")
C_LIGHT = make_coll("Lighting")
C_CAM = make_coll("Cameras")

# ----------------------------------------------------------------------------
# materials
# ----------------------------------------------------------------------------

def _principled(mat):
    return mat.node_tree.nodes.get("Principled BSDF")


def _set(node, name, value):
    sock = node.inputs.get(name)
    if sock is not None:
        sock.default_value = value


def mat_plain(name, color, rough=0.6, metal=0.0, emit=None, emit_strength=0.0,
              spec=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = _principled(m)
    _set(p, "Base Color", (*color, 1.0))
    _set(p, "Roughness", rough)
    _set(p, "Metallic", metal)
    _set(p, "Specular IOR Level", spec)
    if emit:
        _set(p, "Emission Color", (*emit, 1.0))
        _set(p, "Emission Strength", emit_strength)
    m.diffuse_color = (*color, 1.0)
    return m


def mat_stone(name, c1, c2, rough=0.82, bump=0.28, scale=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = _principled(m)
    _set(p, "Roughness", rough)
    _set(p, "Specular IOR Level", 0.35)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.20 * scale,) * 3
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.2
    noise.inputs["Detail"].default_value = 9.0
    noise.inputs["Roughness"].default_value = 0.62
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[0].color = (*c1, 1)
    ramp.color_ramp.elements[1].position = 0.72
    ramp.color_ramp.elements[1].color = (*c2, 1)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])

    fine = nt.nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 32.0
    fine.inputs["Detail"].default_value = 6.0
    fine.inputs["Roughness"].default_value = 0.7
    bmp = nt.nodes.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = bump
    bmp.inputs["Distance"].default_value = 0.18
    nt.links.new(mp.outputs["Vector"], fine.inputs["Vector"])
    nt.links.new(fine.outputs["Fac"], bmp.inputs["Height"])
    nt.links.new(bmp.outputs["Normal"], p.inputs["Normal"])
    m.diffuse_color = (*c2, 1)
    return m


def mat_ashlar(name, c1, c2, mortar, rough=0.84, bw=1.6, rh=0.62):
    """Large limestone ashlar blocks + grunge, for wall surfaces."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = _principled(m)
    _set(p, "Roughness", rough)
    _set(p, "Specular IOR Level", 0.32)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    # normal-aware planar projection so courses stay horizontal on all walls
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    nsep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], nsep.inputs["Vector"])
    ax = nt.nodes.new("ShaderNodeMath"); ax.operation = "ABSOLUTE"
    ay = nt.nodes.new("ShaderNodeMath"); ay.operation = "ABSOLUTE"
    nt.links.new(nsep.outputs["X"], ax.inputs[0])
    nt.links.new(nsep.outputs["Y"], ay.inputs[0])
    gt = nt.nodes.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"
    nt.links.new(ax.outputs[0], gt.inputs[0])
    nt.links.new(ay.outputs[0], gt.inputs[1])
    psep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], psep.inputs["Vector"])
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "FLOAT"
    nt.links.new(gt.outputs[0], mx.inputs[0])
    nt.links.new(psep.outputs["X"], mx.inputs[2])
    nt.links.new(psep.outputs["Y"], mx.inputs[3])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(mx.outputs[0], comb.inputs["X"])
    nt.links.new(psep.outputs["Z"], comb.inputs["Y"])
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.offset = 0.5
    brick.offset_frequency = 2
    _set(brick, "Color1", (*c1, 1))
    _set(brick, "Color2", (*c2, 1))
    _set(brick, "Mortar", (*mortar, 1))
    _set(brick, "Scale", 1.0)
    _set(brick, "Mortar Size", 0.022)
    _set(brick, "Mortar Smooth", 0.12)
    _set(brick, "Bias", 0.0)
    _set(brick, "Brick Width", bw)
    _set(brick, "Row Height", rh)
    nt.links.new(comb.outputs["Vector"], brick.inputs["Vector"])

    noise = nt.nodes.new("ShaderNodeTexNoise")
    _set(noise, "Scale", 0.55)
    _set(noise, "Detail", 8.0)
    _set(noise, "Roughness", 0.68)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.28
    ramp.color_ramp.elements[0].color = (*c1, 1)
    ramp.color_ramp.elements[1].position = 0.74
    ramp.color_ramp.elements[1].color = (*c2, 1)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 0.42
    nt.links.new(brick.outputs["Color"], mix.inputs[6])
    nt.links.new(ramp.outputs["Color"], mix.inputs[7])
    nt.links.new(mix.outputs[2], p.inputs["Base Color"])

    fine = nt.nodes.new("ShaderNodeTexNoise")
    _set(fine, "Scale", 18.0)
    _set(fine, "Detail", 7.0)
    _set(fine, "Roughness", 0.72)
    nt.links.new(tc.outputs["Object"], fine.inputs["Vector"])
    bmp1 = nt.nodes.new("ShaderNodeBump")
    bmp1.inputs["Strength"].default_value = 0.35
    bmp1.inputs["Distance"].default_value = 0.10
    nt.links.new(fine.outputs["Fac"], bmp1.inputs["Height"])
    bmp2 = nt.nodes.new("ShaderNodeBump")
    bmp2.inputs["Strength"].default_value = 0.45
    bmp2.inputs["Distance"].default_value = 0.06
    nt.links.new(brick.outputs["Factor"], bmp2.inputs["Height"])
    nt.links.new(bmp1.outputs["Normal"], bmp2.inputs["Normal"])
    nt.links.new(bmp2.outputs["Normal"], p.inputs["Normal"])
    m.diffuse_color = (*c2, 1)
    return m


def mat_grass(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = _principled(m)
    _set(p, "Roughness", 0.95)
    _set(p, "Specular IOR Level", 0.2)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    _set(n1, "Scale", 0.22)
    _set(n1, "Detail", 10.0)
    _set(n1, "Roughness", 0.75)
    nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[0].color = (0.018, 0.030, 0.012, 1)
    ramp.color_ramp.elements[1].position = 0.78
    ramp.color_ramp.elements[1].color = (0.085, 0.110, 0.040, 1)
    mid = ramp.color_ramp.elements.new(0.52)
    mid.color = (0.045, 0.060, 0.022, 1)
    nt.links.new(n1.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])
    fine = nt.nodes.new("ShaderNodeTexNoise")
    _set(fine, "Scale", 2.5)
    _set(fine, "Detail", 8.0)
    _set(fine, "Roughness", 0.8)
    nt.links.new(tc.outputs["Object"], fine.inputs["Vector"])
    bmp = nt.nodes.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = 0.85
    bmp.inputs["Distance"].default_value = 0.25
    nt.links.new(fine.outputs["Fac"], bmp.inputs["Height"])
    nt.links.new(bmp.outputs["Normal"], p.inputs["Normal"])
    m.diffuse_color = (0.05, 0.08, 0.03, 1)
    return m


def mat_tile(name, c1, c2):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = _principled(m)
    _set(p, "Roughness", 0.78)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    w = nt.nodes.new("ShaderNodeTexWave")
    try:
        w.wave_type = "BANDS"
        w.bands_direction = "Y"
    except Exception:
        pass
    _set(w, "Scale", 1.7)
    _set(w, "Distortion", 1.0)
    _set(w, "Detail", 2.0)
    _set(w, "Detail Scale", 1.0)
    nt.links.new(tc.outputs["Object"], w.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*c1, 1)
    ramp.color_ramp.elements[1].color = (*c2, 1)
    nt.links.new(w.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])
    bmp = nt.nodes.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = 0.35
    bmp.inputs["Distance"].default_value = 0.08
    nt.links.new(w.outputs["Fac"], bmp.inputs["Height"])
    nt.links.new(bmp.outputs["Normal"], p.inputs["Normal"])
    m.diffuse_color = (*c1, 1)
    return m


STONE = mat_ashlar("Stone_Limestone", (0.26, 0.195, 0.125), (0.55, 0.43, 0.285),
                   (0.13, 0.11, 0.09))
STONE_LIGHT = mat_stone("Stone_Trim", (0.46, 0.36, 0.245), (0.68, 0.55, 0.385),
                        rough=0.72, bump=0.18)
STONE_DARK = mat_ashlar("Stone_Dark", (0.13, 0.11, 0.09), (0.27, 0.225, 0.18),
                        (0.07, 0.06, 0.05), rough=0.9)
MARBLE = mat_stone("Marble", (0.50, 0.455, 0.38), (0.72, 0.66, 0.56),
                   rough=0.42, bump=0.10, scale=1.8)
MARBLE_RED = mat_stone("Marble_Red", (0.16, 0.035, 0.045), (0.34, 0.10, 0.09),
                       rough=0.32, bump=0.08, scale=2.0)
MARBLE_GREEN = mat_stone("Marble_Green", (0.025, 0.08, 0.055), (0.07, 0.17, 0.11),
                         rough=0.32, bump=0.08, scale=2.0)
LEAD = mat_plain("Lead_Roof", (0.20, 0.22, 0.23), rough=0.40, metal=0.30)
ROOF_TILE = mat_tile("RoofTile", (0.12, 0.045, 0.025), (0.24, 0.10, 0.055))
LEAD_LIGHT = mat_plain("Lead_Ribs", (0.28, 0.30, 0.31), rough=0.36, metal=0.30)
GOLD = mat_plain("Gold", (0.95, 0.62, 0.18), rough=0.24, metal=1.0)
IRON = mat_plain("Iron", (0.035, 0.04, 0.045), rough=0.45, metal=0.8)
WOOD = mat_plain("BoatWood", (0.11, 0.05, 0.022), rough=0.55)
TREE = mat_plain("Cypress", (0.018, 0.045, 0.026), rough=0.9)
TREE_TRUNK = mat_plain("Trunk", (0.05, 0.035, 0.022), rough=0.9)
CITY_STONE = mat_plain("CityStone", (0.085, 0.085, 0.085), rough=0.95)
HILL = mat_plain("Hills", (0.03, 0.045, 0.055), rough=1.0)
HILLSIDE = mat_grass("Hillside")

WARM_WIN = mat_plain("Window_Warm", (0.03, 0.012, 0.002), rough=0.25,
                     emit=(1.0, 0.27, 0.045), emit_strength=3.3)
AMBER_WIN = mat_plain("Window_Amber", (0.03, 0.015, 0.004), rough=0.25,
                      emit=(1.0, 0.42, 0.11), emit_strength=2.6)
DIM_WIN = mat_plain("Window_Dim", (0.02, 0.012, 0.005), rough=0.3,
                    emit=(1.0, 0.38, 0.10), emit_strength=1.1)
DARK_WIN = mat_plain("Window_Dark", (0.004, 0.006, 0.009), rough=0.08,
                     metal=0.1)
DOOR = mat_plain("PortalDoor", (0.022, 0.010, 0.005), rough=0.38, metal=0.05,
                 emit=(0.5, 0.18, 0.05), emit_strength=0.25)
BRASS = mat_plain("Brass", (0.55, 0.32, 0.08), rough=0.3, metal=1.0)
MOON = mat_plain("Moon", (0.55, 0.5, 0.4), rough=1.0,
                 emit=(1.0, 0.94, 0.80), emit_strength=7.0)
LAMP_GLOW = mat_plain("LampGlow", (0.08, 0.04, 0.005), rough=0.2,
                      emit=(1.0, 0.58, 0.22), emit_strength=30.0)

WATER = bpy.data.materials.new("Bosphorus_Water")
WATER.use_nodes = True
_wn = WATER.node_tree
_wp = _principled(WATER)
_set(_wp, "Base Color", (0.005, 0.018, 0.026, 1))
_set(_wp, "Roughness", 0.05)
_set(_wp, "IOR", 1.333)
_set(_wp, "Specular IOR Level", 0.48)
_tex = _wn.nodes.new("ShaderNodeTexCoord")
_map = _wn.nodes.new("ShaderNodeMapping")
_map.inputs["Scale"].default_value = (1.0, 0.35, 1.0)
_noise = _wn.nodes.new("ShaderNodeTexNoise")
_noise.inputs["Scale"].default_value = 5.5
_noise.inputs["Detail"].default_value = 7.0
_noise.inputs["Roughness"].default_value = 0.55
_wn.links.new(_tex.outputs["Object"], _map.inputs["Vector"])
_wn.links.new(_map.outputs["Vector"], _noise.inputs["Vector"])
_b1 = _wn.nodes.new("ShaderNodeBump")
_b1.inputs["Strength"].default_value = 0.45
_b1.inputs["Distance"].default_value = 0.18
_wn.links.new(_noise.outputs["Fac"], _b1.inputs["Height"])
_b2 = _wn.nodes.new("ShaderNodeBump")
_b2.inputs["Strength"].default_value = 0.32
_b2.inputs["Distance"].default_value = 0.4
_noise2 = _wn.nodes.new("ShaderNodeTexNoise")
_noise2.inputs["Scale"].default_value = 0.32
_noise2.inputs["Detail"].default_value = 4.0
_wn.links.new(_map.outputs["Vector"], _noise2.inputs["Vector"])
_wn.links.new(_noise2.outputs["Fac"], _b2.inputs["Height"])
_wn.links.new(_b1.outputs["Normal"], _b2.inputs["Normal"])
_wn.links.new(_b2.outputs["Normal"], _wp.inputs["Normal"])
WATER.diffuse_color = (0.02, 0.06, 0.08, 1)

# ----------------------------------------------------------------------------
# mesh helpers
# ----------------------------------------------------------------------------

def new_obj(name, bm, mat, coll, smooth=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    if mat:
        me.materials.append(mat)
    if smooth:
        for poly in me.polygons:
            poly.use_smooth = True
    return ob


def add_box(name, dims, loc, mat, coll=C_BUILD, bevel=0.0, rot_z=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= dims[0]
        v.co.y *= dims[1]
        v.co.z *= dims[2]
    ob = new_obj(name, bm, mat, coll)
    ob.location = loc
    ob.rotation_euler[2] = rot_z
    if bevel > 0:
        md = ob.modifiers.new("bev", "BEVEL")
        md.width = bevel
        md.segments = 2
        md.limit_method = "ANGLE"
    return ob


def add_cyl(name, r, h, loc, mat, coll=C_BUILD, seg=48, r2=None,
            rot=(0, 0, 0), smooth=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                          radius1=r, radius2=(r if r2 is None else r2),
                          depth=h)
    if smooth:
        for f in bm.faces:
            f.smooth = abs(f.normal.z) < 0.85
    ob = new_obj(name, bm, mat, coll)
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def add_torus(name, R, r, loc, mat, coll=C_BUILD, maj=96, mino=10,
              rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r,
                                     major_segments=maj, minor_segments=mino,
                                     location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    coll.objects.link(ob)
    if mat:
        ob.data.materials.append(mat)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def add_sphere(name, r, loc, mat, coll=C_BUILD, seg=48, rings=24,
               zscale=1.0, cut_z=None, cut_x=None, close=False):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    if cut_z is not None:
        doomed = [v for v in bm.verts if v.co.z < cut_z - 1e-5]
        bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    if cut_x is not None:
        doomed = [v for v in bm.verts if v.co.x > cut_x + 1e-5]
        bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    for v in bm.verts:
        v.co.z *= zscale
    if close:
        edges = [e for e in bm.edges if e.is_boundary]
        if edges:
            bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    for f in bm.faces:
        f.smooth = True
    ob = new_obj(name, bm, mat, coll)
    ob.location = loc
    return ob


def add_curve(name, splines, bevel, mat, coll=C_BUILD, res=1):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.resolution_u = res
    cu.bevel_depth = bevel
    cu.bevel_resolution = 1
    cu.use_fill_caps = True
    for pts in splines:
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for p, co in zip(sp.points, pts):
            p.co = (co[0], co[1], co[2], 1.0)
    ob = bpy.data.objects.new(name, cu)
    coll.objects.link(ob)
    if mat:
        cu.materials.append(mat)
    return ob


# ----------------------------------------------------------------------------
# arched windows
# ----------------------------------------------------------------------------
FRAME_SPLINES = []


def arch_points(w, h, seg=14):
    r = w / 2.0
    sh = h - r
    pts = [(-r, 0.0), (r, 0.0), (r, sh)]
    for i in range(1, seg + 1):
        a = math.pi * i / seg
        pts.append((r * math.cos(a), sh + r * math.sin(a)))
    pts.append((-r, sh))
    return pts


def make_arch_plane(name, P, T, N, w, h, mat, coll=C_DETAIL):
    pts = arch_points(w, h)
    bm = bmesh.new()
    vs = [bm.verts.new((u, v, 0.0)) for (u, v) in pts]
    bm.faces.new(vs)
    ob = new_obj(name, bm, mat, coll)
    up = Vector((0, 0, 1))
    M = Matrix((T, up, N)).transposed().to_4x4()
    M.translation = P
    ob.matrix_world = M
    return ob


def add_window(name, P, T, N, w, h, lit=0.85, frame=True, fw=0.38,
               mat_override=None):
    P = Vector(P)
    T = Vector(T).normalized()
    N = Vector(N).normalized()
    if mat_override is not None:
        m = mat_override
    elif random.random() < lit:
        m = random.choices([WARM_WIN, AMBER_WIN, DIM_WIN],
                           weights=[0.55, 0.33, 0.12])[0]
    else:
        m = DARK_WIN
    make_arch_plane(name, P + N * 0.018, T, N, w, h, m)
    if frame:
        up = Vector((0, 0, 1))
        rr = w / 2.0 + fw
        sh = h - w / 2.0
        q = [(-rr, 0.0), (-rr, sh)]
        for i in range(15):
            a = math.pi - math.pi * i / 14
            q.append((rr * math.cos(a), sh + rr * math.sin(a)))
        q.append((rr, 0.0))
        pts = [P + T * u + up * v + N * 0.09 for (u, v) in q]
        FRAME_SPLINES.append(pts)


def add_hood(P, T, N, w, h):
    P = Vector(P); T = Vector(T); N = Vector(N); up = Vector((0, 0, 1))
    rr = w / 2.0 + 0.62
    sh = h - w / 2.0
    q = [(-rr, 0.0), (-rr, sh)]
    for i in range(15):
        a = math.pi - math.pi * i / 14
        q.append((rr * math.cos(a), sh + rr * math.sin(a)))
    q.append((rr, 0.0))
    FRAME_SPLINES.append([P + T * u + up * v + N * 0.42 for (u, v) in q])


def add_bars(P, T, N, w, h):
    P = Vector(P); T = Vector(T); N = Vector(N); up = Vector((0, 0, 1))
    M = Matrix((T, up, N)).transposed().to_4x4()
    specs = [(0.0, 0.13, h * 0.90, 0.08),
             (-w * 0.27, 0.10, h * 0.84, 0.07),
             (w * 0.27, 0.10, h * 0.84, 0.07)]
    for i, (u, bw, bh, bd) in enumerate(specs):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co.x *= bw; v.co.y *= bh; v.co.z *= bd
        ob = new_obj(f"Mullion_{i}", bm, STONE_LIGHT, C_DETAIL)
        m2 = M.copy()
        m2.translation = P + T * u + up * (bh / 2 + 0.1) + N * 0.14
        ob.matrix_world = m2
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= w * 0.86; v.co.y *= 0.12; v.co.z *= 0.09
    ob = new_obj("Transom", bm, STONE_LIGHT, C_DETAIL)
    m3 = M.copy(); m3.translation = P + up * (h * 0.62) + N * 0.14
    ob.matrix_world = m3


def add_sill(name, P, T, N, w):
    P = Vector(P)
    T = Vector(T)
    N = Vector(N)
    up = Vector((0, 0, 1))
    b = add_box(name, (w + 0.8, 0.45, 0.30), (0, 0, 0), STONE_LIGHT,
                C_DETAIL, bevel=0.04)
    M = Matrix((T, up, N)).transposed().to_4x4()
    M.translation = P + N * 0.18
    b.matrix_world = M


# ----------------------------------------------------------------------------
# main masses
# ----------------------------------------------------------------------------
add_box("Podium", (82, 70, 1.2), (0, 0, BASE_Z - 0.6), STONE_DARK, bevel=0.15)
add_box("LowerMass", (LOW_W, LOW_D, LOW_H), (0, 0, BASE_Z + LOW_H / 2), STONE)
add_box("BasePlinth", (LOW_W + 1.0, LOW_D + 1.0, 1.4),
        (0, 0, BASE_Z + 0.7), STONE_DARK, bevel=0.08)
add_box("LowerCornice", (LOW_W + 2.4, LOW_D + 2.4, 1.1),
        (0, 0, BASE_Z + LOW_H + 0.2), STONE_LIGHT, bevel=0.08)
add_box("UpperMass", (UP_W, UP_D, 9.0), (0, 0, BASE_Z + LOW_H + 4.5), STONE)
add_box("UpperCornice", (UP_W + 2.0, UP_D + 2.0, 0.9),
        (0, 0, BASE_Z + LOW_H + 9.0), STONE_LIGHT, bevel=0.06)
add_box("RoofSlab", (UP_W + 0.6, UP_D + 0.6, 0.8),
        (0, 0, ROOF_Z + 0.35), LEAD)
add_box("AtticBase", (ATTIC, ATTIC, 2.0), (0, 0, ROOF_Z + 1.0), STONE)
add_box("AtticCornice", (ATTIC + 1.6, ATTIC + 1.6, 0.9),
        (0, 0, ROOF_Z + 2.35), STONE_LIGHT, bevel=0.05)

# ----------------------------------------------------------------------------
# dome, drum, semi-domes
# ----------------------------------------------------------------------------
add_cyl("DrumWall", DRUM_R, DRUM_TOP - DRUM_BOT,
        (0, 0, (DRUM_BOT + DRUM_TOP) / 2), STONE, seg=128)
add_torus("DrumBaseRing", DRUM_R + 0.35, 0.55, (0, 0, DRUM_BOT + 0.2),
          STONE_LIGHT, maj=128, mino=10)
add_torus("DrumTopRing", DRUM_R + 0.45, 0.45, (0, 0, DRUM_TOP - 0.1),
          STONE_LIGHT, maj=128, mino=10)
add_torus("DrumMidBand", DRUM_R + 0.28, 0.18, (0, 0, DRUM_BOT + 1.1),
          STONE_LIGHT, maj=128, mino=8)
add_torus("DrumUpperBand", DRUM_R + 0.30, 0.20, (0, 0, DRUM_BOT + 8.9),
          STONE_LIGHT, maj=128, mino=8)

add_sphere("MainDome", DRUM_R, (0, 0, DRUM_TOP), LEAD, seg=128, rings=48,
           zscale=DOME_ZS, cut_z=0.0)

N_DRUM = 40
for i in range(N_DRUM):
    a = 2 * math.pi * i / N_DRUM
    N = Vector((math.cos(a), math.sin(a), 0))
    T = Vector((-math.sin(a), math.cos(a), 0))
    P = N * (DRUM_R + 0.03) + Vector((0, 0, DRUM_BOT + 1.15))
    add_window(f"DrumWin{i:02d}", P, T, N, 1.72, 6.4,
               lit=0.93 if i % 9 else 0.2, fw=0.20)
    aa = a + math.pi / N_DRUM
    pn = Vector((math.cos(aa), math.sin(aa), 0))
    add_box(f"DrumPil{i:02d}", (0.55, 0.75, 9.8),
            pn * (DRUM_R + 0.18) + Vector((0, 0, DRUM_BOT + 4.9)),
            STONE_LIGHT, C_DETAIL, bevel=0.03, rot_z=aa)

ribs = []
for i in range(40):
    a = 2 * math.pi * i / 40
    pts = []
    for k in range(19):
        t = (math.pi / 2) * k / 18
        rad = DRUM_R + 0.10
        pts.append((rad * math.sin(t) * math.cos(a),
                    rad * math.sin(t) * math.sin(a),
                    DRUM_TOP + (DRUM_R * DOME_ZS + 0.06) * math.cos(t)))
    ribs.append(pts)
add_curve("DomeRibs", ribs, 0.21, LEAD_LIGHT, C_DETAIL)
for k, frac in enumerate((0.28, 0.52, 0.74)):
    rr = DRUM_R * math.sqrt(max(0.0, 1.0 - frac * frac)) + 0.03
    zz = DRUM_TOP + DRUM_R * DOME_ZS * frac
    add_torus(f"DomeSeam{k}", rr, 0.065, (0, 0, zz), LEAD_LIGHT,
              maj=128, mino=6)
add_torus("DomeOculusRing", 1.1, 0.22, (0, 0, DOME_TOP + 0.15), GOLD,
          maj=40, mino=8)
add_sphere("DomeFinialBall", 0.75, (0, 0, DOME_TOP + 0.55), GOLD, seg=24,
           rings=12)
add_cyl("DomeFinialPole", 0.10, 2.4, (0, 0, DOME_TOP + 1.9), GOLD, seg=12)

# --- semi-domes east / west -------------------------------------------------
for sx in (-1, 1):
    cx = sx * DRUM_R
    a0, a1 = (math.pi / 2, 3 * math.pi / 2) if sx < 0 else (-math.pi / 2, math.pi / 2)
    bm = bmesh.new()
    n = 40
    rings = []
    for j in range(n + 1):
        a = a0 + (a1 - a0) * j / n
        x = cx + 17.0 * math.cos(a)
        y = 17.0 * math.sin(a)
        rings.append([bm.verts.new((x, y, ROOF_Z - 1.5)),
                      bm.verts.new((x, y, DRUM_BOT - 1.0))])
    for j in range(n):
        bm.faces.new((rings[j][0], rings[j + 1][0], rings[j + 1][1], rings[j][1]))
    bm.faces.new((rings[0][0], rings[0][1], rings[-1][1], rings[-1][0]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    new_obj(f"SemiDrum{sx}", bm, STONE, C_BUILD)

    sd = add_sphere(f"SemiDome{sx}", 17.0, (cx, 0, DRUM_BOT - 1.0), LEAD,
                    seg=96, rings=40, zscale=0.62, cut_z=0.0, cut_x=0.0,
                    close=True)
    if sx > 0:
        sd.rotation_euler[2] = math.pi

    sribs = []
    for k in range(15):
        a = a0 + (a1 - a0) * k / 14
        pts = []
        for m in range(16):
            t = (math.pi / 2) * m / 15
            x = cx + 17.10 * math.sin(t) * math.cos(a)
            y = 17.10 * math.sin(t) * math.sin(a)
            z = (DRUM_BOT - 1.0) + (17.05 * 0.62) * math.cos(t)
            pts.append((x, y, z))
        sribs.append(pts)
    add_curve(f"SemiDomeRibs{sx}", sribs, 0.15, LEAD_LIGHT, C_DETAIL)

    for k in range(7):
        a = a0 + (a1 - a0) * (0.12 + 0.76 * k / 6)
        N = Vector((math.cos(a), math.sin(a), 0))
        T = Vector((-math.sin(a), math.cos(a), 0))
        P = Vector((cx, 0, ROOF_Z - 0.6)) + N * 17.05
        add_window(f"SemiDrumWin{sx}_{k}", P, T, N, 1.55, 3.0,
                   lit=0.9, fw=0.2)

# --- exedrae (north & south) ------------------------------------------------
for sy in (-1, 1):
    cy = sy * 19.0
    a0, a1 = (math.pi, 2 * math.pi) if sy < 0 else (0.0, math.pi)
    bm = bmesh.new()
    n = 32
    rings = []
    for j in range(n + 1):
        a = a0 + (a1 - a0) * j / n
        x = 10.5 * math.cos(a)
        y = cy + 10.5 * math.sin(a)
        rings.append([bm.verts.new((x, y, ROOF_Z - 1.0)),
                      bm.verts.new((x, y, ROOF_Z + 1.3))])
    for j in range(n):
        bm.faces.new((rings[j][0], rings[j + 1][0], rings[j + 1][1], rings[j][1]))
    bm.faces.new((rings[0][0], rings[0][1], rings[-1][1], rings[-1][0]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    new_obj(f"ExedraDrum{sy}", bm, STONE, C_BUILD)

    ed = add_sphere(f"ExedraDome{sy}", 10.5, (0, cy, ROOF_Z + 0.5), LEAD,
                    seg=64, rings=28, zscale=0.65, cut_z=0.0)
    bm = bmesh.new()
    bm.from_mesh(ed.data)
    doomed = [v for v in bm.verts if v.co.y * sy < 0.001]
    bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    bm.to_mesh(ed.data)
    bm.free()

    for k in range(9):
        a = a0 + (a1 - a0) * (0.1 + 0.8 * k / 8)
        N = Vector((math.cos(a), math.sin(a), 0))
        T = Vector((-math.sin(a), math.cos(a), 0))
        P = Vector((0, cy, ROOF_Z - 0.9)) + N * 10.55
        add_window(f"ExedraWin{sy}_{k}", P, T, N, 1.15, 2.1,
                   lit=0.8, fw=0.16)

# ----------------------------------------------------------------------------
# minarets
# ----------------------------------------------------------------------------
def crescent(name, loc, size, coll=C_DETAIL, mat=GOLD):
    R = size
    r = size * 0.86
    d = size * 0.30
    alpha = math.acos((d * d + R * R - r * r) / (2 * d * R))
    pts = []
    for i in range(25):
        a = alpha + (2 * math.pi - 2 * alpha) * i / 24
        pts.append((R * math.cos(a), R * math.sin(a)))
    beta = math.atan2(R * math.sin(alpha), R * math.cos(alpha) - d)
    for i in range(13):
        a = -beta + 2 * beta * i / 12
        pts.append((d + r * math.cos(a), r * math.sin(a)))
    bm = bmesh.new()
    vs = [bm.verts.new((x, 0.0, z)) for (x, z) in pts]
    bm.faces.new(vs)
    ob = new_obj(name, bm, mat, coll)
    ob.location = loc
    md = ob.modifiers.new("sol", "SOLIDIFY")
    md.thickness = 0.10
    md.offset = 0
    return ob


def minaret(idx, x, y, hs=1.0):
    tag = f"Min{idx}"
    z0 = BASE_Z
    base_parts = [(7.2, 9.5), (6.2, 6.0), (5.2, 4.0)]
    zz = z0
    for i, (sz, hh) in enumerate(base_parts):
        add_box(f"{tag}_Base{i}", (sz, sz, hh), (x, y, zz + hh / 2), STONE,
                bevel=0.12)
        zz += hh
    zb = zz
    add_cyl(f"{tag}_Trans", 3.8, 3.5, (x, y, zb + 1.75), STONE, seg=8, r2=1.85)
    sh1 = 22.0 * hs
    add_cyl(f"{tag}_Shaft1", 1.70, sh1, (x, y, zb + 3.5 + sh1 / 2),
            STONE_LIGHT, seg=32)
    b1 = zb + 3.5 + sh1
    add_torus(f"{tag}_Corbel1", 2.45, 0.35, (x, y, b1 - 0.30), STONE_LIGHT,
              maj=48, mino=8)
    add_cyl(f"{tag}_Balc1", 2.95, 0.8, (x, y, b1 + 0.4), STONE_DARK, seg=48)
    add_cyl(f"{tag}_Balc1b", 2.95, 1.05, (x, y, b1 + 1.3), STONE_LIGHT,
            seg=48, r2=2.7)
    add_torus(f"{tag}_Rail1", 2.70, 0.09, (x, y, b1 + 1.8), IRON, maj=48, mino=6)
    sh2 = 10.0 * hs
    add_cyl(f"{tag}_Shaft2", 1.70, sh2, (x, y, b1 + 2.0 + sh2 / 2),
            STONE_LIGHT, seg=32)
    b2 = b1 + 2.0 + sh2
    add_torus(f"{tag}_Corbel2", 2.35, 0.30, (x, y, b2 - 0.25), STONE_LIGHT,
              maj=48, mino=8)
    add_cyl(f"{tag}_Balc2", 2.85, 0.75, (x, y, b2 + 0.35), STONE_DARK, seg=48)
    add_cyl(f"{tag}_Balc2b", 2.85, 0.95, (x, y, b2 + 1.15), STONE_LIGHT,
            seg=48, r2=2.6)
    add_torus(f"{tag}_Rail2", 2.65, 0.08, (x, y, b2 + 1.6), IRON, maj=48, mino=6)
    sh3 = 8.0 * hs
    add_cyl(f"{tag}_Shaft3", 1.62, sh3, (x, y, b2 + 1.9 + sh3 / 2),
            STONE_LIGHT, seg=32)
    zc = b2 + 1.9 + sh3
    add_cyl(f"{tag}_Cone", 2.45, 7.5, (x, y, zc + 3.75), LEAD, seg=48,
            r2=0.05)
    add_torus(f"{tag}_ConeRing", 2.35, 0.18, (x, y, zc + 0.2), STONE_LIGHT,
              maj=48, mino=8)
    zf = zc + 7.5
    add_sphere(f"{tag}_Ball", 0.55, (x, y, zf + 0.5), GOLD, seg=20, rings=10)
    add_cyl(f"{tag}_Pole", 0.07, 2.0, (x, y, zf + 1.8), GOLD, seg=10)
    crescent(f"{tag}_Crescent", (x, y - 0.35, zf + 3.05), 0.85)

    for zz2, nn in ((zb + 5.5, 4), (b1 + 4.5, 4), (b2 + 4.0, 4)):
        rad = 1.76 if zz2 < b2 else 1.68
        for k in range(nn):
            a = 2 * math.pi * k / nn + 0.3
            N = Vector((math.cos(a), math.sin(a), 0))
            T = Vector((-math.sin(a), math.cos(a), 0))
            P = Vector((x, y, zz2)) + N * rad
            add_window(f"{tag}_w{idx}_{zz2:.0f}_{k}", P, T, N, 0.55, 1.35,
                       lit=0.65, frame=False)
    return zf + 3.5


minaret(0, -46, -37, 1.0)
minaret(1, 46, -37, 1.0)
minaret(2, -46, 37, 0.96)
minaret(3, 46, 37, 0.96)

# ----------------------------------------------------------------------------
# facade windows, pilasters, portal
# ----------------------------------------------------------------------------
for x in (-32, -24, -16, -8, 8, 16, 24, 32):
    add_window(f"S_Low_{x}", (x, FRONT_Y - 0.03, BASE_Z + 3.6),
               (1, 0, 0), (0, -1, 0), 3.1, 10.5, lit=0.9)
    add_sill(f"SillS{x}", (x, FRONT_Y - 0.03, BASE_Z + 3.5),
             (1, 0, 0), (0, -1, 0), 3.1)
    add_bars((x, FRONT_Y - 0.03, BASE_Z + 3.6), (1, 0, 0), (0, -1, 0),
             3.1, 9.8)
    add_hood((x, FRONT_Y - 0.03, BASE_Z + 3.6), (1, 0, 0), (0, -1, 0),
             3.1, 10.5)

for x in (-30, -22.5, -15, -7.5, 0, 7.5, 15, 22.5, 30):
    add_window(f"S_Up_{x}", (x, FRONT_Y + 4.0 - 0.03, BASE_Z + 24.1),
               (1, 0, 0), (0, -1, 0), 2.2, 5.8,
               lit=1.0 if x == 0 else 0.85)
    add_sill(f"SillU{x}", (x, FRONT_Y + 4.0 - 0.03, BASE_Z + 24.0),
             (1, 0, 0), (0, -1, 0), 2.2)

for x in (-18, -12, -6, 0, 6, 12, 18):
    add_window(f"S_Att_{x}", (x, -ATTIC / 2 - 0.03, ROOF_Z + 2.4),
               (1, 0, 0), (0, -1, 0), 1.6, 3.4, lit=0.9, fw=0.18)

for sx in (-1, 1):
    N = Vector((sx, 0, 0))
    T = Vector((0, -sx, 0))
    xface = sx * (LOW_W / 2 + 0.03)
    for y in (-22, -11, 0, 11, 22):
        add_window(f"End_Low_{sx}_{y}", (xface, y, BASE_Z + 3.8), T, N,
                   2.9, 9.5, lit=0.8)
    xface2 = sx * (UP_W / 2 + 0.03)
    for y in (-18, -6, 6, 18):
        add_window(f"End_Up_{sx}_{y}", (xface2, y, BASE_Z + 24.2), T, N,
                   2.0, 5.2, lit=0.8)
    for y in (-15, -9, -3, 3, 9, 15):
        add_window(f"End_Att_{sx}_{y}", (sx * (ATTIC / 2 + 0.03), y, ROOF_Z + 2.5),
                   T, N, 1.4, 3.0, lit=0.7, fw=0.16)

for x in (-24, -12, 0, 12, 24):
    add_window(f"N_Low_{x}", (x, LOW_D / 2 + 0.03, BASE_Z + 3.6),
               (-1, 0, 0), (0, 1, 0), 2.6, 8.5, lit=0.55)
for x in (-18, -6, 6, 18):
    add_window(f"N_Up_{x}", (x, UP_D / 2 + 0.03, BASE_Z + 24.2),
               (-1, 0, 0), (0, 1, 0), 1.8, 4.6, lit=0.5)

for x in (-36, -28, -20, -12, -4, 4, 12, 20, 28, 36):
    add_box(f"PilasterS{x}", (1.5, 1.0, LOW_H - 1.0),
            (x, FRONT_Y - 0.55, BASE_Z + LOW_H / 2 - 0.2), STONE_LIGHT,
            C_DETAIL, bevel=0.05)
add_box("FacadeBaseBand", (76.5, 0.55, 0.7), (0, FRONT_Y - 0.22,
        BASE_Z + 3.0), STONE_LIGHT, C_DETAIL, bevel=0.04)
add_box("FacadeUpperBand", (76.5, 0.50, 0.55), (0, FRONT_Y - 0.22,
        BASE_Z + 16.55), STONE_LIGHT, C_DETAIL, bevel=0.04)

for zz2 in (BASE_Z + 15.8, BASE_Z + 19.4):
    add_box(f"StringS{zz2:.0f}", (LOW_W + 0.8, 0.55, 0.35),
            (0, FRONT_Y - 0.35, zz2), STONE_LIGHT, C_DETAIL, bevel=0.03)

# pilaster capitals + bases
for x in (-36, -28, -20, -12, -4, 4, 12, 20, 28, 36):
    add_box(f"PilCapS{x}", (2.0, 1.65, 0.8),
            (x, FRONT_Y - 0.55, BASE_Z + LOW_H - 0.75), STONE_LIGHT,
            C_DETAIL, bevel=0.06)
    add_box(f"PilBaseS{x}", (1.95, 1.55, 1.0),
            (x, FRONT_Y - 0.55, BASE_Z + 1.9), STONE_LIGHT,
            C_DETAIL, bevel=0.05)
for x in (-32, -24, -16, -8, 8, 16, 24, 32):
    add_window(f"S_Mid_{x}", (x, FRONT_Y - 0.03, BASE_Z + 17.1),
               (1, 0, 0), (0, -1, 0), 1.45, 2.9, lit=0.45, fw=0.15)
for x in (-30, -22.5, -15, -7.5, 0, 7.5, 15, 22.5, 30):
    add_window(f"S_Ocul_{x}", (x, FRONT_Y + 4.0 - 0.03, BASE_Z + 30.5),
               (1, 0, 0), (0, -1, 0), 1.1, 2.1, lit=0.55, fw=0.12)

for i in range(48):
    x = -37.0 + i * 1.58
    add_box(f"DentilS{i}", (0.34, 0.55, 0.42), (x, FRONT_Y - 0.35,
            BASE_Z + LOW_H - 0.55), STONE_LIGHT, C_DETAIL)
for i in range(44):
    x = -33.0 + i * 1.54
    add_box(f"DentilU{i}", (0.30, 0.45, 0.36), (x, FRONT_Y + 4.25,
            BASE_Z + LOW_H + 8.4), STONE_LIGHT, C_DETAIL)

for sx in (-1, 1):
    for sy in (-1, 1):
        add_box(f"CornerTower{sx}{sy}", (7.0, 7.0, 24.0),
                (sx * 37.0, sy * 30.0, BASE_Z + 12.0), STONE, bevel=0.1)
        add_box(f"CornerCap{sx}{sy}", (8.0, 8.0, 1.0),
                (sx * 37.0, sy * 30.0, BASE_Z + 24.2), STONE_LIGHT,
                bevel=0.06)
for sx in (-1, 1):
    add_box(f"Buttress{sx}", (5.5, 4.0, 19.0),
            (sx * 33.5, FRONT_Y - 1.4, BASE_Z + 9.5), STONE, bevel=0.08)
    add_box(f"ButtressCap{sx}", (4.0, 3.0, 4.0),
            (sx * 33.5, FRONT_Y - 1.4, BASE_Z + 21.0), STONE, bevel=0.06)

# upper-facade pilasters + corbels between the upper windows
for x in (-33.75, -26.25, -18.75, -11.25, -3.75, 3.75, 11.25, 18.75, 26.25, 33.75):
    add_box(f"UpperPil{x}", (1.35, 0.9, 10.0),
            (x, FRONT_Y + 4.0 - 0.40, BASE_Z + 27.4), STONE_LIGHT,
            C_DETAIL, bevel=0.05)
    add_box(f"UpperPilCap{x}", (1.75, 1.25, 0.65),
            (x, FRONT_Y + 4.0 - 0.40, BASE_Z + 32.3), STONE_LIGHT,
            C_DETAIL, bevel=0.05)
    add_box(f"UpperPilBase{x}", (1.6, 1.1, 0.7),
            (x, FRONT_Y + 4.0 - 0.40, BASE_Z + 22.8), STONE_LIGHT,
            C_DETAIL, bevel=0.04)
for i in range(17):
    x = -32 + i * 4.0
    add_box(f"UpperCorbel{i}", (0.45, 0.9, 0.55),
            (x, FRONT_Y + 3.5, BASE_Z + 32.35), STONE_LIGHT, C_DETAIL)

# central triple window above the portico
add_box("CentralSill", (12.0, 1.6, 0.55), (0, FRONT_Y - 0.8, BASE_Z + 16.2),
        STONE_LIGHT, C_DETAIL, bevel=0.06)
add_box("BalconyFloor", (12.6, 2.4, 0.45), (0, FRONT_Y - 1.2, BASE_Z + 14.0),
        STONE_LIGHT, C_DETAIL, bevel=0.05)
add_box("BalconyRail", (12.0, 0.28, 0.16), (0, FRONT_Y - 2.35, BASE_Z + 15.2),
        STONE_LIGHT, C_DETAIL, bevel=0.03)
for i in range(5):
    add_box(f"BalconyCorbel{i}", (0.55, 1.2, 0.75),
            (-4.8 + i * 2.4, FRONT_Y - 2.1, BASE_Z + 13.35), STONE_LIGHT,
            C_DETAIL, bevel=0.04)
for i in range(9):
    add_box(f"BalconyPost{i}", (0.18, 0.18, 1.05),
            (-5.2 + i * 1.3, FRONT_Y - 2.35, BASE_Z + 14.75),
            STONE_LIGHT, C_DETAIL)
for x in (-3.3, 0.0, 3.3):
    add_window(f"S_Central_{x}", (x, FRONT_Y - 0.05, BASE_Z + 17.2),
               (1, 0, 0), (0, -1, 0), 2.1, 3.9,
               lit=1.0 if x == 0 else 0.9, fw=0.22)
add_box("CentralHood", (12.0, 0.9, 0.5), (0, FRONT_Y - 0.35, BASE_Z + 21.8),
        STONE_LIGHT, C_DETAIL, bevel=0.05)

# portal
PX, PY = 0.0, FRONT_Y
add_window("PortalArch", (PX, PY - 0.10, BASE_Z + 1.0), (1, 0, 0), (0, -1, 0),
           6.4, 10.8, lit=1.0, frame=True, fw=0.55, mat_override=DOOR)
add_box("PortalDoorLintel", (6.6, 0.5, 0.45), (PX, PY - 0.30, BASE_Z + 8.7),
        STONE_LIGHT, C_DETAIL, bevel=0.04)
add_window("PortalTransom", (PX, PY - 0.28, BASE_Z + 9.05), (1, 0, 0), (0, -1, 0),
           3.6, 2.6, lit=1.0, frame=False, mat_override=AMBER_WIN)
for zz3 in (BASE_Z + 2.2, BASE_Z + 4.6, BASE_Z + 7.0):
    add_box(f"DoorBand{zz3:.0f}", (6.2, 0.14, 0.14), (PX, PY - 0.38, zz3),
            BRASS, C_DETAIL, bevel=0.02)
add_box("PortalLintel", (10.0, 1.6, 1.0), (PX, PY - 1.0, BASE_Z + 12.4),
        STONE_LIGHT, C_DETAIL, bevel=0.08)
for sx in (-1, 1):
    add_cyl(f"PortalCol{sx}", 0.62, 10.0, (PX + sx * 4.5, PY - 1.6, BASE_Z + 5.0),
            MARBLE, C_DETAIL, seg=24)
    add_box(f"PortalCap{sx}", (1.6, 1.6, 0.6),
            (PX + sx * 4.5, PY - 1.6, BASE_Z + 10.2), STONE_LIGHT,
            C_DETAIL, bevel=0.05)
add_box("PortalStep1", (14.0, 5.0, 0.5), (PX, PY - 2.5, BASE_Z + 0.25),
        STONE_LIGHT, C_DETAIL, bevel=0.05)
add_box("PortalStep2", (12.0, 4.0, 0.5), (PX, PY - 2.0, BASE_Z + 0.75),
        STONE_LIGHT, C_DETAIL, bevel=0.05)

# ----------------------------------------------------------------------------
# sea, shore, quay
# ----------------------------------------------------------------------------
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=300, y_segments=240, size=1.0)
for v in bm.verts:
    v.co.x *= 380.0
    v.co.y = v.co.y * 300.0 - 250.0
    v.co.z = SEA_Z
sea = new_obj("Sea", bm, WATER, C_ENV)
for tex_name, nscale, strength in (("swell", 9.0, 0.10),
                                   ("chop", 3.2, 0.045)):
    tex = bpy.data.textures.new(tex_name, "CLOUDS")
    tex.noise_scale = nscale
    tex.noise_depth = 4
    md = sea.modifiers.new(tex_name, "DISPLACE")
    md.texture = tex
    md.strength = strength
    md.mid_level = 0.5
    md.direction = "Z"
# far water plane, no displacement
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=2, y_segments=2, size=1.0)
for v in bm.verts:
    v.co.x *= 3000.0
    v.co.y = v.co.y * 3000.0 - 500.0
    v.co.z = SEA_Z - 0.06
new_obj("SeaFar", bm, WATER, C_ENV)

# waterfront terrace (peninsula) with sea on three sides
add_box("Land", (276, 162, 1.6), (0, 39, QUAY_Z - 0.8), STONE_DARK, C_ENV)
add_box("Quay", (280, 12, 2.0), (0, -38, QUAY_Z - 1.0), STONE_LIGHT, C_ENV,
        bevel=0.15)
add_box("QuayLip", (280, 1.2, 0.5), (0, -44.2, QUAY_Z + 0.15), STONE_LIGHT,
        C_ENV, bevel=0.08)
add_box("QuayRail", (280, 0.35, 0.9), (0, -43.8, QUAY_Z + 0.75), STONE_LIGHT,
        C_ENV, bevel=0.04)
# far shore across the water
add_box("FarShore", (1700, 260, 1.8), (0, 330, SEA_Z + 0.9), STONE_DARK, C_ENV)

for i in range(13):
    x = -120 + i * 20
    add_cyl(f"Bollard{i}", 0.32, 1.15, (x, -43.0, QUAY_Z + 0.55), IRON,
            C_DETAIL, seg=12)
for i in range(11):
    x = -120 + i * 24
    if abs(x) < 8:
        continue
    add_cyl(f"LampPost{i}", 0.11, 4.6, (x, -42.0, QUAY_Z + 2.3), IRON,
            C_DETAIL, seg=10)
    add_sphere(f"LampGlobe{i}", 0.30, (x, -42.0, QUAY_Z + 4.7), LAMP_GLOW,
               C_DETAIL, seg=16, rings=8)
    add_box(f"LampCap{i}", (0.56, 0.56, 0.12), (x, -42.0, QUAY_Z + 5.0),
            IRON, C_DETAIL)


def cypress(name, x, y, h, base_z=QUAY_Z):
    add_cyl(name + "_trunk", 0.28, h * 0.22, (x, y, base_z + h * 0.11),
            TREE_TRUNK, C_ENV, seg=10)
    bm = bmesh.new()
    seg = 20
    levels = 16
    rings = []
    for j in range(levels + 1):
        t = j / levels
        rad = (h * 0.155) * (1.0 - t) ** 0.72
        rad *= 1.0 + 0.16 * math.sin(t * 19.0 + x)
        rad = max(rad, 0.018)
        z = base_z + h * (0.16 + 0.82 * t)
        ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            wob = 1.0 + 0.10 * math.sin(a * 5.0 + t * 13.0 + x)
            ring.append(bm.verts.new((x + rad * wob * math.cos(a),
                                      y + rad * wob * math.sin(a), z)))
        rings.append(ring)
    for j in range(levels):
        for i in range(seg):
            i2 = (i + 1) % seg
            bm.faces.new((rings[j][i], rings[j][i2], rings[j + 1][i2], rings[j + 1][i]))
    bm.faces.new(list(reversed(rings[0])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = True
    new_obj(f"{name}_c", bm, TREE, C_ENV)


for i, x in enumerate((-126, -112, -98, 96, 110, 124)):
    cypress(f"Cypress{i}", x, -39.5, 20 + (i % 3) * 3.0)
for i, (x, y) in enumerate(((-118, 30), (-124, 58), (120, 34), (126, 66))):
    cypress(f"CypressB{i}", x, y, 17 + (i % 2) * 5.0)
for i, x in enumerate((-130, -106, -84, -62, 62, 84, 106, 130)):
    cypress(f"CrestCypress{i}", x, -41.5, 9 + (i % 3) * 2.0)


# ----------------------------------------------------------------------------
# the hill: Hagia Sophia on the crest, sea 28 m below
# ----------------------------------------------------------------------------
def hill_z(y, x=0.0):
    t = (y - WATER_Y) / (CREST_Y - WATER_Y)
    t = max(0.0, min(1.0, t))
    s = t * t * (3.0 - 2.0 * t)
    z = SEA_Z + 16.0 * s
    if 0.0 < t < 1.0:
        z += 0.45 * math.sin(x * 0.06 + 1.2) * math.sin(t * math.pi)
        z += 0.18 * math.sin(x * 0.17 + y * 0.11)
        z += 8.0 * math.exp(-((x + 130.0) / 80.0) ** 2) * math.sin(t * math.pi) ** 1.2
        z += 4.5 * math.exp(-((x - 155.0) / 95.0) ** 2) * math.sin(t * math.pi) ** 1.3
    return z


# hillside surface
NX, NY = 96, 40
bm = bmesh.new()
rows = []
for j in range(NY + 1):
    y = WATER_Y + (CREST_Y - WATER_Y) * j / NY
    row = []
    for i in range(NX + 1):
        x = -260.0 + 520.0 * i / NX
        row.append(bm.verts.new((x, y, hill_z(y, x))))
    rows.append(row)
for j in range(NY):
    for i in range(NX):
        bm.faces.new((rows[j][i], rows[j][i + 1],
                      rows[j + 1][i + 1], rows[j + 1][i]))
for f in bm.faces:
    f.smooth = True
hill = new_obj("Hillside", bm, HILLSIDE, C_ENV)
md = hill.modifiers.new("solid", "SOLIDIFY")
md.thickness = 2.5

# crest retaining wall just under the terrace
add_box("CrestWall", (430, 3.2, 5.4), (0, -45.6, -0.7), STONE, C_ENV,
        bevel=0.12)
add_box("CrestCornice", (432, 3.8, 0.5), (0, -45.4, 2.15), STONE_LIGHT,
        C_ENV, bevel=0.06)

# (the slope is left natural; only the crest retains a wall)

# rock outcrops and shrubs break up the green slope
random.seed(41)
for i in range(18):
    x = random.uniform(-235, 235)
    yy = random.uniform(-88, -50)
    if abs(x) < 14:
        continue
    zz = hill_z(yy)
    add_sphere(f"Rock{i}", random.uniform(2.2, 5.5), (x, yy, zz + 0.4),
               STONE_DARK, C_ENV, seg=16, rings=8, zscale=0.45, cut_z=0.0)
for i in range(14):
    x = random.uniform(-220, 220)
    yy = random.uniform(-86, -50)
    if abs(x) < 18:
        continue
    zz = hill_z(yy)
    add_sphere(f"Shrub{i}", random.uniform(1.1, 2.1), (x, yy, zz + 1.0),
               TREE, C_ENV, seg=12, rings=6, zscale=0.75, cut_z=0.0)

# grand stair from the lower quay to the terrace
NSTEP = 32
for i in range(NSTEP):
    yy = -90.0 + i * (43.0 / (NSTEP - 1))
    zz = hill_z(yy) + 0.14
    add_box(f"Stair{i}", (9.2, 1.65, 1.30), (0, yy, zz - 0.65),
            STONE, C_ENV, bevel=0.03)
    if i in (8, 16, 24):
        add_box(f"StairLanding{i}", (12.0, 3.6, 1.3), (0, yy, zz - 0.6),
                STONE_LIGHT, C_ENV, bevel=0.04)
    if i % 4 == 0:
        lz = zz + 3.4
        add_cyl(f"StairLampPost{i}", 0.09, 3.2, (5.9, yy, zz + 1.6),
                IRON, C_DETAIL, seg=8)
        add_sphere(f"StairLampGlobe{i}", 0.32, (5.9, yy, lz), LAMP_GLOW,
                   C_DETAIL, seg=14, rings=6)
        add_cyl(f"StairLampPostL{i}", 0.09, 3.2, (-5.9, yy, zz + 1.6),
                IRON, C_DETAIL, seg=8)
        add_sphere(f"StairLampGlobeL{i}", 0.32, (-5.9, yy, lz), LAMP_GLOW,
                   C_DETAIL, seg=14, rings=6)
        STAIR_LAMPS.append((5.9, yy, lz))

# stair parapets as curves
for sx in (-1, 1):
    pts = []
    for i in range(0, NSTEP, 2):
        yy = -90.0 + i * (43.0 / (NSTEP - 1))
        zz = hill_z(yy) + 0.95
        pts.append((sx * 5.2, yy, zz))
    add_curve(f"StairRail{sx}", [pts], 0.22, STONE_LIGHT, C_ENV)

add_box("LowerLanding", (18, 5, 1.2), (0, -91.5, SEA_Z + 0.6), STONE_LIGHT,
        C_ENV, bevel=0.05)
add_box("UpperLanding", (18, 3, 1.0), (0, -46.8, 1.55), STONE_LIGHT,
        C_ENV, bevel=0.05)

# cypresses on the hillside
for i, (x, yy, h) in enumerate(((-28, -86, 12), (-44, -78, 15), (30, -83, 13),
                                (48, -72, 16), (-70, -60, 12), (72, -58, 14),
                                (-150, -84, 17), (150, -80, 16),
                                (-108, -74, 19), (110, -70, 18),
                                (-190, -66, 16), (192, -62, 15),
                                (-20, -58, 11), (22, -56, 12))):
    cypress(f"SlopeCypress{i}", x, yy, h, base_z=hill_z(yy) + 0.15)

# hillside houses with warm windows
def hill_house(name, x, y, w=13.0, d=9.0, h=7.0):
    z0 = hill_z(y)
    add_box(name + "_base", (w + 2.2, d + 2.2, 3.0), (x, y, z0 - 0.4),
            STONE_DARK, C_ENV, bevel=0.08)
    add_box(name + "_body", (w, d, h), (x, y, z0 + 1.6), STONE, C_ENV,
            bevel=0.08)
    # gable roof
    bm = bmesh.new()
    zr = z0 + 1.6 + h / 2
    v = [bm.verts.new((-w / 2 - 0.7, -d / 2 - 0.7, 0)),
         bm.verts.new((w / 2 + 0.7, -d / 2 - 0.7, 0)),
         bm.verts.new((w / 2 + 0.7, d / 2 + 0.7, 0)),
         bm.verts.new((-w / 2 - 0.7, d / 2 + 0.7, 0)),
         bm.verts.new((-w / 2 - 0.7, 0, 2.4)),
         bm.verts.new((w / 2 + 0.7, 0, 2.4))]
    bm.faces.new((v[0], v[1], v[5], v[4]))
    bm.faces.new((v[2], v[3], v[4], v[5]))
    bm.faces.new((v[0], v[4], v[3]))
    bm.faces.new((v[1], v[2], v[5]))
    roof = new_obj(name + "_roof", bm, ROOF_TILE, C_ENV)
    roof.location = (x, y, zr)
    add_box(name + "_chimney", (0.7, 0.7, 1.8), (x + w * 0.25, y - d * 0.2, zr + 1.8),
            STONE_DARK, C_ENV)
    for k in range(2):
        px = x - w * 0.24 + k * w * 0.48
        add_window(name + f"_w{k}", (px, y - d / 2 - 0.03, z0 + 2.6),
                   (1, 0, 0), (0, -1, 0), 1.15, 2.1, lit=1.0, frame=False)
    add_box(name + "_garden", (w, 0.6, 1.1),
            (x, y - d / 2 - 2.0, z0 + 1.8), STONE_DARK, C_ENV, bevel=0.03)
    HOUSE_LIGHTS.append((x, y + 2, z0 + 3.0))


hill_house("HillHouse0", -58, -74)
hill_house("HillHouse1", -92, -64, 15, 10, 8)
hill_house("HillHouse2", -124, -80, 12, 9, 7)
hill_house("HillHouse3", 58, -78)
hill_house("HillHouse4", 94, -62, 16, 10, 8)
hill_house("HillHouse5", 124, -84, 12, 8, 6)
hill_house("HillHouse6", -40, -86, 10, 8, 6)
hill_house("HillHouse7", 42, -88, 10, 8, 6)
hill_house("HillHouse8", -152, -74, 14, 10, 8)
hill_house("HillHouse9", 158, -78, 13, 9, 7)
hill_house("HillHouse10", -206, -86, 12, 9, 6)
hill_house("HillHouse11", 208, -90, 12, 8, 6)
hill_house("HillHouse12", -36, -82, 10, 8, 6)
hill_house("HillHouse13", 34, -84, 10, 8, 6)
hill_house("HillHouse14", -168, -62, 13, 10, 7)
hill_house("HillHouse15", 174, -68, 14, 10, 8)
hill_house("HillHouse16", -214, -74, 12, 9, 6)
hill_house("HillHouse17", 220, -78, 12, 8, 6)
hill_house("HillHouse18", -86, -56, 11, 9, 7)
hill_house("HillHouse19", 112, -54, 12, 9, 7)

# lower waterfront at sea level
add_box("LowerQuay", (430, 10, 1.8), (0, -97.0, SEA_Z + 1.0), STONE_LIGHT,
        C_ENV, bevel=0.10)
add_box("LowerSeawall", (430, 3.0, 5.0), (0, -102.0, SEA_Z - 1.2), STONE_DARK,
        C_ENV, bevel=0.10)
LOWER_LAMPS = []
for i in range(9):
    lx = -160 + i * 40
    lz = SEA_Z + 4.0
    add_cyl(f"LowerLampPost{i}", 0.08, 3.2, (lx, -98.0, SEA_Z + 2.6), IRON,
            C_DETAIL, seg=8)
    add_sphere(f"LowerLampGlobe{i}", 0.30, (lx, -98.0, lz), LAMP_GLOW,
               C_DETAIL, seg=14, rings=6)
    LOWER_LAMPS.append((lx, -98.0, lz))
    add_cyl(f"LowerBollard{i}", 0.28, 1.0, (lx + 12, -100.0, SEA_Z + 0.7),
            IRON, C_DETAIL, seg=10)

# small secondary mosque silhouette on the plateau, left of Hagia Sophia
add_box("SmallMosqueBody", (26, 20, 9), (-108, 8, QUAY_Z + 4.5), STONE_DARK,
        C_ENV, bevel=0.1)
add_sphere("SmallMosqueDome", 8.5, (-108, 8, QUAY_Z + 9.0), LEAD, C_ENV,
           seg=40, rings=20, zscale=0.85, cut_z=0.0)
for sx in (-1, 1):
    add_cyl(f"SmallMosqueMin{sx}", 0.75, 26, (-108 + sx * 15, 12,
            QUAY_Z + 13.0), STONE_DARK, C_ENV, seg=12)
    add_cyl(f"SmallMosqueCap{sx}", 1.3, 5.5, (-108 + sx * 15, 12,
            QUAY_Z + 28.8), LEAD, C_ENV, seg=10, r2=0.04)
for k in range(3):
    add_window(f"SmallMosqueWin{k}", (-114 + k * 6, 7.95, QUAY_Z + 2.0),
               (1, 0, 0), (0, -1, 0), 1.3, 2.6, lit=1.0, frame=False)

# low houses on the plateau flanks
def plateau_house(name, x, y, w, d, h):
    add_box(name + "_b", (w, d, h), (x, y, QUAY_Z + h / 2), STONE, C_ENV,
            bevel=0.06)
    bm = bmesh.new()
    v = [bm.verts.new((-w/2 - 0.5, -d/2 - 0.5, 0)),
         bm.verts.new((w/2 + 0.5, -d/2 - 0.5, 0)),
         bm.verts.new((w/2 + 0.5, d/2 + 0.5, 0)),
         bm.verts.new((-w/2 - 0.5, d/2 + 0.5, 0)),
         bm.verts.new((-w/2 - 0.5, 0, 2.0)),
         bm.verts.new((w/2 + 0.5, 0, 2.0))]
    bm.faces.new((v[0], v[1], v[5], v[4]))
    bm.faces.new((v[2], v[3], v[4], v[5]))
    bm.faces.new((v[0], v[4], v[3]))
    bm.faces.new((v[1], v[2], v[5]))
    roof = new_obj(name + "_r", bm, ROOF_TILE, C_ENV)
    roof.location = (x, y, QUAY_Z + h)
    for k in range(2):
        add_window(name + f"_w{k}", (x - w*0.22 + k*w*0.44, y - d/2 - 0.03,
                   QUAY_Z + 1.5), (1, 0, 0), (0, -1, 0), 1.1, 2.0,
                   lit=1.0, frame=False)

plateau_house("PlateauH0", -65, 6, 13, 10, 7)
plateau_house("PlateauH1", -82, 20, 11, 9, 6)
plateau_house("PlateauH2", 66, 2, 12, 10, 7)
plateau_house("PlateauH3", 86, 18, 14, 10, 8)
plateau_house("PlateauH4", 115, 4, 11, 9, 6)
for i, hx in enumerate((-120, -98, -76, 76, 98, 120)):
    plateau_house(f"CrestHouse{i}", hx, -35.8, 11, 9, 6.5 + (i % 2))
for i, hx in enumerate((-132, -108, -86, -66, 66, 86, 108, 132)):
    cypress(f"CrestCypressB{i}", hx, -41.0, 8 + (i % 3) * 2.0)

add_box("GardenWall", (276, 1.2, 2.6), (0, -35.2, QUAY_Z + 1.3), STONE,
        C_ENV, bevel=0.05)

# ----------------------------------------------------------------------------
# boats
# ----------------------------------------------------------------------------
def boat(name, loc, scale=1.0, rot=0.0):
    x, y, z = loc
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=28, v_segments=14, radius=1.0)
    doomed = [v for v in bm.verts if v.co.z > 0.10]
    bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    for v in bm.verts:
        v.co.x *= 4.4 * scale
        v.co.y *= 1.35 * scale
        v.co.z *= 1.15 * scale
    hull = new_obj(name + "_hull", bm, WOOD, C_ENV)
    hull.location = (x, y, z)
    hull.rotation_euler[2] = rot
    add_box(name + "_deck", (6.8 * scale, 1.9 * scale, 0.12),
            (x, y, z + 0.55 * scale), WOOD, C_ENV, rot_z=rot)
    add_box(name + "_cabin", (2.4 * scale, 1.35 * scale, 0.9 * scale),
            (x - 0.8 * scale, y, z + 1.0 * scale), WOOD, C_ENV, rot_z=rot)
    add_cyl(name + "_mast", 0.06 * scale, 4.2 * scale,
            (x + 1.6 * scale, y, z + 2.4 * scale), WOOD, C_ENV, seg=8)
    add_sphere(name + "_lantern", 0.18 * scale,
               (x + 1.6 * scale, y, z + 4.4 * scale), LAMP_GLOW,
               C_ENV, seg=12, rings=6)


boat("Boat1", (-80, -128, SEA_Z + 0.15), 1.35, 0.35)
boat("Boat2", (58, -160, SEA_Z + 0.1), 1.0, -0.5)
boat("Boat3", (15, -108, SEA_Z + 0.1), 0.75, 0.1)


def caique(name, loc, rot=0.0):
    x, y, z = loc
    sections = [(-6.2, 0.10), (-5.0, 0.75), (-3.0, 1.25), (0.0, 1.45),
                (2.8, 1.25), (5.0, 0.65), (6.2, 0.06)]
    bm = bmesh.new()
    rings = []
    for (sx, w) in sections:
        ring = [bm.verts.new((sx, w, 0.38)),
                bm.verts.new((sx, w * 0.94, -0.30)),
                bm.verts.new((sx, 0.0, -0.95)),
                bm.verts.new((sx, -w * 0.94, -0.30)),
                bm.verts.new((sx, -w, 0.38))]
        rings.append(ring)
    for j in range(len(rings) - 1):
        for i in range(5):
            i2 = (i + 1) % 5
            bm.faces.new((rings[j][i], rings[j][i2], rings[j + 1][i2], rings[j + 1][i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    hull = new_obj(name + "_hull", bm, WOOD, C_ENV)
    hull.location = (x, y, z); hull.rotation_euler[2] = rot
    # rim curve
    rim = [Vector((sx, w, 0.40)) for (sx, w) in sections]
    rim += [Vector((sx, -w, 0.40)) for (sx, w) in reversed(sections)]
    add_curve(name + "_rim", [[tuple((hull.matrix_world @ p)) for p in rim]],
              0.06, WOOD, C_ENV)
    add_box(name + "_deck", (8.5, 2.1, 0.10), (x, y, z + 0.34), WOOD, C_ENV,
            rot_z=rot)
    add_box(name + "_cabin", (3.2, 1.5, 1.15), (x - 1.2, y, z + 0.95), WOOD,
            C_ENV, rot_z=rot)
    add_box(name + "_cabinTop", (3.5, 1.75, 0.12), (x - 1.2, y, z + 1.56),
            WOOD, C_ENV, rot_z=rot)
    add_cyl(name + "_mast", 0.07, 5.6, (x + 1.8, y, z + 2.6), WOOD, C_ENV,
            seg=8)
    add_cyl(name + "_yard", 0.05, 5.0, (x + 1.8, y, z + 4.3), WOOD, C_ENV,
            seg=6, rot=(0, math.radians(90), 0))
    add_sphere(name + "_lantern", 0.22, (x + 1.8, y, z + 5.5), LAMP_GLOW,
               C_ENV, seg=12, rings=6)


# a lit caique in the foreground
caique("Caique", (-95, -205, SEA_Z + 0.12), 0.22)



# ----------------------------------------------------------------------------
# distant city
# ----------------------------------------------------------------------------
def city_block(x, y, w, d, h):
    add_box("CityB", (w, d, h), (x, y, QUAY_Z + h / 2), CITY_STONE, C_CITY)


random.seed(11)
for i in range(52):
    x = random.uniform(-560, 560)
    y = random.uniform(230, 430)
    if abs(x) < 80 and y < 260:
        continue
    city_block(x, y, random.uniform(8, 26), random.uniform(8, 22),
               random.uniform(6, 18))


def far_mosque(x, y, s):
    add_box(f"FM{x}_body", (30 * s, 24 * s, 10 * s), (x, y, QUAY_Z + 5 * s),
            CITY_STONE, C_CITY)
    add_sphere(f"FM{x}_dome", 9 * s, (x, y, QUAY_Z + 10 * s), CITY_STONE,
               C_CITY, seg=32, rings=16, zscale=0.85, cut_z=0.0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            px = x + sx * 18 * s
            py = y + sy * 14 * s
            add_cyl(f"FM{x}_min", 0.7 * s, 30 * s, (px, py, QUAY_Z + 15 * s),
                    CITY_STONE, C_CITY, seg=10)
            add_cyl(f"FM{x}_cap", 1.3 * s, 6 * s, (px, py, QUAY_Z + 32 * s),
                    CITY_STONE, C_CITY, seg=8, r2=0.05)


far_mosque(-230, 300, 1.7)
far_mosque(260, 330, 1.8)
far_mosque(40, 410, 1.4)

random.seed(23)
for i in range(30):
    lx = random.uniform(-520, 520)
    ly = random.uniform(198, 214)
    lz = random.uniform(3.0, 10.0)
    add_sphere(f"FarLight{i}", 0.38, (lx, ly, lz), LAMP_GLOW, C_CITY,
               seg=8, rings=4)

for i, (x, y, r, h) in enumerate([(-420, 620, 300, 26), (260, 680, 340, 20),
                                  (620, 600, 240, 18)]):
    add_sphere(f"Hill{i}", r, (x, y, 0), HILL, C_CITY, seg=48, rings=20,
               zscale=h / r, cut_z=0.0)

# lower the far city to the new sea level
for ob in C_CITY.objects:
    ob.location.z -= 14.0

# frames as one curve object
add_curve("WindowFrames", FRAME_SPLINES, 0.26, STONE_LIGHT, C_DETAIL)

# ----------------------------------------------------------------------------
# lighting - blue hour
# ----------------------------------------------------------------------------
world = bpy.data.worlds.new("BlueHour")
world.use_nodes = True
scene.world = world
nt = world.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
out = nt.nodes.new("ShaderNodeOutputWorld")
bg = nt.nodes.new("ShaderNodeBackground")
geo = nt.nodes.new("ShaderNodeNewGeometry")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.interpolation = "EASE"
els = ramp.color_ramp.elements
els[0].position = 0.0
els[0].color = (0.95, 0.38, 0.19, 1)
els[1].position = 0.07
els[1].color = (0.62, 0.23, 0.22, 1)
e2 = ramp.color_ramp.elements.new(0.16)
e2.color = (0.30, 0.17, 0.28, 1)
e5 = ramp.color_ramp.elements.new(0.28)
e5.color = (0.075, 0.13, 0.34, 1)
e3 = ramp.color_ramp.elements.new(0.52)
e3.color = (0.025, 0.06, 0.22, 1)
e4 = ramp.color_ramp.elements.new(1.0)
e4.color = (0.008, 0.022, 0.09, 1)
nt.links.new(geo.outputs["Incoming"], sep.inputs["Vector"])
negz = nt.nodes.new("ShaderNodeMath")
negz.operation = "MULTIPLY"
negz.inputs[1].default_value = -1.0
nt.links.new(sep.outputs["Z"], negz.inputs[0])
nt.links.new(negz.outputs[0], ramp.inputs["Fac"])
haze = nt.nodes.new("ShaderNodeMath")
haze.operation = "POWER"
haze.inputs[1].default_value = 8.0
inv = nt.nodes.new("ShaderNodeMath")
inv.operation = "SUBTRACT"
inv.inputs[0].default_value = 1.0
nt.links.new(negz.outputs[0], inv.inputs[1])
absn = nt.nodes.new("ShaderNodeMath")
absn.operation = "ABSOLUTE"
nt.links.new(inv.outputs[0], absn.inputs[0])
nt.links.new(absn.outputs[0], haze.inputs[0])
mix = nt.nodes.new("ShaderNodeMix")
mix.data_type = "RGBA"
mix.blend_type = "ADD"
mix.inputs[7].default_value = (1.0, 0.36, 0.12, 1)
hazemul = nt.nodes.new("ShaderNodeMath")
hazemul.operation = "MULTIPLY"
hazemul.inputs[1].default_value = 0.10
nt.links.new(haze.outputs[0], hazemul.inputs[0])
nt.links.new(ramp.outputs["Color"], mix.inputs[6])
nt.links.new(hazemul.outputs[0], mix.inputs[0])
nt.links.new(mix.outputs[2], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 0.22
nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def add_light(kind, loc, energy, color, name, target=None, size=None,
              spot_size=None, blend=0.5, shape="DISK", size_y=None):
    bpy.ops.object.light_add(type=kind, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.data.energy = energy
    ob.data.color = color
    if kind == "AREA":
        ob.data.shape = shape
        if size:
            ob.data.size = size
        if size_y:
            ob.data.size_y = size_y
    if kind == "SPOT":
        if spot_size:
            ob.data.spot_size = spot_size
        ob.data.spot_blend = blend
        ob.data.shadow_soft_size = 0.5
    if kind == "POINT":
        ob.data.shadow_soft_size = 0.25
    if target:
        d = Vector(target) - Vector(loc)
        ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    C_LIGHT.objects.link(ob)
    return ob


add_light("AREA", (90, -190, 95), 50000, (0.48, 0.64, 1.0), "SkyFill",
          target=(0, 0, 30), size=80, shape="DISK")
add_light("AREA", (-230, -10, 55), 70000, (1.0, 0.48, 0.24), "WestRim",
          target=(0, 0, 34), size=55, size_y=28, shape="RECTANGLE")
add_light("AREA", (80, 180, 120), 60000, (0.40, 0.62, 1.0), "BackRim",
          target=(0, 0, 35), size=80, shape="DISK")
add_light("AREA", (-260, -140, 30), 90000, (1.0, 0.46, 0.20), "KeyWarm",
          target=(0, -30, 20), size=55, size_y=28, shape="RECTANGLE")
add_light("AREA", (200, 150, 80), 40000, (0.38, 0.60, 1.0), "KeyCool",
          target=(0, 0, 32), size=70, shape="DISK")

for i, x in enumerate((-36, -27, -18, -9, 0, 9, 18, 27, 36)):
    add_light("SPOT", (x - 3.2, -38.5, 2.4), 1200, (1.0, 0.58, 0.28),
              f"FacadeSpot{i}", target=(x + 2.0, -26, 23),
              spot_size=math.radians(38), blend=0.45)

for i, (x, y) in enumerate(((-44, -36), (44, -36), (-44, 36), (44, 36))):
    add_light("SPOT", (x + (3 if x > 0 else -3), y - 6, 2.4), 5000,
              (1.0, 0.64, 0.34), f"MinaretSpot{i}",
              target=(x, y, 48), spot_size=math.radians(14), blend=0.45)

for i, (x, y) in enumerate(((-18, -55), (18, -55))):
    add_light("SPOT", (x, y, 20), 16000, (1.0, 0.68, 0.40),
              f"DomeSpot{i}", target=(0, -5, 50),
              spot_size=math.radians(26), blend=0.5)
add_light("AREA", (55, -95, 65), 3000, (1.0, 0.72, 0.46), "DomeWash",
          target=(0, 0, 52), size=55, size_y=27, shape="RECTANGLE")
add_light("AREA", (0, -95, 32), 4000, (1.0, 0.68, 0.40), "DomeFlood",
          target=(0, 0, 52), size=35, size_y=18, shape="RECTANGLE")
for i, x in enumerate((-26, -9, 9, 26)):
    add_light("SPOT", (x, -44.0, 2.4), 300, (1.0, 0.62, 0.32),
              f"UpperWash{i}", target=(x * 0.7, -27, 28),
              spot_size=math.radians(30), blend=0.5)
add_light("SPOT", (0, -44.0, 2.4), 5000, (1.0, 0.66, 0.38),
          "DrumWash", target=(0, -12, 41), spot_size=math.radians(55), blend=0.75)

for i in range(11):
    x = -120 + i * 24
    if abs(x) < 8:
        continue
    add_light("POINT", (x, -42.0, QUAY_Z + 4.7), 240, (1.0, 0.55, 0.22),
              f"QuayLamp{i}")

for i, (x, y) in enumerate(((-80, -128), (58, -160), (15, -108), (-93.2, -205))):
    add_light("POINT", (x, y, SEA_Z + (5.4 if i == 3 else 3.0)), 70,
              (1.0, 0.55, 0.20), f"BoatLamp{i}")

for i, (x, y, z) in enumerate(STAIR_LAMPS):
    add_light("POINT", (x, y, z), 500, (1.0, 0.58, 0.26), f"StairLamp{i}")
for i, (x, y, z) in enumerate(HOUSE_LIGHTS[::2]):
    add_light("POINT", (x, y, z), 170, (1.0, 0.56, 0.24), f"HillHouseLamp{i}")
for i, (x, y, z) in enumerate(LOWER_LAMPS[::2]):
    add_light("POINT", (x, y, z), 140, (1.0, 0.58, 0.26), f"LowerLamp{i}")
add_light("AREA", (0, -165, -2), 145000, (1.0, 0.62, 0.34), "HillWash",
          target=(0, -68, 8), size=125, size_y=50, shape="RECTANGLE")
add_light("AREA", (-220, -100, 2), 150000, (1.0, 0.50, 0.24), "HillRim",
          target=(0, -48, 10), size=75, size_y=38, shape="RECTANGLE")

add_light("SPOT", (-110, -75, 22), 40000, (1.0, 0.56, 0.26), "SideWarm",
          target=(0, -28, 24), spot_size=math.radians(46), blend=0.55)
add_light("SPOT", (120, -80, 18), 20000, (0.38, 0.58, 1.0), "SideCool",
          target=(0, -28, 26), spot_size=math.radians(42), blend=0.6)

add_light("POINT", (0, -35.0, 5.5), 220, (1.0, 0.62, 0.30), "PorticoGlow")
add_light("POINT", (0, -33.0, 10.5), 120, (1.0, 0.66, 0.34), "PorticoGlow2")

# ----------------------------------------------------------------------------
# cameras
# ----------------------------------------------------------------------------
def add_cam(name, loc, target, lens):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.sensor_fit = "AUTO"
    cam.clip_end = 20000.0
    ob = bpy.data.objects.new(name, cam)
    C_CAM.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


add_cam("CAM_Hero", (-130, -340, -9.0), (0, -20, 18), 45)
add_cam("CAM_Front", (-5, -330, -9.0), (0, 0, 20), 38)
add_cam("CAM_Close", (-75, -155, -9.0), (0, -25, 24), 42)
add_cam("CAM_East", (160, -270, -8.0), (0, 0, 22), 38)
scene.camera = bpy.data.objects["CAM_Hero"]

# ----------------------------------------------------------------------------
# render settings
# ----------------------------------------------------------------------------
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 160
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.015
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 6
scene.cycles.diffuse_bounces = 3
scene.cycles.glossy_bounces = 4
scene.cycles.transmission_bounces = 4
scene.cycles.transparent_max_bounces = 4
scene.cycles.caustics_reflective = False
scene.cycles.caustics_refractive = False
scene.cycles.sample_clamp_indirect = 4.0
scene.render.resolution_x = 1800
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
scene.render.use_persistent_data = True
scene.render.filepath = os.path.join(RENDERS, "hero_raw.png")
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.render.image_settings.color_depth = "16"

scene.view_settings.view_transform = "AgX"
try:
    scene.view_settings.look = "AgX - Medium High Contrast"
except Exception:
    scene.view_settings.look = "None"
scene.view_settings.exposure = 0.58
scene.view_settings.gamma = 1.0

scene.view_layers[0].use_pass_mist = True
world.mist_settings.start = 45.0
world.mist_settings.depth = 420.0
world.mist_settings.falloff = "QUADRATIC"

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "hagia_sophia_hill_v2.blend"))
print("SCENE BUILT:", len(bpy.data.objects), "objects")
print("dome top", DOME_TOP)
