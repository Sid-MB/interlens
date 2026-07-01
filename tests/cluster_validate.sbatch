#!/bin/bash
# [complete-chat-harness]: GPU validation of the chat harness — full pytest (fast+slow) + multi-GPU driver.
#SBATCH --account=nlp
#SBATCH --partition=jag-standard
#SBATCH --gres=gpu:a6000:2
#SBATCH --mem=96G
#SBATCH --time=2:00:00
#SBATCH --output=logs/%j.out
#SBATCH --error=logs/%j.err
set -e
export HF_HOME="$LARGE_ARTIFACTS_DIR/hf_cache"
export HF_HUB_CACHE="$LARGE_ARTIFACTS_DIR/hf_cache/hub"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
cd "$SLURM_SUBMIT_DIR/.."   # submit from experiments/ -> repo root
echo "host=$(hostname) job=$SLURM_JOB_ID cuda=$CUDA_VISIBLE_DEVICES"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true

RUN_DIR="$LARGE_ARTIFACTS_DIR/ii_mats/chat_harness/validate_${SLURM_JOB_ID}"
mkdir -p "$RUN_DIR"
echo "=== artifacts: $RUN_DIR ==="

echo "########## FAST + SLOW PYTEST ##########"
uv run pytest tests/ -m 'slow or not slow' -q 2>&1 || echo "PYTEST_EXIT=$?"

echo "########## MULTI-GPU DRIVER ##########"
uv run python -u -m tests.cluster_validate "$RUN_DIR/rollout" 2>&1
echo "EXIT_CODE=$?"
