# 3D-genAI-runner

3D生成AIモデルを Mac (Apple Silicon / MPS) および CUDA 環境で簡単に動かすためのスクリプト集です。

## 構成

```
3D-genAI-runner/
├── models/              # 各モデルのリポジトリ (submodule)
│   └── TripoSR/
├── scripts/             # モデルごとのセットアップ・実行スクリプト
│   └── tripo/
│       ├── setup_mac.sh
│       ├── setup_cuda.sh
│       └── run_tripo.py
└── tools/               # 共通ツール
    ├── open_in_blender.py
    └── open_in_blender.sh
```

## クローン

サブモジュールを含めてクローンしてください:

```bash
git clone --recursive https://github.com/TS0321/3D-genAI-runner.git
```

既にクローン済みの場合:

```bash
git submodule update --init --recursive
```

## 対応モデル

### TripoSR

画像1枚から3Dメッシュを生成するモデル。

#### セットアップ

```bash
# Mac (Apple Silicon)
./scripts/tripo/setup_mac.sh

# CUDA (Linux / WSL)
./scripts/tripo/setup_cuda.sh
```

#### 推論

```bash
# 頂点カラー付き .obj
python scripts/tripo/run_tripo.py image.png

# テクスチャ付き（.obj + texture.png）
python scripts/tripo/run_tripo.py image.png --bake-texture

# 出力先を指定
python scripts/tripo/run_tripo.py image.png --bake-texture --output-dir results/
```

#### オプション

| オプション | 説明 | デフォルト |
|---|---|---|
| `--bake-texture` | UV展開 + テクスチャ画像を生成 | なし（頂点カラー） |
| `--texture-resolution N` | テクスチャ解像度 | 2048 |
| `--mc-resolution N` | メッシュの精細度 | 256 |
| `--chunk-size N` | 評価チャンクサイズ（小さいほどVRAM節約） | 8192 |
| `--no-remove-bg` | 背景除去をスキップ | 自動除去 |
| `--output-dir DIR` | 出力先ディレクトリ | `output/` |

## 共通ツール

### Blender ビューア

生成した .obj ファイルを Blender で表示します（Blender 5.x 対応）:

```bash
./tools/open_in_blender.sh output/mesh.obj
```

## ライセンス

各モデルのライセンスに準じます。
