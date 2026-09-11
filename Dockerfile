FROM runpod/worker-comfyui:5.10.0-base

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install every custom-node repository used by the supplied workflow.
# URLs avoid dependence on the Wizard's source detection and registry aliases.
RUN comfy-node-install \
    https://github.com/kijai/ComfyUI-KJNodes \
    https://github.com/bbaudio-2025/Comfyui-MMH3-UltimateUpscale \
    https://github.com/rgthree/rgthree-comfy \
    https://github.com/darksidewalker/ComfyUI-DaSiWa-Nodes \
    https://github.com/PlagueKind/ComfyUI-PlagueKind-Nodes \
    https://github.com/city96/ComfyUI-GGUF

# Keep the editable UI workflow in the image for reference. Serverless API jobs
# still submit an API-format workflow in input.workflow.
RUN mkdir -p /comfyui/user/default/workflows
COPY DasiwaMinimaxH3WorkflowsT2VA_cMMH3V19.json /comfyui/user/default/workflows/

# Model weights are stored on an attached Runpod Network Volume. The official
# base worker automatically scans /runpod-volume/models at runtime.
