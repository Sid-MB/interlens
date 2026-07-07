#!/bin/bash
# [implement: interlens API batch + OpenAI + benchmark example] — GPU smoke-run of the GSM8K benchmark example.
#SBATCH --job-name=ilx_gsm8k
#SBATCH --account=nlp
#SBATCH --partition=jag-standard
#SBATCH --gres=gpu:a6000:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=01:00:00
#SBATCH --output=/juice2/u/siddharth/ii_mats/libs/interlens/examples/logs/%x_%j.out
set -euo pipefail
cd /juice2/u/siddharth/ii_mats
source set-env.sh 2>/dev/null || true
export HF_HUB_CACHE=/nlp/scr/siddharth/hf_cache/hub
echo "INVOCATION: examples/gsm8k_benchmark_rollout.py $*"
./.venv/bin/python libs/interlens/examples/gsm8k_benchmark_rollout.py "$@"
