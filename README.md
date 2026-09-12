# MiniMax H3 ComfyUI — Runpod Serverless

This repository builds a custom-node worker. Large model weights live on a
persistent Runpod Network Volume so the GitHub build stays small and fast.

## 1. Populate the Network Volume

Create a Network Volume of at least **150 GB** (200 GB recommended) in the same
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

The script resumes interrupted downloads and verifies all ten files using
their published SHA-256 checksums. Terminate the temporary Pod after it reports
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
and downloads every model. Existing verified models are skipped.

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

## Installed models

- DaSiWa MiniMax H3 Hybrid 8Turbo v1 INT8
- Qwen3-VL 32B MiniMax H3 INT4 ConvRot
- Qwen3-VL 32B MiniMax H3 NVFP4 AWQ
- Original MiniMax H3 FL2VA pruned INT8 ConvRot
- Original MiniMax H3 REF2VA pruned INT8 ConvRot
- MiniMax H3 video VAE INT8 and FP16
- MiniMax H3 audio VAE FP32
- MiniMax H3 TAE preview model
- RIFE 4.26 interpolation

URLs and SHA-256 values are recorded in `model-sources.json`. Optional latent
and AnimeSharp upscaler weights are not installed; keep those stages disabled
unless you add their models to the volume.

Runpod's GitHub builder limits Docker builds to 30 minutes and images to 80 GB.
Keeping roughly 115 GB of weights on the volume avoids both limits.

References: [GitHub deployment](https://docs.runpod.io/serverless/workers/github-integration),
[network-volume paths](https://github.com/runpod-workers/worker-comfyui/blob/main/docs/network-volumes.md),
and [official ComfyUI worker](https://github.com/runpod-workers/worker-comfyui).
