#!/bin/bash
# [complete-chat-harness]: attempt to install flash-attn into the uv env (heavy source build; torch 2.12+cu130 is new).
#SBATCH --account=nlp
#SBATCH --partition=jag-standard
#SBATCH --gres=gpu:a6000:1
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --time=3:00:00
#SBATCH --output=logs/%j.out
#SBATCH --error=logs/%j.err
set -e
export HF_HOME="$LARGE_ARTIFACTS_DIR/hf_cache"
cd "$SLURM_SUBMIT_DIR/.."
echo "host=$(hostname) cuda=$CUDA_VISIBLE_DEVICES"
nvcc --version 2>&1 | tail -2 || echo "no nvcc"
export MAX_JOBS=8
echo "=== trying prebuilt wheel first ==="
uv pip install flash-attn --no-build-isolation 2>&1 | tail -30 || echo "INSTALL_FAILED=$?"
echo "=== verify ==="
uv run python -c "import flash_attn; print('flash_attn', flash_attn.__version__)" 2>&1 | tail -3
echo "DONE"
