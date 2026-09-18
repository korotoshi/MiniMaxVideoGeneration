#!/usr/bin/env python3
"""Create a non-turbo UI workflow without altering the original turbo file."""

import json
import sys
from pathlib import Path

source, destination = map(Path, sys.argv[1:3])
workflow = json.loads(source.read_text())
settings = next(
    node for node in workflow["nodes"]
    if node.get("widgets_values_named", {}).get("unet_name") is not None
)
updates = {
    "sampler_name": (0, "res_multistep"),
    "steps": (2, 25),
    "shift_video": (3, 10),
    "shift_audio": (4, 3),
    "unet_name": (17, "MiniMaxH3/minimax_h3_fl2va_int8_convrot.safetensors"),
    "unet_name_1": (18, "MiniMaxH3/DasiwaMinimaxH3_dasiwaHybridV2_int8.safetensors"),
    "clip_name": (19, "qwen3vl_32b_minimax_h3_bf16.safetensors"),
    "vae_name": (20, "MiniMaxH3/minimax_h3_video_vae_fp16.safetensors"),
}
for name, (index, value) in updates.items():
    settings["widgets_values"][index] = value
    settings["widgets_values_named"][name] = value

if destination.exists():
    print(f"Keeping existing workflow: {destination}")
else:
    destination.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n")
    print(f"Created quality workflow: {destination}")
