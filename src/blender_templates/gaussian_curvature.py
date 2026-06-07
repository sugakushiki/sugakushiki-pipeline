"""
gaussian_curvature.py — Blender template for Theorema Egregium visualization

Renders 3D surfaces colored by Gaussian curvature to demonstrate
Gauss's Theorema Egregium: curvature is an intrinsic property of a surface.

Modes:
    sphere       - Positive curvature (sphere). Uniform warm color.
    saddle       - Negative curvature (saddle/hyperbolic paraboloid).
    flat         - Zero curvature (plane and cylinder).
    deformation  - Bending a surface without stretching: curvature preserved.
    map_projection - Sphere flattening attempt showing distortion.

Parameters (from _blender_params.json):
    mode: str        - One of the modes above
    duration: float  - Target video duration in seconds
    width: int       - Output width (1920)
    height: int      - Output height (1080)
    fps: int         - Frames per second (30)
    output_path: str - Output MP4 path

Runs in Blender --background mode (headless).
Uses Eevee renderer for CPU-friendly performance.

Used by: Episode 010 (Gauss) — Pillar 4
"""

import json
import math
import os
import sys

# ---------------------------------------------------------------------------
# Load parameters
# ---------------------------------------------------------------------------
PARAMS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "_blender_params.json")

def load_params():
    if os.path.exists(PARAMS_FILE):
        with open(PARAMS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


params = load_params()
MODE = params.get("mode", "sphere")
DURATION = params.get("duration", 12)
WIDTH = params.get("width", 1920)
HEIGHT = params.get("height", 1080)
FPS = params.get("fps", 30)
OUTPUT_PATH = params.get("output_path", "gaussian_curvature_output.mp4")

# ---------------------------------------------------------------------------
# Blender imports (only available inside Blender)
# ---------------------------------------------------------------------------
try:
    import bpy
    import bmesh
    from mathutils import Vector, Color
except ImportError:
    print("[gaussian_curvature] Not running inside Blender. Exiting.")
    sys.exit(0)


# ---------------------------------------------------------------------------
# Colors matching style.py
# ---------------------------------------------------------------------------
BG_COLOR = (0x1A / 255, 0x1A / 255, 0x2E / 255, 1.0)  # #1a1a2e
GOLD = (0xE2 / 255, 0xB7 / 255, 0x14 / 255, 1.0)       # #e2b714
CYAN = (0x4C / 255, 0xC9 / 255, 0xF0 / 255, 1.0)       # #4cc9f0
PINK = (0xF7 / 255, 0x25 / 255, 0x85 / 255, 1.0)       # #f72585
WHITE = (1.0, 1.0, 1.0, 1.0)

# Curvature color map: negative=PINK, zero=WHITE, positive=GOLD
CURV_NEGATIVE = (PINK[0], PINK[1], PINK[2])
CURV_ZERO = (0.85, 0.85, 0.92)
CURV_POSITIVE = (GOLD[0], GOLD[1], GOLD[2])


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------
def cleanup_scene():
    """Remove all default objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def setup_render():
    """Configure Eevee render settings for CPU rendering."""
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = int(DURATION * FPS)

    # Eevee settings (low samples for CPU-only rendering)
    scene.eevee.taa_render_samples = 8

    # Background color
    scene.world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg_node = scene.world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs[0].default_value = BG_COLOR

    # Output settings
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
    scene.render.ffmpeg.audio_codec = 'NONE'
    scene.render.filepath = OUTPUT_PATH


def setup_camera(location=(0, -6, 3), target=(0, 0, 0)):
    """Set up camera looking at target."""
    bpy.ops.object.camera_add(location=location)
    cam = bpy.context.object
    cam.name = "Camera"
    bpy.context.scene.camera = cam

    # Point camera at target
    direction = Vector(target) - Vector(location)
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam.rotation_euler = rot_quat.to_euler()

    return cam


def setup_lighting():
    """Set up three-point lighting."""
    # Key light
    bpy.ops.object.light_add(type='SUN', location=(3, -3, 5))
    key = bpy.context.object
    key.data.energy = 3.0
    key.data.color = (1.0, 0.95, 0.9)

    # Fill light
    bpy.ops.object.light_add(type='SUN', location=(-3, -2, 3))
    fill = bpy.context.object
    fill.data.energy = 1.5
    fill.data.color = (0.8, 0.85, 1.0)


def add_title_text(text, location=(0, 0, 2.5), size=0.3, color=GOLD):
    """Add 3D text overlay."""
    bpy.ops.object.text_add(location=location)
    txt = bpy.context.object
    txt.data.body = text
    txt.data.size = size
    txt.data.align_x = 'CENTER'

    # Material
    mat = bpy.data.materials.new("TitleMat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Emission Color"].default_value = color
        bsdf.inputs["Emission Strength"].default_value = 2.0
    txt.data.materials.append(mat)

    return txt


def curvature_color(k):
    """Map curvature value to RGB color."""
    if k > 0.01:
        t = min(k / 0.5, 1.0)
        return tuple(CURV_ZERO[i] * (1 - t) + CURV_POSITIVE[i] * t for i in range(3))
    elif k < -0.01:
        t = min(-k / 0.5, 1.0)
        return tuple(CURV_ZERO[i] * (1 - t) + CURV_NEGATIVE[i] * t for i in range(3))
    else:
        return CURV_ZERO


def create_curvature_material(name, color):
    """Create a simple colored material."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.4
        bsdf.inputs["Metallic"].default_value = 0.1
    return mat


def add_slow_rotation(obj, total_frames, axis='Z', degrees=60):
    """Add slow rotation animation to an object."""
    obj.rotation_euler = (0, 0, 0)
    obj.keyframe_insert(data_path="rotation_euler", frame=1)

    rad = math.radians(degrees)
    if axis == 'Z':
        obj.rotation_euler = (0, 0, rad)
    elif axis == 'X':
        obj.rotation_euler = (rad, 0, 0)
    elif axis == 'Y':
        obj.rotation_euler = (0, rad, 0)
    obj.keyframe_insert(data_path="rotation_euler", frame=total_frames)


# ---------------------------------------------------------------------------
# Mode builders
# ---------------------------------------------------------------------------
def build_sphere():
    """Positive curvature: colored sphere."""
    total_frames = int(DURATION * FPS)

    title = add_title_text("Positive curvature  K > 0", size=0.25)
    title.location = (0, 0, 2.8)

    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.5, segments=64, ring_count=32,
                                          location=(0, 0, 0))
    sphere = bpy.context.object
    mat = create_curvature_material("SphereMat", CURV_POSITIVE)
    sphere.data.materials.append(mat)

    # Curvature label
    label = add_title_text("K = 1/r\u00b2", location=(0, 0, -2.2), size=0.2,
                           color=GOLD)

    add_slow_rotation(sphere, total_frames, degrees=45)


