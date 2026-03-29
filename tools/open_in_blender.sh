#!/bin/bash
# 指定した 3D ファイル（OBJ / GLB）を Blender で開くスクリプト
# 使い方: ./open_in_blender.sh output/mesh.obj
#         ./open_in_blender.sh output/mesh.glb

OBJ_PATH="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -f "$OBJ_PATH" ]; then
    echo "エラー: ファイルが見つかりません: $1"
    exit 1
fi

echo "Blender で ${OBJ_PATH} を開いています..."
blender --python "$SCRIPT_DIR/open_in_blender.py" -- "$OBJ_PATH"
