#!/bin/bash
#SBATCH --job-name=codec-sweep
#SBATCH --partition=defq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/scratch/shivam.chauhan/codecs/slurm/%x-%A_%a.out
#SBATCH --array=0-5

# One array task per codec/rate configuration. Ask for one GPU and a slice of a
# node, not a whole node: 8 GPUs per node means --gres=gpu:1 queues far sooner
# on a busy cluster, and this workload does not scale past one device.
#
# The outbound proxy comes from the login profile and is deliberately NOT set
# here: it carries a shared credential and must never be written into a file
# that could reach git.

set -euo pipefail
source /scratch/shivam.chauhan/codecs/env.sh
cd "$CODECS_ROOT/experiments"

CONFIGS=(
  "encodec:1.5" "encodec:3" "encodec:6" "encodec:12" "encodec:24"
  "identity:24000"
)
SPEC="${CONFIGS[$SLURM_ARRAY_TASK_ID]}"
TAG="${SPEC//:/_}"

echo "host $(hostname)  gpu ${CUDA_VISIBLE_DEVICES:-none}  config $SPEC"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true

python run_sweep.py \
    --codec "$SPEC" \
    --reps "${REPS:-20}" \
    --references 110 220 440 880 \
    --out "$CODECS_ROOT/results/sweep_${TAG}.csv"
