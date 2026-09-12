#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -ge 1 ]]; then
  comfy_root="$1"
elif [[ -d "${PWD}/models" && -d "${PWD}/custom_nodes" ]]; then
  comfy_root="${PWD}"
else
  echo "Run this from the ComfyUI directory or pass its full path:" >&2
  echo "  bash scripts/setup-vm.sh /path/to/ComfyUI" >&2
  exit 1
fi

if [[ ! -d "${comfy_root}/models" || ! -d "${comfy_root}/custom_nodes" ]]; then
  echo "Not a ComfyUI directory: ${comfy_root}" >&2
  exit 1
fi

if [[ -f "${HOME}/.env" ]]; then
  set -a
  # Massed Compute writes user-provided environment values here on boot.
  source "${HOME}/.env"
  set +a
fi

if ! command -v aria2c >/dev/null 2>&1; then
  echo "Installing aria2 for accelerated multi-connection model downloads"
  sudo apt-get update
  sudo apt-get install -y aria2
fi

if [[ -x "${comfy_root}/.venv/bin/python" ]]; then
  comfy_python="${comfy_root}/.venv/bin/python"
elif [[ -x "${comfy_root}/venv/bin/python" ]]; then
  comfy_python="${comfy_root}/venv/bin/python"
else
  comfy_python="$(command -v python3 || command -v python)"
fi

install_node() {
  local repo_url="$1"
  local directory="$2"
  local destination="${comfy_root}/custom_nodes/${directory}"

  if [[ -d "${destination}/.git" ]]; then
    echo "Updating ${directory}"
    git -C "${destination}" pull --ff-only
  elif [[ -e "${destination}" ]]; then
    echo "Skipping ${directory}: destination exists but is not a Git checkout"
  else
    echo "Installing ${directory}"
    git clone --depth 1 "${repo_url}" "${destination}"
  fi

  if [[ -f "${destination}/requirements.txt" ]]; then
    "${comfy_python}" -m pip install -r "${destination}/requirements.txt"
  fi
}

install_node "https://github.com/kijai/ComfyUI-KJNodes.git" \
  "ComfyUI-KJNodes"
install_node "https://github.com/bbaudio-2025/Comfyui-MMH3-UltimateUpscale.git" \
  "Comfyui-MMH3-UltimateUpscale"
install_node "https://github.com/rgthree/rgthree-comfy.git" \
  "rgthree-comfy"
install_node "https://github.com/darksidewalker/ComfyUI-DaSiWa-Nodes.git" \
  "ComfyUI-DaSiWa-Nodes"
install_node "https://github.com/PlagueKind/ComfyUI-PlagueKind-Nodes.git" \
  "ComfyUI-PlagueKind-Nodes"
install_node "https://github.com/city96/ComfyUI-GGUF.git" \
  "ComfyUI-GGUF"

bash "${script_dir}/populate-network-volume.sh" "${comfy_root}"

echo
echo "VM setup complete. Restart ComfyUI before loading the workflow."
