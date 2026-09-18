# MiniMax H3 ComfyUI — Runpod Serverless

This repository builds a custom-node worker. Large model weights live on a
persistent Runpod Network Volume so the GitHub build stays small and fast.

## 1. Populate the Network Volume

Create a Network Volume of at least **150 GB** for the quality profile (200 GB
recommended, or more if keeping the old turbo weights too) in the same
datacenter as the endpoint. Attach it temporarily to a Runpod Pod, open that
Pod's terminal, and run:

```bash
git clone https://github.com/korotoshi/MiniMaxVideoGeneration.git
cd MiniMaxVideoGeneration
bash scripts/populate-network-volume.sh /workspace
```

This repository is private, so authenticate GitHub in the temporary Pod before
cloning it. Alternatively, upload `scripts/populate-network-volume.sh` to the
Pod and run it there.

The script defaults to the **quality** profile shown below, resumes interrupted
downloads, and verifies SHA-256 checksums. Set `CIVITAIKEY` (or
`CIVITAI_API_KEY`) if CivitAI requires authentication. Terminate the temporary Pod after it reports
success; this does not delete the Network Volume.

The all-in-one VM setup installs `aria2`. Downloads then use eight HTTP range
connections per model and two model files concurrently. Override either value:

```bash
ARIA2_CONNECTIONS=8 MAX_PARALLEL_DOWNLOADS=2 \
  bash scripts/populate-network-volume.sh /workspace
```

For a normal Massed Compute ComfyUI VM, open a terminal in the ComfyUI folder
and run the all-in-one setup instead:

```bash
bash /path/to/MiniMaxVideoGeneration/scripts/setup-vm.sh
```

It installs or updates all custom nodes, installs their Python requirements,
and downloads the quality-profile models. Existing verified models are skipped.
To restore the previous fast setup instead, use `MODEL_PROFILE=turbo` before
either download command. The two profiles can coexist on a volume.

For a fresh or existing Massed Compute VM, this **single command** clones or
updates this repository and performs the entire quality setup, including a
separate `MiniMax-H3-Quality` workflow in ComfyUI:

```bash
bash -lc 'repo="$HOME/MiniMaxVideoGeneration"; if [ -d "$repo/.git" ]; then git -C "$repo" pull --ff-only; else git clone https://github.com/korotoshi/MiniMaxVideoGeneration.git "$repo"; fi && bash "$repo/scripts/bootstrap-vm.sh" "$HOME/apps/ComfyUI"'
```

The repository is private, so the VM must already have GitHub access. The
bootstrap fixes ownership only within ComfyUI's custom-node tree and model
directories when needed; `sudo` may prompt. It loads CivitAI credentials from
`~/.env` through `setup-vm.sh`, skips verified downloads, and can be rerun.

## 2. Deploy from GitHub

1. Connect GitHub under Runpod **Settings → Connections**.
2. Choose **Serverless → New Endpoint → Import Git Repository**.
3. Select `korotoshi/MiniMaxVideoGeneration`, branch `main`, and `Dockerfile`.
4. Choose a Queue endpoint and a GPU with sufficient VRAM for MiniMax H3.
5. Under **Advanced → Select Network Volume**, attach the populated volume.
6. Set a long video-generation timeout and deploy.

The official worker automatically scans `/runpod-volume/models/...`. No custom
symlinks are needed. Temporarily set `NETWORK_VOLUME_DEBUG=true` on the endpoint
if models are not detected.

## API request

The worker expects a ComfyUI API-format workflow:

```json
{"input":{"workflow":{}}}
```

The included JSON is the editable UI workflow. Load it in ComfyUI and choose
**Workflow → Export (API)**, then submit that exported object as
`input.workflow`.

## Quality-profile models (default)

- Original MiniMax H3 FL2VA full INT8 ConvRot (34 GB)
- DaSiWa Hybrid V2 non-turbo INT8 (19.53 GB; CivitAI)
- Qwen3-VL 32B MiniMax H3 BF16 (51.5 GB)
- MiniMax H3 video VAE FP16 and audio VAE FP32
- MiniMax H3 3D BF16 latent upscaler (691 MB)
- MiniMax H3 TAE preview model and RIFE 4.26 interpolation

`bootstrap-vm.sh` creates a separate quality workflow with those exact files,
`res_multistep` / `simple`, 25 steps, and video/audio shifts of 10 / 3. The
bundled original workflow retains its turbo defaults. The generated workflow
is kept if it already exists so reruns do not overwrite your edits.
The latent 2x stage remains optional and may need its spatial-split settings
refreshed if the installed node version rejects the old workflow values.

The CivitAI V2 download is pinned to INT8 file ID `3203130` and its published
SHA-256 hash. A checksum mismatch stops the setup.

## Turbo-profile models (`MODEL_PROFILE=turbo`)

- DaSiWa MiniMax H3 Hybrid 8Turbo v1 INT8
- Qwen3-VL 32B MiniMax H3 INT4 ConvRot
- Qwen3-VL 32B MiniMax H3 NVFP4 AWQ
- Original MiniMax H3 FL2VA pruned INT8 ConvRot
- Original MiniMax H3 REF2VA pruned INT8 ConvRot
- MiniMax H3 video VAE INT8 and FP16
- MiniMax H3 audio VAE FP32
- MiniMax H3 TAE preview model
- RIFE 4.26 interpolation

URLs and SHA-256 values are recorded in `model-sources.json`. The AnimeSharp
upscaler weight is not installed; keep that stage disabled unless you add it.

Runpod's GitHub builder limits Docker builds to 30 minutes and images to 80 GB.
Keeping model weights on the volume avoids both limits.

References: [GitHub deployment](https://docs.runpod.io/serverless/workers/github-integration),
[network-volume paths](https://github.com/runpod-workers/worker-comfyui/blob/main/docs/network-volumes.md),
and [official ComfyUI worker](https://github.com/runpod-workers/worker-comfyui).
