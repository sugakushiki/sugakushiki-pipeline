"""
gaussian_curvature_v2.py — Theorema Egregium visualization v2

Redesigned for visual impact:
- Paper rolling into cylinder (curvature stays 0)
- Sphere that resists flattening
- Globe "peeling" onto flat surface with distortion

No 3D text overlays. Clean materials with environment lighting.

Modes:
    paper_to_cylinder - Flat paper rolls into cylinder, color stays blue (K=0)
    globe_peel        - Globe surface peels flat, grid distorts and turns pink

Used by: Episode 010 (Gauss) — Pillar 4 benchmark
"""

import json
import math
import os
import sys

PARAMS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "_blender_params.json")

def load_params():
    if os.path.exists(PARAMS_FILE):
        with open(PARAMS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

params = load_params()
MODE = params.get("mode", "paper_to_cylinder")
DURATION = params.get("duration", 5)
WIDTH = params.get("width", 1280)
HEIGHT = params.get("height", 720)
FPS = params.get("fps", 24)
OUTPUT_PATH = params.get("output_path", "gaussian_curvature_v2_output.mp4")

try:
    import bpy
    import bmesh
    from mathutils import Vector, Color
except ImportError:
    print("[gaussian_curvature_v2] Not running inside Blender. Exiting.")
    sys.exit(0)

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
BG_COLOR = (0.05, 0.05, 0.12, 1.0)  # Deeper dark blue
GOLD = (0.89, 0.72, 0.08)
CYAN_SOFT = (0.35, 0.70, 0.88)
PINK = (0.92, 0.18, 0.45)
WHITE_WARM = (0.95, 0.93, 0.88)


def cleanup_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    # Remove orphan data
    for mesh in bpy.data.meshes:
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        if mat.users == 0:
            bpy.data.materials.remove(mat)


def setup_render():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = int(DURATION * FPS)

    scene.eevee.taa_render_samples = 8

    # World: gradient background
    scene.world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    nodes = scene.world.node_tree.nodes
    links = scene.world.node_tree.links
    nodes.clear()

    bg = nodes.new('ShaderNodeBackground')
    bg.inputs[0].default_value = BG_COLOR
    bg.inputs[1].default_value = 1.0  # strength

    output = nodes.new('ShaderNodeOutputWorld')
    links.new(bg.outputs[0], output.inputs[0])

    # Output
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
    scene.render.ffmpeg.audio_codec = 'NONE'
    scene.render.filepath = OUTPUT_PATH


def setup_camera(location=(0, -5.5, 2.5), target=(0, 0, 0)):
    bpy.ops.object.camera_add(location=location)
    cam = bpy.context.object
    cam.name = "Camera"
    bpy.context.scene.camera = cam
    direction = Vector(target) - Vector(location)
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam.rotation_euler = rot_quat.to_euler()
    cam.data.lens = 50
    return cam


def setup_lighting():
    # Key light - warm
    bpy.ops.object.light_add(type='AREA', location=(3, -2, 4))
    key = bpy.context.object
    key.data.energy = 150
    key.data.color = (1.0, 0.95, 0.85)
    key.data.size = 3.0
    key.rotation_euler = (math.radians(45), 0, math.radians(30))

    # Fill light - cool
    bpy.ops.object.light_add(type='AREA', location=(-3, -1, 3))
    fill = bpy.context.object
    fill.data.energy = 80
    fill.data.color = (0.75, 0.85, 1.0)
    fill.data.size = 4.0
    fill.rotation_euler = (math.radians(50), 0, math.radians(-40))

    # Rim light
    bpy.ops.object.light_add(type='AREA', location=(0, 3, 2))
    rim = bpy.context.object
    rim.data.energy = 60
    rim.data.color = (0.9, 0.9, 1.0)
    rim.data.size = 2.0
    rim.rotation_euler = (math.radians(120), 0, 0)


def create_material(name, base_color, roughness=0.35, metallic=0.0,
                    emission_color=None, emission_strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*base_color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        if emission_color:
            bsdf.inputs["Emission Color"].default_value = (*emission_color, 1.0)
            bsdf.inputs["Emission Strength"].default_value = emission_strength
    return mat


# ---------------------------------------------------------------------------
# Mode: paper_to_cylinder
# ---------------------------------------------------------------------------
def build_paper_to_cylinder():
    total_frames = int(DURATION * FPS)

    # Create subdivided plane (the "paper")
    n = 40
    size = 3.0
    verts = []
    faces = []
    for i in range(n + 1):
        for j in range(n + 1):
            x = (i / n - 0.5) * size
            y = (j / n - 0.5) * size * 0.7  # slightly rectangular
            verts.append((x, y, 0))

    for i in range(n):
        for j in range(n):
            v0 = i * (n + 1) + j
            v1 = v0 + 1
            v2 = v0 + (n + 1) + 1
            v3 = v0 + (n + 1)
            faces.append((v0, v1, v2, v3))

    mesh = bpy.data.meshes.new("PaperMesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("Paper", mesh)
    bpy.context.collection.objects.link(obj)

    # Material: soft cyan (K=0)
    mat = create_material("PaperMat", CYAN_SOFT, roughness=0.5,
                          emission_color=CYAN_SOFT, emission_strength=0.15)
    obj.data.materials.append(mat)

    for poly in obj.data.polygons:
        poly.use_smooth = True

    # Shape key: flat (basis)
    obj.shape_key_add(name="Basis")

    # Shape key: cylinder
    radius = 1.2
    sk = obj.shape_key_add(name="Cylinder")
    for idx, v in enumerate(verts):
        x, y, z = v
        angle = x / radius
        new_x = radius * math.sin(angle)
        new_z = radius * (1 - math.cos(angle))
        sk.data[idx].co = Vector((new_x, y, new_z))

    # Animate: flat -> cylinder in first 60%, hold 40%
    bend_end = int(total_frames * 0.6)
    sk.value = 0.0
    sk.keyframe_insert(data_path="value", frame=1)
    sk.value = 1.0
    sk.keyframe_insert(data_path="value", frame=bend_end)
    sk.value = 1.0
    sk.keyframe_insert(data_path="value", frame=total_frames)

    # Smooth interpolation
    if sk.id_data.animation_data:
        for fc in sk.id_data.animation_data.action.fcurves:
            for kf in fc.keyframe_points:
                kf.interpolation = 'BEZIER'

    # Camera orbit: slow rotation during hold
    cam = bpy.context.scene.camera
    cam.location = (0, -5, 2.5)
    cam.keyframe_insert(data_path="location", frame=1)
    cam.location = (2, -4.5, 2.5)
    cam.keyframe_insert(data_path="location", frame=total_frames)

    # Re-point camera
    for frame in [1, total_frames]:
        bpy.context.scene.frame_set(frame)
        direction = Vector((0, 0, 0.3)) - Vector(cam.location)
        rot_quat = direction.to_track_quat('-Z', 'Y')
        cam.rotation_euler = rot_quat.to_euler()
        cam.keyframe_insert(data_path="rotation_euler", frame=frame)


# ---------------------------------------------------------------------------
# Mode: globe_peel
# ---------------------------------------------------------------------------
def build_globe_peel():
    total_frames = int(DURATION * FPS)

    # Create UV sphere with grid lines via wireframe
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=1.5, segments=32, ring_count=16, location=(0, 0, 0))
    sphere = bpy.context.object
    sphere.name = "Globe"

    # Gold material
    mat_sphere = create_material("GlobeMat", GOLD, roughness=0.3, metallic=0.15,
                                 emission_color=GOLD, emission_strength=0.1)
    sphere.data.materials.append(mat_sphere)

    for poly in sphere.data.polygons:
        poly.use_smooth = True

    # Wireframe overlay for grid lines
    mod = sphere.modifiers.new("Wire", 'WIREFRAME')
    mod.thickness = 0.015
    mod.use_replace = False

    # Create a flat "target" plane (where the map goes)
    bpy.ops.mesh.primitive_plane_add(size=4.0, location=(0, 0, -2.2))
    plane = bpy.context.object
    plane.name = "MapTarget"

    # Pink-tinted material for the distorted map
    mat_plane = create_material("MapMat", PINK, roughness=0.5,
                                emission_color=PINK, emission_strength=0.08)
    plane.data.materials.append(mat_plane)
    plane.scale = (1.0, 0.6, 1.0)

    # Animate sphere: squeeze vertically (can't flatten without distortion)
    sphere.scale = (1.0, 1.0, 1.0)
    sphere.keyframe_insert(data_path="scale", frame=1)

    squash_frame = int(total_frames * 0.5)
    sphere.scale = (1.4, 1.4, 0.5)  # squash
    sphere.keyframe_insert(data_path="scale", frame=squash_frame)

    # Bounce back slightly (it resists)
    end_frame = int(total_frames * 0.7)
    sphere.scale = (1.15, 1.15, 0.8)
    sphere.keyframe_insert(data_path="scale", frame=end_frame)

    sphere.scale = (1.15, 1.15, 0.8)
    sphere.keyframe_insert(data_path="scale", frame=total_frames)

    # Slow rotation
    sphere.rotation_euler = (0, 0, 0)
    sphere.keyframe_insert(data_path="rotation_euler", frame=1)
    sphere.rotation_euler = (0, 0, math.radians(30))
    sphere.keyframe_insert(data_path="rotation_euler", frame=total_frames)

    # Camera
    cam = bpy.context.scene.camera
    cam.location = (3, -4.5, 3)
    direction = Vector((0, 0, -0.3)) - Vector(cam.location)
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam.rotation_euler = rot_quat.to_euler()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    cleanup_scene()
    setup_render()
    setup_camera()
    setup_lighting()

    if MODE == "globe_peel":
        build_globe_peel()
    else:
        build_paper_to_cylinder()

    print(f"[gaussian_curvature_v2] mode={MODE}, {DURATION}s, {WIDTH}x{HEIGHT}@{FPS}fps")
    bpy.ops.render.render(animation=True)
    print(f"[gaussian_curvature_v2] Render complete.")


if __name__ == "__main__":
    main()
