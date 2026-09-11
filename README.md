# MiniMax H3 ComfyUI — Runpod Serverless

Custom Runpod Serverless worker for the included DaSiWa MiniMax H3 8Turbo
ComfyUI workflow. The Docker build installs all custom nodes and downloads the
active model set into the exact directories expected by the workflow.

## Deploy from GitHub

1. In Runpod, open **Settings → Connections → GitHub** and authorize this repo.
2. Open **Serverless → New Endpoint → Import Git Repository**.
3. Select this repository, branch `main`, and Dockerfile path `Dockerfile`.
4. Choose a Queue endpoint and a GPU with enough VRAM for MiniMax H3.
5. Set a suitably long execution timeout for video generation, then deploy.

Runpod builds and stores the image. Do not use the ComfyUI-to-API Wizard for
this repo—the Dockerfile already resolves the model and custom-node sources.

## Request format

The official worker expects a ComfyUI **API-format** workflow:

```json
{
  "input": {
    "workflow": {}
  }
}
```

The included JSON is the editable UI workflow. Load it in ComfyUI, then choose
**Workflow → Export (API)** and put that exported object in `input.workflow`.
Images and other input media can be supplied using the worker's `input.images`
array.

## Included active models

- DaSiWa MiniMax H3 Hybrid 8Turbo v1 INT8
- Qwen3-VL 32B MiniMax H3 INT4 ConvRot text encoder
- MiniMax H3 video VAE INT8
- MiniMax H3 audio VAE FP32
- MiniMax H3 video VAE FP16
- MiniMax H3 TAE preview model
- RIFE 4.26 frame interpolation

Exact URLs and known SHA-256 values are recorded in `model-sources.json`.

## Deliberately excluded optional weights

The workflow contains disabled branches for the original FL2VA/REF2VA models,
latent upscaling, and AnimeSharp upscaling. Those weights are not baked into
the image because Runpod's GitHub integration limits images to 80 GB. Keep
those stages disabled unless you later put their weights on a Runpod Network
Volume.

## Important build limits

Runpod currently gives GitHub Docker builds 30 minutes and limits the final
image to 80 GB. The initial build downloads tens of gigabytes. If it exceeds
the build timeout, use the same Dockerfile with an external container builder
and deploy the resulting registry image, or move models to a Network Volume.

References: [Runpod GitHub deployment](https://docs.runpod.io/serverless/workers/github-integration),
[official ComfyUI worker](https://github.com/runpod-workers/worker-comfyui), and
[worker customization](https://github.com/runpod-workers/worker-comfyui/blob/main/docs/customization.md).

