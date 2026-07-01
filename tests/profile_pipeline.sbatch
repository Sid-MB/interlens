#!/bin/bash
# [interp-refactor]: profile the captured-turn pipeline (generate vs tokenize/decode vs capture-forward vs offload variants).
#SBATCH --account=nlp
#SBATCH --partition=jag-standard
#SBATCH --gres=gpu:a6000:1
#SBATCH --mem=48G
#SBATCH --time=0:30:00
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

for M in qwen2.5-3b qwen3-8b; do
	echo "########## PROFILE $M ##########"
	uv run python -u -m tests.profile_pipeline --model "$M" --prompt-tokens 1024 --new-tokens 128 --reps 5 2>&1 || echo "EXIT=$?"
done
