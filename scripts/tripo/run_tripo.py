"""
TripoSR 推論スクリプト (Apple Silicon MPS 対応)

使い方:
    python run_tripo.py <画像ファイルパス> [--output-dir OUTPUT_DIR] [--mc-resolution 256]

例:
    python run_tripo.py test.png
    python run_tripo.py photo.jpg --output-dir results/
"""

import argparse
import logging
import os
import sys
import time
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

import numpy as np
import torch
from PIL import Image

# TripoSR のモジュールパスを追加
TRIPOSR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "models", "TripoSR")
if TRIPOSR_DIR not in sys.path:
    sys.path.insert(0, TRIPOSR_DIR)

from tsr.system import TSR
from tsr.utils import remove_background, resize_foreground
from tsr.bake_texture import bake_texture


logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def select_device() -> str:
    """利用可能な最適なデバイスを自動選択する"""
    if torch.backends.mps.is_available() and torch.backends.mps.is_built():
        logger.info("Apple Silicon MPS デバイスを使用します")
        return "mps"
    elif torch.cuda.is_available():
        logger.info("CUDA デバイスを使用します")
        return "cuda:0"
    else:
        logger.info("CPU を使用します（GPU が見つかりません）")
        return "cpu"


def preprocess_image(image_path: str, foreground_ratio: float = 0.85) -> Image.Image:
    """画像を読み込み、背景除去と前景リサイズを行う"""
    import rembg

    logger.info(f"画像を読み込み中: {image_path}")
    image = Image.open(image_path)

    logger.info("背景を除去中...")
    session = rembg.new_session()
    image = remove_background(image, session)
    image = resize_foreground(image, foreground_ratio)

    # RGBA -> RGB (グレー背景に合成)
    image = np.array(image).astype(np.float32) / 255.0
    image = image[:, :, :3] * image[:, :, 3:4] + (1 - image[:, :, 3:4]) * 0.5
    image = Image.fromarray((image * 255.0).astype(np.uint8))

    return image


