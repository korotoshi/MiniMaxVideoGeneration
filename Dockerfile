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

# Active MiniMax H3 8-step model path. Model filenames and directories match
# the values stored in DasiwaMinimaxH3WorkflowsT2VA_cMMH3V19.json.
RUN comfy model download \
      --url "https://huggingface.co/brurpo/DaSiWa-MiniMax-H3-Hybrid/resolve/main/DasiwaMinimaxH3_dasiwaHybrid8turboV1.safetensors?download=true" \
      --relative-path models/diffusion_models/MiniMaxH3 \
      --filename DasiwaMinimaxH3_dasiwaHybrid8turboV1.safetensors \
 && comfy model download \
      --url "https://huggingface.co/Abiray/MiniMax-H3-GGUF/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_int4_convrot.safetensors?download=true" \
      --relative-path models/text_encoders \
      --filename qwen3vl_32b_minimax_h3_int4_convrot.safetensors

RUN comfy model download \
      --url "https://huggingface.co/Kijai/MiniMax-H3-experimental/resolve/main/minimax_h3_video_vae_int8_convrot.safetensors?download=true" \
      --relative-path models/vae/MiniMaxH3 \
      --filename minimax_h3_video_vae_int8_convrot.safetensors \
 && comfy model download \
      --url "https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_audio_vae_fp32.safetensors?download=true" \
      --relative-path models/vae/MiniMaxH3 \
      --filename minimax_h3_audio_vae_fp32.safetensors

# Optional models referenced by the UI workflow. They are small enough to keep
# in this image and prevent missing-model warnings when those toggles are used.
RUN comfy model download \
      --url "https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_video_vae_fp16.safetensors?download=true" \
      --relative-path models/vae/MiniMaxH3 \
      --filename minimax_h3_video_vae_fp16.safetensors \
 && comfy model download \
      --url "https://huggingface.co/Kijai/MiniMax-H3-TAE/resolve/main/vae_approx/taeh3.safetensors?download=true" \
      --relative-path models/vae_approx \
      --filename taeh3.safetensors \
 && comfy model download \
      --url "https://huggingface.co/Comfy-Org/frame_interpolation/resolve/main/frame_interpolation/rife_v4.26.safetensors?download=true" \
      --relative-path models/frame_interpolation \
      --filename rife_v4.26.safetensors

# Keep the editable UI workflow in the image for reference. Serverless API jobs
# still submit an API-format workflow in input.workflow.
RUN mkdir -p /comfyui/user/default/workflows
COPY DasiwaMinimaxH3WorkflowsT2VA_cMMH3V19.json /comfyui/user/default/workflows/

