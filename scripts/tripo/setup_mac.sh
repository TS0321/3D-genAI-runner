#!/bin/bash
set -e

echo "======================================"
echo " TripoSR Setup for Apple Silicon Mac"
echo "======================================"

# ----------------------------------------
# 1. pyenv / pyenv-virtualenv のインストール
# ----------------------------------------
if ! command -v pyenv &> /dev/null; then
    echo "[1/6] pyenv をインストール中..."
    brew install pyenv pyenv-virtualenv

    # シェル設定に pyenv の初期化を追加（まだ無い場合）
    SHELL_RC="$HOME/.zshrc"
    if ! grep -q 'pyenv init' "$SHELL_RC" 2>/dev/null; then
        cat >> "$SHELL_RC" << 'PYENV_INIT'

# pyenv
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
PYENV_INIT
        echo "  -> .zshrc に pyenv 初期化を追加しました"
    fi
else
    echo "[1/6] pyenv は既にインストール済みです"
fi

# 現在のシェルで pyenv を有効化
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

# ----------------------------------------
# 2. Python 3.10 のインストール
# ----------------------------------------
PYTHON_VERSION="3.10.16"

if ! pyenv versions --bare | grep -q "^${PYTHON_VERSION}$"; then
    echo "[2/6] Python ${PYTHON_VERSION} をインストール中..."
    pyenv install "${PYTHON_VERSION}"
else
    echo "[2/6] Python ${PYTHON_VERSION} は既にインストール済みです"
fi

# ----------------------------------------
# 3. 仮想環境 tripo_env の作成
# ----------------------------------------
if ! pyenv versions --bare | grep -q "tripo_env"; then
    echo "[3/6] 仮想環境 tripo_env を作成中..."
    pyenv virtualenv "${PYTHON_VERSION}" tripo_env
else
    echo "[3/6] 仮想環境 tripo_env は既に存在します"
fi

# このディレクトリで tripo_env を有効化
cd "$(dirname "$0")"
pyenv local tripo_env
echo "  -> pyenv local tripo_env を設定しました"

# ----------------------------------------
# 3.5. ビルドツールのインストール (cmake, ninja)
# ----------------------------------------
echo "  ビルドツールを確認中..."
if ! command -v cmake &> /dev/null; then
    echo "  cmake をインストール中..."
    brew install cmake
fi
if ! command -v ninja &> /dev/null; then
    echo "  ninja をインストール中..."
    brew install ninja
fi

# ----------------------------------------
# 4. TripoSR リポジトリのクローン
# ----------------------------------------
if [ ! -d "TripoSR" ]; then
    echo "[4/6] TripoSR リポジトリをクローン中..."
    git clone https://github.com/VAST-AI-Research/TripoSR.git
else
    echo "[4/6] TripoSR ディレクトリは既に存在します（スキップ）"
fi

# ----------------------------------------
# 5. PyTorch のインストール（Apple Silicon MPS 対応）
# ----------------------------------------
echo "[5/6] PyTorch をインストール中（MPS バックエンド対応）..."
pip install --upgrade pip
pip install torch torchvision torchaudio

# MPS が使えるか確認
python -c "
import torch
print(f'  PyTorch version: {torch.__version__}')
print(f'  MPS available:   {torch.backends.mps.is_available()}')
print(f'  MPS built:       {torch.backends.mps.is_built()}')
"

# ----------------------------------------
# 6. 依存ライブラリのインストール
# ----------------------------------------
echo "[6/6] 依存ライブラリをインストール中..."

# torchmcubes は Mac で C++ ビルドが困難な場合があるため個別対応
pip install omegaconf==2.3.0
pip install Pillow==10.1.0
pip install einops==0.7.0
pip install transformers==4.35.0
pip install trimesh>=4.6.0
pip install rembg onnxruntime
pip install huggingface-hub
pip install "imageio[ffmpeg]"
pip install xatlas
pip install moderngl==5.10.0

# PyMCubes（torchmcubes のフォールバック用に常にインストール）
pip install PyMCubes

# torchmcubes のインストール（ビルドに失敗しても続行）
echo "  torchmcubes をインストール中..."
if pip install git+https://github.com/tatsy/torchmcubes.git 2>/dev/null; then
    echo "  -> torchmcubes インストール成功"
else
    echo "  [WARNING] torchmcubes のビルドに失敗しました。PyMCubes を使用します。"
fi

echo ""
echo "======================================"
echo " セットアップ完了!"
echo "======================================"
echo ""
echo "使い方:"
echo "  1. テスト画像を用意してください（例: test.png）"
echo "  2. 以下のコマンドで推論を実行:"
echo "     python run_tripo.py test.png"
echo "  3. 結果は output/ ディレクトリに .obj ファイルとして保存されます"
echo ""
