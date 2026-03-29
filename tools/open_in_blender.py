"""
Blender起動後に自動実行されるインポートスクリプト
使い方: blender --python open_in_blender.py -- /path/to/mesh.obj
"""
import bpy
import math
import mathutils
import os
import sys

# -- 以降の引数を取得
argv = sys.argv
argv = argv[argv.index("--") + 1:]
obj_path = argv[0]

# デフォルトオブジェクト（Cube, Light, Camera）を削除
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete()

# OBJ インポート
bpy.ops.wm.obj_import(filepath=obj_path)

imported = [o for o in bpy.data.objects if o.type == "MESH"]
if not imported:
    print("ERROR: メッシュが見つかりません")
    sys.exit(1)

obj = imported[0]

# 10倍スケール
obj.scale = (10, 10, 10)
bpy.context.view_layer.update()

# 原点をジオメトリの中心に
bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
obj.location = (0, 0, 0)
bpy.context.view_layer.update()

# ライト追加
bpy.ops.object.light_add(type="SUN", location=(5, 5, 10))
bpy.context.object.data.energy = 3.0
bpy.ops.object.light_add(type="SUN", location=(-5, -3, 8))
bpy.context.object.data.energy = 1.5

# テクスチャファイルがあればマテリアルを設定
texture_path = os.path.join(os.path.dirname(obj_path), "texture.png")
if os.path.exists(texture_path) and not obj.data.materials:
    mat = bpy.data.materials.new(name="TripoSR_Material")
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    tex_node = nodes.new("ShaderNodeTexImage")
    tex_node.image = bpy.data.images.load(texture_path)
    links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
    obj.data.materials.append(mat)
    print(f"テクスチャを適用: {texture_path}")

# 3D Viewport 設定
for area in bpy.context.screen.areas:
    if area.type == "VIEW_3D":
        space = area.spaces[0]
        space.clip_start = 0.01
        space.clip_end = 1000
        space.shading.type = "MATERIAL"

        # ビュー位置を直接指定（斜め前から見る）
        r3d = space.region_3d
        r3d.view_location = mathutils.Vector((0, 0, 0))
        r3d.view_distance = 12.0
        r3d.view_rotation = mathutils.Euler(
            (math.radians(60), 0, math.radians(45))
        ).to_quaternion()
        break

# メッシュを再選択
bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj

dims = tuple(round(d, 2) for d in obj.dimensions)
print(f"読み込み完了: {obj.name} ({len(obj.data.vertices)} vertices, size={dims})")