def build_saddle():
    """Negative curvature: hyperbolic paraboloid."""
    total_frames = int(DURATION * FPS)

    title = add_title_text("Negative curvature  K < 0", size=0.25)
    title.location = (0, 0, 2.8)

    # Create mesh grid for z = x^2 - y^2
    verts = []
    faces = []
    n = 40
    scale = 2.0
    for i in range(n + 1):
        for j in range(n + 1):
            x = (i / n - 0.5) * scale * 2
            y = (j / n - 0.5) * scale * 2
            z = 0.3 * (x * x - y * y)
            verts.append((x, y, z))

    for i in range(n):
        for j in range(n):
            v0 = i * (n + 1) + j
            v1 = v0 + 1
            v2 = v0 + (n + 1) + 1
            v3 = v0 + (n + 1)
            faces.append((v0, v1, v2, v3))

    mesh = bpy.data.meshes.new("SaddleMesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("Saddle", mesh)
    bpy.context.collection.objects.link(obj)

    mat = create_curvature_material("SaddleMat", CURV_NEGATIVE)
    obj.data.materials.append(mat)

    # Smooth shading
    for poly in obj.data.polygons:
        poly.use_smooth = True

    add_slow_rotation(obj, total_frames, degrees=45)

    label = add_title_text("K < 0", location=(0, 0, -2.2), size=0.2,
                           color=PINK)


def build_flat():
    """Zero curvature: plane and cylinder side by side."""
    total_frames = int(DURATION * FPS)

    title = add_title_text("Zero curvature  K = 0", size=0.25)
    title.location = (0, 0, 2.8)

    # Plane
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=(-1.8, 0, 0))
    plane = bpy.context.object
    mat_flat = create_curvature_material("FlatMat", CURV_ZERO)
    plane.data.materials.append(mat_flat)

    plane_label = add_title_text("Plane", location=(-1.8, 0, -1.5), size=0.18,
                                 color=WHITE)

    # Cylinder
    bpy.ops.mesh.primitive_cylinder_add(radius=0.7, depth=2.0, location=(1.8, 0, 0),
                                         vertices=64)
    cyl = bpy.context.object
    cyl.rotation_euler = (math.radians(90), 0, 0)
    cyl.data.materials.append(mat_flat)

    cyl_label = add_title_text("Cylinder", location=(1.8, 0, -1.5), size=0.18,
                               color=WHITE)

    add_slow_rotation(cyl, total_frames, axis='Z', degrees=30)

    note = add_title_text("Cylinder = bent plane (same K)",
                          location=(0, 0, -2.2), size=0.15, color=CYAN)


