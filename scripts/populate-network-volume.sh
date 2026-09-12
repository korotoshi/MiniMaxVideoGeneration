#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ge 1 ]]; then
  volume_root="$1"
elif [[ -d "${PWD}/models" ]]; then
  volume_root="${PWD}"
else
  volume_root="/workspace"
fi
models_root="${volume_root}/models"

if [[ ! -d "${volume_root}" ]]; then
  echo "Volume mount does not exist: ${volume_root}" >&2
  exit 1
fi

download_model() {
  local relative_path="$1"
  local filename="$2"
  local sha256="$3"
  local url="$4"
  local destination="${models_root}/${relative_path}/${filename}"
  local partial="${destination}.part"

  mkdir -p "$(dirname "${destination}")"

  if [[ -f "${destination}" ]] && \
     echo "${sha256}  ${destination}" | sha256sum --check --status; then
    echo "Already verified: ${destination}"
    return
  fi

  echo "Downloading ${filename}"
  if command -v aria2c >/dev/null 2>&1; then
    aria2c \
      --allow-overwrite=true \
      --auto-file-renaming=false \
      --check-certificate=true \
      --console-log-level=warn \
      --continue=true \
      --dir="$(dirname "${partial}")" \
      --file-allocation=none \
      --max-connection-per-server="${ARIA2_CONNECTIONS:-8}" \
      --max-tries=10 \
      --min-split-size=16M \
      --out="$(basename "${partial}")" \
      --retry-wait=3 \
      --split="${ARIA2_CONNECTIONS:-8}" \
      --summary-interval=10 \
      "${url}"
  else
    curl --fail --location --retry 8 --retry-all-errors \
      --continue-at - --output "${partial}" "${url}"
  fi
  echo "${sha256}  ${partial}" | sha256sum --check
  mv "${partial}" "${destination}"
}

if command -v aria2c >/dev/null 2>&1; then
  default_parallel=2
else
  default_parallel=3
fi
max_parallel="${MAX_PARALLEL_DOWNLOADS:-${default_parallel}}"
if ! [[ "${max_parallel}" =~ ^[1-9][0-9]*$ ]]; then
  echo "MAX_PARALLEL_DOWNLOADS must be a positive integer" >&2
  exit 1
fi

download_pids=()
download_failed=0

wait_for_oldest_download() {
  local pid="${download_pids[0]}"
  if ! wait "${pid}"; then
    download_failed=1
  fi
  download_pids=("${download_pids[@]:1}")
}

queue_download() {
  download_model "$@" &
  download_pids+=("$!")
  if (( ${#download_pids[@]} >= max_parallel )); then
    wait_for_oldest_download
  fi
}

if command -v aria2c >/dev/null 2>&1; then
  echo "Fast downloader: aria2 (${ARIA2_CONNECTIONS:-8} connections per file)"
else
  echo "Downloader: curl (install aria2 for multi-connection downloads)"
fi
echo "Downloading up to ${max_parallel} model files concurrently"

queue_download "diffusion_models/MiniMaxH3" \
  "DasiwaMinimaxH3_dasiwaHybrid8turboV1.safetensors" \
  "e0441d26414f6e0c28f43d580e6cc56fad424da0fa4d261b698ca73188aa6332" \
  "https://huggingface.co/brurpo/DaSiWa-MiniMax-H3-Hybrid/resolve/main/DasiwaMinimaxH3_dasiwaHybrid8turboV1.safetensors?download=true"

queue_download "text_encoders" \
  "qwen3vl_32b_minimax_h3_int4_convrot.safetensors" \
  "21fd2e2f06bc4fc422c6aa20893fe189edbbd9ab3068215f96e7a6cf2f6cb5bb" \
  "https://huggingface.co/Abiray/MiniMax-H3-GGUF/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_int4_convrot.safetensors?download=true"

queue_download "text_encoders" \
  "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors" \
  "35a88d51044231fe332301d7a62aa81e3f2cba62febeb446e2c1e3e0ef76f2c6" \
  "https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors?download=true"

queue_download "diffusion_models/MiniMaxH3" \
  "minimax_h3_fl2va_pruned_int8_convrot.safetensors" \
  "e889202c41dafb67b10d67b97f0d8541508036a6090af23425a5c2615d03c47a" \
  "https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors?download=true"

queue_download "diffusion_models/MiniMaxH3" \
  "minimax_h3_ref2va_pruned_int8_convrot.safetensors" \
  "9255f52b6677845ad238f20dfaafa94727053694127ab7f255c048f0f9365779" \
  "https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors?download=true"

queue_download "vae/MiniMaxH3" \
  "minimax_h3_video_vae_int8_convrot.safetensors" \
  "9bb2d96f218c76babd85e0611b85ca8fb330a90546c01a0005e8a58a59593410a" \
  "https://huggingface.co/Kijai/MiniMax-H3-experimental/resolve/main/minimax_h3_video_vae_int8_convrot.safetensors?download=true"

queue_download "vae/MiniMaxH3" \
  "minimax_h3_audio_vae_fp32.safetensors" \
  "8e505d95dd1561d47abd43d4238fd40d9bb1ae9e147ed0a4cba778d76ae4db48" \
  "https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_audio_vae_fp32.safetensors?download=true"

queue_download "vae/MiniMaxH3" \
  "minimax_h3_video_vae_fp16.safetensors" \
  "7c1f131492e7eddacaac9069a61b81bdd39de5cc96561e677c5eab1cdce5e522" \
  "https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_video_vae_fp16.safetensors?download=true"

queue_download "vae_approx" \
  "taeh3.safetensors" \
  "f0f60fa072089997f817402098c2fd90777cb2660dd79cf5df42fc1e3e08e527" \
  "https://huggingface.co/Kijai/MiniMax-H3-TAE/resolve/main/vae_approx/taeh3.safetensors?download=true"

queue_download "frame_interpolation" \
  "rife_v4.26.safetensors" \
  "151874592c877740e5db11522f4514df569eeafb0a0fcb2696f16e9e8d317c94" \
  "https://huggingface.co/Comfy-Org/frame_interpolation/resolve/main/frame_interpolation/rife_v4.26.safetensors?download=true"

while (( ${#download_pids[@]} > 0 )); do
  wait_for_oldest_download
done

if (( download_failed != 0 )); then
  echo "One or more model downloads failed. Run this script again to resume." >&2
  exit 1
fi

echo
echo "Network Volume is ready at ${models_root}"
du -sh "${models_root}"
