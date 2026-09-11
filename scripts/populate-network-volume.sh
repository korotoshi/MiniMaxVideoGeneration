#!/usr/bin/env bash
set -euo pipefail

volume_root="${1:-/workspace}"
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
  curl --fail --location --retry 8 --retry-all-errors \
    --continue-at - --output "${partial}" "${url}"
  echo "${sha256}  ${partial}" | sha256sum --check
  mv "${partial}" "${destination}"
}

download_model "diffusion_models/MiniMaxH3" \
  "DasiwaMinimaxH3_dasiwaHybrid8turboV1.safetensors" \
  "e0441d26414f6e0c28f43d580e6cc56fad424da0fa4d261b698ca73188aa6332" \
  "https://huggingface.co/brurpo/DaSiWa-MiniMax-H3-Hybrid/resolve/main/DasiwaMinimaxH3_dasiwaHybrid8turboV1.safetensors?download=true"

download_model "text_encoders" \
  "qwen3vl_32b_minimax_h3_int4_convrot.safetensors" \
  "21fd2e2f06bc4fc422c6aa20893fe189edbbd9ab3068215f96e7a6cf2f6cb5bb" \
  "https://huggingface.co/Abiray/MiniMax-H3-GGUF/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_int4_convrot.safetensors?download=true"

download_model "vae/MiniMaxH3" \
  "minimax_h3_video_vae_int8_convrot.safetensors" \
  "9bb2d96f218c76babd85e0611b85ca8fb330a90546c01a0005e8a58a59593410a" \
  "https://huggingface.co/Kijai/MiniMax-H3-experimental/resolve/main/minimax_h3_video_vae_int8_convrot.safetensors?download=true"

download_model "vae/MiniMaxH3" \
  "minimax_h3_audio_vae_fp32.safetensors" \
  "8e505d95dd1561d47abd43d4238fd40d9bb1ae9e147ed0a4cba778d76ae4db48" \
  "https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_audio_vae_fp32.safetensors?download=true"

download_model "vae/MiniMaxH3" \
  "minimax_h3_video_vae_fp16.safetensors" \
  "7c1f131492e7eddacaac9069a61b81bdd39de5cc96561e677c5eab1cdce5e522" \
  "https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_video_vae_fp16.safetensors?download=true"

download_model "vae_approx" \
  "taeh3.safetensors" \
  "f0f60fa072089997f817402098c2fd90777cb2660dd79cf5df42fc1e3e08e527" \
  "https://huggingface.co/Kijai/MiniMax-H3-TAE/resolve/main/vae_approx/taeh3.safetensors?download=true"

download_model "frame_interpolation" \
  "rife_v4.26.safetensors" \
  "151874592c877740e5db11522f4514df569eeafb0a0fcb2696f16e9e8d317c94" \
  "https://huggingface.co/Comfy-Org/frame_interpolation/resolve/main/frame_interpolation/rife_v4.26.safetensors?download=true"

echo
echo "Network Volume is ready at ${models_root}"
du -sh "${models_root}"
