#!/usr/bin/env bash
set -euo pipefail

# DGX Spark entrypoint for the fixed Director primary using the installed
# ARM64 vLLM container. Gemma/Ollama is never substituted for this slot.
MODEL_ID="${LOCAL_LLM_MODEL:-nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4}"
PORT="${LOCAL_LLM_PORT:-8001}"
HOST="${LOCAL_LLM_HOST:-127.0.0.1}"
GPU_UTIL="${LOCAL_LLM_GPU_MEMORY_UTILIZATION:-0.65}"
MAX_MODEL_LEN="${LOCAL_LLM_MAX_MODEL_LEN:-8192}"
MODEL_DIR="${LOCAL_LLM_MODEL_DIR:-/home/hajimi2025/.cache/interaction-nemotron}"
IMAGE="${LOCAL_LLM_VLLM_IMAGE:-vllm/vllm-openai:v0.27.1-aarch64}"

command -v docker >/dev/null || { echo "BLOCKED: docker not found" >&2; exit 2; }
test -f "$MODEL_DIR/config.json" || {
  echo "BLOCKED: model weights missing from $MODEL_DIR" >&2
  exit 2
}
test -f "$MODEL_DIR/model.safetensors.index.json" || {
  echo "BLOCKED: model shard index missing from $MODEL_DIR" >&2
  exit 2
}
for shard in "$MODEL_DIR"/model-*.safetensors; do
  test -f "$shard" || { echo "BLOCKED: no model shards in $MODEL_DIR" >&2; exit 2; }
done
EXPECTED_SHARDS=52
ACTUAL_SHARDS=$(find "$MODEL_DIR" -maxdepth 1 -name 'model-*.safetensors' | wc -l)
if [ "$ACTUAL_SHARDS" -ne "$EXPECTED_SHARDS" ]; then
  echo "BLOCKED: only $ACTUAL_SHARDS/$EXPECTED_SHARDS model shards downloaded" >&2
  exit 2
fi

docker rm -f interaction-nemotron >/dev/null 2>&1 || true
exec docker run --name interaction-nemotron --gpus all --ipc host --network host \
  -v "$MODEL_DIR:/models/nemotron:ro" \
  "$IMAGE" /models/nemotron \
  --served-model-name "$MODEL_ID" \
  --host "$HOST" \
  --port "$PORT" \
  --trust-remote-code \
  --dtype auto \
  --moe-backend marlin \
  --kv-cache-dtype fp8 \
  --mamba-backend flashinfer \
  --mamba-cache-mode align \
  --enable-prefix-caching \
  --reasoning-parser nemotron_v3 \
  --gpu-memory-utilization "$GPU_UTIL" \
  --max-model-len "$MAX_MODEL_LEN"
