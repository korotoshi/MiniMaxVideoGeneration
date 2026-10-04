#!/usr/bin/env python3
"""Merge the SAM/Qwen MiniMax H3 character workflow with DaSiWa quality post-processing."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path.home() / "Downloads" / "minimaxH3Character_v30WithQwenvl (1).json"
DEFAULT_TEMPLATE = ROOT / "DasiwaMinimaxH3WorkflowsT2VA_cMMH3V26.json"
DEFAULT_OUTPUT = ROOT / "minimaxH3Character_v30_DaSiWa_Quality.json"


def main() -> None:
    source_path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else DEFAULT_SOURCE
    output_path = Path(sys.argv[2]).expanduser() if len(sys.argv) > 2 else DEFAULT_OUTPUT
    workflow = json.loads(source_path.read_text())
    template = json.loads(DEFAULT_TEMPLATE.read_text())
    template_subgraph = template["definitions"]["subgraphs"][0]
    templates = {node["id"]: node for node in template_subgraph["nodes"]}

    # The original basic video writers are superseded by DaSiWa Enhanced Video Combine.
    remove_nodes = {475, 476, 482}
    workflow["nodes"] = [node for node in workflow["nodes"] if node["id"] not in remove_nodes]
    workflow["links"] = [
        link for link in workflow["links"] if link[1] not in remove_nodes and link[3] not in remove_nodes
    ]

    nodes = {node["id"]: node for node in workflow["nodes"]}
    for node in workflow["nodes"]:
        for inp in node.get("inputs", []):
            if inp.get("link") is not None and not any(link[0] == inp["link"] for link in workflow["links"]):
                inp["link"] = None
        for out in node.get("outputs", []):
            if out.get("links"):
                out["links"] = [lid for lid in out["links"] if any(link[0] == lid for link in workflow["links"])] or None

    # Avoid the remote finegrained-FP8 kernel/trust failure in both Qwen analysis nodes.
    for node_id in (916, 921):
        if node_id in nodes:
            node = nodes[node_id]
            node["widgets_values"][0] = "Qwen3-VL-8B-Instruct"
            node["widgets_values"][1] = "None (FP16)"
            node["widgets_values"][2] = "sdpa"
            node["widgets_values"][13] = False

    next_node_id = max(node["id"] for node in workflow["nodes"]) + 1
    next_link_id = max((link[0] for link in workflow["links"]), default=0) + 1

    def clone(template_id: int, position: tuple[float, float], title: str | None = None) -> int:
        nonlocal next_node_id
        node = copy.deepcopy(templates[template_id])
        node["id"] = next_node_id
        node["pos"] = list(position)
        if title:
            node["title"] = title
        for inp in node.get("inputs", []):
            inp["link"] = None
        for out in node.get("outputs", []):
            out["links"] = None
        workflow["nodes"].append(node)
        nodes[node["id"]] = node
        next_node_id += 1
        return node["id"]

    def connect(origin_id: int, origin_slot: int, target_id: int, target_slot: int, data_type: str) -> int:
        nonlocal next_link_id
        link_id = next_link_id
        next_link_id += 1
        workflow["links"].append([link_id, origin_id, origin_slot, target_id, target_slot, data_type])
        nodes[target_id]["inputs"][target_slot]["link"] = link_id
        out = nodes[origin_id]["outputs"][origin_slot]
        if out.get("links") is None:
            out["links"] = []
        out["links"].append(link_id)
        return link_id

    # Optional H3 latent 2x upscale before VAE decoding.
    width_x2 = clone(2775, (100, 7020), "Latent upscale width ×2")
    height_x2 = clone(2776, (100, 7200), "Latent upscale height ×2")
    latent_params = clone(2768, (390, 7000), "H3 latent upscaler model")
    latent_scheduler = clone(2777, (390, 7190), "H3 latent upscale scheduler")
    temporal_params = clone(2774, (700, 7000), "H3 temporal split")
    spatial_params = clone(2773, (700, 7160), "H3 spatial split")
    latent_upscale = clone(2769, (1050, 6990), "Optional H3 latent upscale ×2")
    latent_switch = clone(2749, (1050, 7350), "Enable H3 latent upscale ×2")
    # Use the model filename downloaded by this repository.
    nodes[latent_params]["widgets_values"][0] = "minimax_h3_latent_upscaler_3d_conv_v1_bf16.safetensors"

    connect(925, 0, width_x2, 0, "FLOAT,INT,BOOLEAN")
    connect(925, 1, height_x2, 0, "FLOAT,INT,BOOLEAN")
    connect(width_x2, 1, latent_params, 1, "INT")
    connect(height_x2, 1, latent_params, 2, "INT")
    connect(width_x2, 1, spatial_params, 0, "INT")
    connect(height_x2, 1, spatial_params, 1, "INT")
    connect(503, 0, latent_scheduler, 0, "MODEL")
    connect(503, 0, latent_upscale, 0, "MODEL")
    connect(464, 0, latent_upscale, 1, "CONDITIONING")
    connect(469, 0, latent_upscale, 2, "LATENT")
    connect(467, 0, latent_upscale, 3, "NOISE")
    connect(468, 0, latent_upscale, 4, "SAMPLER")
    connect(latent_scheduler, 0, latent_upscale, 5, "SIGMAS")
    connect(latent_params, 0, latent_upscale, 7, "H3_UPSCALE_PARAM")
    connect(temporal_params, 0, latent_upscale, 8, "H3_TEMPORAL_PARAM")
    connect(spatial_params, 0, latent_upscale, 9, "H3_SPATIAL_PARAM")
    connect(spatial_params, 0, latent_switch, 3, "H3_SPATIAL_PARAM")
    connect(latent_params, 0, latent_switch, 4, "H3_UPSCALE_PARAM")
    connect(latent_upscale, 0, latent_switch, 5, "LATENT")
    connect(latent_scheduler, 0, latent_switch, 6, "SIGMAS")
    connect(temporal_params, 0, latent_switch, 7, "H3_TEMPORAL_PARAM")
    connect(width_x2, 1, latent_switch, 8, "INT")
    connect(height_x2, 1, latent_switch, 9, "INT")
    # Replace the direct sampler-to-video-decode link. Audio remains decoded from the base latent,
    # while final export intentionally uses the untouched source audio.
    old_video_decode_link = nodes[472]["inputs"][0].get("link")
    if old_video_decode_link is not None:
        workflow["links"] = [link for link in workflow["links"] if link[0] != old_video_decode_link]
        old_out = nodes[469]["outputs"][0]
        old_out["links"] = [lid for lid in (old_out.get("links") or []) if lid != old_video_decode_link] or None
    nodes[472]["inputs"][0]["link"] = None
    connect(latent_upscale, 0, 472, 0, "LATENT")

    # DaSiWa post-decode quality chain. Every expensive stage is bypassed by default.
    interp_model = clone(2714, (390, 7650), "RIFE interpolation model")
    interpolate = clone(2715, (700, 7650), "Optional RIFE ×2 interpolation")
    fps_x2 = clone(2717, (700, 7870), "Output FPS ×2 when interpolating")
    interp_switch = clone(2716, (700, 8040), "Enable RIFE interpolation")
    simple_upscale = clone(2546, (1050, 7650), "Optional simple 2× upscale")
    simple_switch = clone(2448, (1050, 8010), "Enable simple 2× upscale")
    upscale_loader = clone(2079, (1360, 7650), "2× upscale model")
    model_upscale = clone(2537, (1360, 7780), "Optional model 2× upscale")
    model_switch = clone(2449, (1360, 8010), "Enable model 2× upscale")
    rtx_upscale = clone(2528, (1700, 7650), "Optional DaSiWa RTX upscaler/refiner")
    rtx_switch = clone(2450, (1700, 8010), "Enable RTX upscaler/refiner")

    # DaSiWa EnhancedVideoCombine is a top-level node, not part of the Settings subgraph.
    combine_template = next(node for node in template["nodes"] if node["type"] == "DaSiWa_EnhancedVideoCombine")
    combine = copy.deepcopy(combine_template)
    combine["id"] = next_node_id
    next_node_id += 1
    combine["pos"] = [2080, 7650]
    combine["title"] = "DaSiWa final video — original source audio"
    for inp in combine.get("inputs", []):
        inp["link"] = None
    for out in combine.get("outputs", []):
        out["links"] = None
    combine["widgets_values"][8] = "video/character_swap/%date:yyyy-MM-dd%/%date:hhmmss%"
    workflow["nodes"].append(combine)
    nodes[combine["id"]] = combine
    combine_id = combine["id"]

    connect(472, 0, interpolate, 1, "IMAGE")
    connect(interp_model, 0, interpolate, 0, "INTERP_MODEL")
    connect(460, 2, fps_x2, 0, "FLOAT,INT,BOOLEAN")
    connect(interpolate, 0, simple_upscale, 0, "IMAGE")
    connect(simple_upscale, 0, model_upscale, 1, "IMAGE")
    connect(upscale_loader, 0, model_upscale, 0, "UPSCALE_MODEL")
    connect(model_upscale, 0, rtx_upscale, 0, "IMAGE")
    connect(rtx_upscale, 0, combine_id, 0, "IMAGE")
    connect(460, 1, combine_id, 1, "AUDIO")
    connect(fps_x2, 0, combine_id, 3, "FLOAT")

    connect(fps_x2, 0, interp_switch, 1, "FLOAT")
    connect(interpolate, 0, interp_switch, 2, "IMAGE")
    connect(interp_model, 0, interp_switch, 3, "INTERP_MODEL")
    connect(simple_upscale, 0, simple_switch, 1, "IMAGE")
    connect(model_upscale, 0, model_switch, 1, "IMAGE")
    connect(upscale_loader, 0, model_switch, 2, "UPSCALE_MODEL")
    connect(rtx_upscale, 0, rtx_switch, 1, "IMAGE")

    workflow.setdefault("groups", []).append(
        {
            "id": max((g.get("id", 0) for g in workflow.get("groups", [])), default=0) + 1,
            "title": "DaSiWa Quality Post-Processing — all optional stages disabled by default",
            "bounding": [55, 6940, 2375, 1260],
            "color": "#3f789e",
            "flags": {},
        }
    )

    workflow["last_node_id"] = max(node["id"] for node in workflow["nodes"])
    workflow["last_link_id"] = max(link[0] for link in workflow["links"])
    output_path.write_text(json.dumps(workflow, separators=(",", ":")))
    print(f"Created {output_path}")


if __name__ == "__main__":
    main()