def run_inference(
    image_path: str,
    output_dir: str = "output",
    mc_resolution: int = 256,
    chunk_size: int = 8192,
    model_name: str = "stabilityai/TripoSR",
    no_remove_bg: bool = False,
    foreground_ratio: float = 0.85,
    bake: bool = False,
    texture_resolution: int = 2048,
    output_format: str = "obj",
):
    """TripoSR による 3D メッシュ生成を実行する"""
    os.makedirs(output_dir, exist_ok=True)
    device = select_device()

    # --- モデルの読み込み ---
    t0 = time.time()
    logger.info("TripoSR モデルを読み込み中...")
    model = TSR.from_pretrained(
        model_name,
        config_name="config.yaml",
        weight_name="model.ckpt",
    )
    model.renderer.set_chunk_size(chunk_size)
    model.to(device)
    logger.info(f"モデル読み込み完了 ({time.time() - t0:.1f}秒)")

    # --- 画像の前処理 ---
    t1 = time.time()
    if no_remove_bg:
        image = Image.open(image_path).convert("RGB")
    else:
        image = preprocess_image(image_path, foreground_ratio)

    # 前処理済み画像を保存
    preprocessed_path = os.path.join(output_dir, "input_preprocessed.png")
    image.save(preprocessed_path)
    logger.info(f"前処理済み画像を保存: {preprocessed_path} ({time.time() - t1:.1f}秒)")

    # --- 推論 ---
    t2 = time.time()
    logger.info("3D 推論を実行中...")
    with torch.no_grad():
        scene_codes = model([image], device=device)
    logger.info(f"推論完了 ({time.time() - t2:.1f}秒)")

    # --- メッシュ抽出 ---
    t3 = time.time()
    logger.info("メッシュを抽出中...")
    # bake_texture 使用時は頂点カラー不要、未使用時は頂点カラーを付与
    meshes = model.extract_mesh(scene_codes, has_vertex_color=not bake, resolution=mc_resolution)
    logger.info(f"メッシュ抽出完了 ({time.time() - t3:.1f}秒)")

    ext = output_format.lower()
    output_path = os.path.join(output_dir, f"mesh.{ext}")

    if bake:
        import xatlas
        import trimesh

        # --- テクスチャベイク ---
        t4 = time.time()
        logger.info(f"テクスチャをベイク中 ({texture_resolution}x{texture_resolution})...")
        bake_output = bake_texture(meshes[0], model, scene_codes[0], texture_resolution)
        logger.info(f"テクスチャベイク完了 ({time.time() - t4:.1f}秒)")

        texture_image = Image.fromarray(
            (bake_output["colors"] * 255.0).astype(np.uint8)
        ).transpose(Image.FLIP_TOP_BOTTOM)

        if ext == "glb":
            # GLB: テクスチャを埋め込んだ単一ファイルとして出力
            material = trimesh.visual.material.PBRMaterial(
                baseColorTexture=texture_image,
            )
            uv_visual = trimesh.visual.TextureVisuals(
                uv=bake_output["uvs"],
                material=material,
            )
            textured_mesh = trimesh.Trimesh(
                vertices=meshes[0].vertices[bake_output["vmapping"]],
                faces=bake_output["indices"],
                vertex_normals=meshes[0].vertex_normals[bake_output["vmapping"]],
                visual=uv_visual,
            )
            textured_mesh.export(output_path)
        else:
            # OBJ: 従来通り .obj + .mtl + texture.png として出力
            xatlas.export(
                output_path,
                meshes[0].vertices[bake_output["vmapping"]],
                bake_output["indices"],
                bake_output["uvs"],
                meshes[0].vertex_normals[bake_output["vmapping"]],
            )
            texture_path = os.path.join(output_dir, "texture.png")
            texture_image.save(texture_path)
            logger.info(f"テクスチャを保存しました: {texture_path}")

            mtl_path = os.path.join(output_dir, "mesh.mtl")
            with open(mtl_path, "w") as f:
                f.write("newmtl material0\n")
                f.write("map_Kd texture.png\n")
            with open(output_path, "r") as f:
                obj_content = f.read()
            with open(output_path, "w") as f:
                f.write("mtllib mesh.mtl\n")
                f.write(obj_content)
            logger.info(f"マテリアルを保存しました: {mtl_path}")
    else:
        # --- 頂点カラー付き ---
        meshes[0].export(output_path)

    logger.info(f"メッシュを保存しました: {output_path}")

    total_time = time.time() - t0
    logger.info(f"全処理完了 (合計 {total_time:.1f}秒)")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="TripoSR: 画像から3Dメッシュを生成 (Apple Silicon MPS 対応)"
    )
    parser.add_argument("image", type=str, help="入力画像のパス")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="出力ディレクトリ (デフォルト: output/)",
    )
    parser.add_argument(
        "--mc-resolution",
        type=int,
        default=256,
        help="Marching Cubes の解像度 (デフォルト: 256)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=8192,
        help="評価チャンクサイズ。小さいほどVRAM節約 (デフォルト: 8192)",
    )
    parser.add_argument(
        "--no-remove-bg",
        action="store_true",
        help="背景除去をスキップする",
    )
    parser.add_argument(
        "--foreground-ratio",
        type=float,
        default=0.85,
        help="前景の比率 (デフォルト: 0.85)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="stabilityai/TripoSR",
        help="モデル名またはパス (デフォルト: stabilityai/TripoSR)",
    )
    parser.add_argument(
        "--bake-texture",
        action="store_true",
        help="テクスチャアトラスをベイクする (UV展開 + texture.png を生成)",
    )
    parser.add_argument(
        "--texture-resolution",
        type=int,
        default=2048,
        help="テクスチャ解像度 (デフォルト: 2048, --bake-texture 時のみ有効)",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["obj", "glb"],
        default="obj",
        help="出力フォーマット (デフォルト: obj)",
    )

    args = parser.parse_args()

    if not os.path.isfile(args.image):
        print(f"エラー: 画像ファイルが見つかりません: {args.image}")
        sys.exit(1)

    output_path = run_inference(
        image_path=args.image,
        output_dir=args.output_dir,
        mc_resolution=args.mc_resolution,
        chunk_size=args.chunk_size,
        model_name=args.model,
        no_remove_bg=args.no_remove_bg,
        foreground_ratio=args.foreground_ratio,
        bake=args.bake_texture,
        texture_resolution=args.texture_resolution,
        output_format=args.format,
    )

    print(f"\n完了! 出力ファイル: {output_path}")


if __name__ == "__main__":
    main()