def build_deformation():
    """Bending without stretching: curvature is preserved."""
    total_frames = int(DURATION * FPS)

    title = add_title_text("Theorema Egregium", size=0.28)
    title.location = (0, 0, 2.8)

    subtitle = add_title_text("Bending preserves curvature",
                              location=(0, 0, 2.3), size=0.15, color=CYAN)

    # Create a flat sheet that bends into a cylinder over time
    n = 30
    verts_flat = []
    faces = []
    for i in range(n + 1):
        for j in range(n + 1):
            x = (i / n - 0.5) * 3.0
            y = (j / n - 0.5) * 2.0
            verts_flat.append((x, y, 0))

    for i in range(n):
        for j in range(n):
            v0 = i * (n + 1) + j
            v1 = v0 + 1
            v2 = v0 + (n + 1) + 1
            v3 = v0 + (n + 1)
            faces.append((v0, v1, v2, v3))

    mesh = bpy.data.meshes.new("SheetMesh")
    mesh.from_pydata(verts_flat, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("Sheet", mesh)
    bpy.context.collection.objects.link(obj)

    mat = create_curvature_material("SheetMat", CURV_ZERO)
    obj.data.materials.append(mat)

    for poly in obj.data.polygons:
        poly.use_smooth = True

    # Animate bending using shape keys
    # Basis = flat
    obj.shape_key_add(name="Basis")

    # Key 1 = bent into half-cylinder
    sk = obj.shape_key_add(name="Bent")
    radius = 1.5
    for idx, v in enumerate(verts_flat):
        x, y, z = v
        # Bend the x-axis around a cylinder of given radius
        angle = x / radius
        new_x = radius * math.sin(angle)
        new_z = radius * (1 - math.cos(angle))
        sk.data[idx].co = Vector((new_x, y, new_z - 0.5))

    # Animate shape key
    sk.value = 0.0
    sk.keyframe_insert(data_path="value", frame=1)
    mid_frame = total_frames // 2
    sk.value = 1.0
    sk.keyframe_insert(data_path="value", frame=mid_frame)
    sk.value = 1.0
    sk.keyframe_insert(data_path="value", frame=total_frames)

    # K = 0 label stays constant
    k_label = add_title_text("K = 0  (unchanged)",
                             location=(0, 0, -2.2), size=0.18, color=GOLD)


def build_map_projection():
    """Sphere → flat: distortion is inevitable."""
    total_frames = int(DURATION * FPS)

    title = add_title_text("Why perfect maps are impossible", size=0.22)
    title.location = (0, 0, 2.8)

    # Sphere (earth-like)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.2, segments=48, ring_count=24,
                                          location=(-2.0, 0, 0))
    sphere = bpy.context.object
    sphere_mat = create_curvature_material("EarthMat", CURV_POSITIVE)
    sphere.data.materials.append(sphere_mat)

    # Add wireframe modifier for grid lines
    mod = sphere.modifiers.new("Wire", 'WIREFRAME')
    mod.thickness = 0.01
    mod.use_replace = False

    sphere_label = add_title_text("K > 0", location=(-2.0, 0, -1.8), size=0.18,
                                  color=GOLD)

    # Arrow
    arrow_text = add_title_text("-->", location=(0, 0, 0), size=0.3,
                                color=WHITE)

    # Flat projection (stretched plane)
    bpy.ops.mesh.primitive_plane_add(size=2.4, location=(2.0, 0, 0))
    plane = bpy.context.object
    plane_mat = create_curvature_material("MapMat", CURV_ZERO)
    plane.data.materials.append(plane_mat)

    # Add grid lines via wireframe
    mod2 = plane.modifiers.new("Wire", 'WIREFRAME')
    mod2.thickness = 0.01
    mod2.use_replace = False

    plane_label = add_title_text("K = 0", location=(2.0, 0, -1.8), size=0.18,
                                 color=PINK)

    # Distortion note
    note = add_title_text("K > 0 cannot become K = 0 without distortion",
                          location=(0, 0, -2.2), size=0.14, color=PINK)

    add_slow_rotation(sphere, total_frames, degrees=30)


# ---------------------------------------------------------------------------
# Main dispatch
# ---------------------------------------------------------------------------
def main():
    cleanup_scene()
    setup_render()
    setup_camera()
    setup_lighting()

    if MODE == "saddle":
        build_saddle()
    elif MODE == "flat":
        build_flat()
    elif MODE == "deformation":
        build_deformation()
    elif MODE == "map_projection":
        build_map_projection()
    else:
        build_sphere()

    # Render animation
    print(f"[gaussian_curvature] Rendering mode={MODE}, {DURATION}s, {WIDTH}x{HEIGHT}@{FPS}fps")
    print(f"[gaussian_curvature] Output: {OUTPUT_PATH}")
    bpy.ops.render.render(animation=True)
    print(f"[gaussian_curvature] Render complete.")


if __name__ == "__main__":
    main()
