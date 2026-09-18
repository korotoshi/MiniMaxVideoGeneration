#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
comfy_root="${1:-${HOME}/apps/ComfyUI}"

if [[ ! -d "${comfy_root}/models" || ! -d "${comfy_root}/custom_nodes" ]]; then
  echo "ComfyUI not found at ${comfy_root}" >&2
  exit 1
fi

# Massed Compute images sometimes create these directories as root. Only
# change ownership inside the ComfyUI node/model paths needed by this setup.
if [[ -n "$(find "${comfy_root}/custom_nodes" ! -writable -print -quit)" ]]; then
  echo "Fixing ownership of ${comfy_root}/custom_nodes"
  sudo chown -R "$(id -u):$(id -g)" "${comfy_root}/custom_nodes"
fi
if [[ -n "$(find "${comfy_root}/models" -type d ! -writable -print -quit)" ]]; then
  echo "Fixing ownership of model directories (not the large model files)"
  sudo find "${comfy_root}/models" -type d -exec chown "$(id -u):$(id -g)" {} +
fi

MODEL_PROFILE=quality bash "${repo_root}/scripts/setup-vm.sh" "${comfy_root}"

workflow_dir="${comfy_root}/user/default/workflows"
if [[ ! -d "${workflow_dir}" ]]; then
  mkdir -p "${workflow_dir}" 2>/dev/null || \
    sudo install -d -o "$(id -u)" -g "$(id -g)" "${workflow_dir}"
fi
if [[ ! -w "${workflow_dir}" ]]; then
  sudo chown "$(id -u):$(id -g)" "${workflow_dir}"
fi
python3 "${repo_root}/scripts/make-quality-workflow.py" \
  "${repo_root}/DasiwaMinimaxH3WorkflowsT2VA_cMMH3V19.json" \
  "${workflow_dir}/MiniMax-H3-Quality.json"

echo "Quality VM setup complete. Restart ComfyUI, then open MiniMax-H3-Quality."
