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
    remove_nodes = {471, 475, 476, 482}
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
    width_x2 = clone(2775, (300, 6350), "01 · Output width ×2")
    height_x2 = clone(2776, (300, 6540), "02 · Output height ×2")
    latent_params = clone(2768, (590, 6350), "03 · H3 latent upscaler model")
    latent_scheduler = clone(2777, (590, 6560), "04 · One-step latent refinement")
    temporal_params = clone(2774, (900, 6350), "05 · Temporal split")
    spatial_params = clone(2773, (900, 6510), "06 · Spatial tiles")
    latent_upscale = clone(2769, (1230, 6350), "07 · H3 latent upscale ×2")
    latent_switch = clone(2749, (1230, 6750), "ENABLE LATENT UPSCALE ×2")
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
    # Replace the direct sampler-to-video-decode link. Final export intentionally uses the
    # untouched source audio, so the generated audio decoder is unnecessary.
    old_video_decode_link = nodes[472]["inputs"][0].get("link")
    if old_video_decode_link is not None:
        workflow["links"] = [link for link in workflow["links"] if link[0] != old_video_decode_link]
        old_out = nodes[469]["outputs"][0]
        old_out["links"] = [lid for lid in (old_out.get("links") or []) if lid != old_video_decode_link] or None
    nodes[472]["inputs"][0]["link"] = None
    connect(latent_upscale, 0, 472, 0, "LATENT")

    # DaSiWa EnhancedVideoCombine is a top-level node, not part of the Settings subgraph.
    combine_template = next(node for node in template["nodes"] if node["type"] == "DaSiWa_EnhancedVideoCombine")
    combine = copy.deepcopy(combine_template)
    combine["id"] = next_node_id
    next_node_id += 1
    combine["pos"] = [1920, 6370]
    combine["title"] = "09 · DaSiWa export · original source audio"
    for inp in combine.get("inputs", []):
        inp["link"] = None
    for out in combine.get("outputs", []):
        out["links"] = None
    combine["widgets_values"][8] = "video/character_swap/%date:yyyy-MM-dd%/%date:hhmmss%"
    workflow["nodes"].append(combine)
    nodes[combine["id"]] = combine
    combine_id = combine["id"]

    nodes[472]["pos"] = [1610, 6370]
    nodes[472]["title"] = "08 · Decode final frames"
    connect(472, 0, combine_id, 0, "IMAGE")
    connect(460, 1, combine_id, 1, "AUDIO")
    connect(460, 2, combine_id, 3, "FLOAT")

    # Organize the complete canvas into a compact, numbered left-to-right workflow.
    layout = {
        # Source video, timing, resolution and replacement image.
        459: ((0, 0), "01A · Load source video"),
        480: ((0, 335), "01B · Duration seconds"),
        483: ((270, 0), "01C · Trim source video"),
        460: ((570, 0), "01D · Video frames + original audio"),
        924: ((570, 145), "01E · Working resolution MP"),
        923: ((860, 0), "01F · Scale source frames"),
        925: ((1110, 0), "01G · Read working dimensions"),
        496: ((0, 465), "01H · Load replacement character"),
        # SAM mask and source-video preparation.
        456: ((1370, 0), "02A · Scale frames for SAM"),
        910: ((1680, 0), "02B · SAM3 subject tracking"),
        491: ((2045, 0), "02C · Mask preview conversion"),
        492: ((2310, 0), "02D · Preview tracked mask"),
        912: ((2045, 105), "02E · Invert source frames"),
        454: ((2310, 330), "02F · Composite masked reference video"),
        461: ((2610, 300), "02G · Preview H3 video reference"),
        # Qwen analysis and final prompt assembly.
        922: ((0, 850), "03A · Character-analysis instructions"),
        916: ((500, 850), "03B · Qwen character analysis"),
        509: ((0, 1300), "03C · Optional action hint"),
        920: ((300, 1190), "03D · Video-analysis instructions"),
        921: ((820, 1190), "03E · Qwen source-video analysis"),
        917: ((1090, 880), "03F · Assemble final H3 prompt"),
        918: ((1400, 850), "03G · Review final prompt before queue"),
        # H3 models and optional acceleration.
        463: ((0, 1730), "04A · H3 Ref2VA model"),
        465: ((0, 1850), "04B · H3 text encoder"),
        470: ((0, 2000), "04C · H3 video VAE"),
        474: ((0, 2100), "04D · H3 audio VAE"),
        502: ((0, 2210), "04E · Optional Turbo LoRA"),
        503: ((270, 2210), "04F · Optional attention acceleration"),
        # Ref2VA conditioning and base sampling.
        464: ((700, 1730), "05A · H3 character replacement conditioning"),
        467: ((1140, 1730), "05B · Seed / noise"),
        466: ((1140, 1840), "05C · Guider"),
        468: ((1140, 1930), "05D · Sampler"),
        473: ((1140, 2030), "05E · Base scheduler"),
        469: ((1540, 1730), "05F · Generate replacement latent"),
        # Latent quality lane and export.
        width_x2: ((1810, 1730), "06A · Output width ×2"),
        height_x2: ((1810, 1935), "06B · Output height ×2"),
        latent_params: ((2250, 1730), "06C · H3 latent upscaler model"),
        latent_scheduler: ((2250, 1940), "06D · One-step refinement"),
        temporal_params: ((2660, 1730), "06E · Temporal split"),
        spatial_params: ((2660, 1890), "06F · Spatial tiles"),
        latent_upscale: ((3010, 1730), "06G · H3 latent upscale ×2"),
        latent_switch: ((3010, 2260), "ENABLE / DISABLE LATENT UPSCALE ×2"),
        472: ((3370, 1730), "06H · Decode final frames"),
        combine_id: ((3650, 1730), "06I · DaSiWa export · original audio"),
    }
    for node_id, (position, title) in layout.items():
        if node_id in nodes:
            nodes[node_id]["pos"] = list(position)
            nodes[node_id]["title"] = title

    # Remove the old unconnected test-links note; it obscures the useful controls.
    workflow["nodes"] = [node for node in workflow["nodes"] if node["id"] != 500]
    nodes.pop(500, None)

    workflow["groups"] = [
        {"id": 1, "title": "01 · INPUTS — SOURCE VIDEO, TIMING, CHARACTER", "bounding": [-35, -55, 1325, 825], "color": "#315c78", "flags": {}},
        {"id": 2, "title": "02 · SAM3 — TRACK SUBJECT AND BUILD VIDEO REFERENCE", "bounding": [1335, -55, 1575, 825], "color": "#466b4f", "flags": {}},
        {"id": 3, "title": "03 · QWEN — ANALYZE CHARACTER + ACTION, THEN REVIEW PROMPT", "bounding": [-35, 795, 2055, 815], "color": "#705b38", "flags": {}},
        {"id": 4, "title": "04 · MODELS — H3 LOADERS + OPTIONAL ACCELERATION", "bounding": [-35, 1675, 690, 1025], "color": "#59466d", "flags": {}},
        {"id": 5, "title": "05 · MINIMAX H3 — REF2VA CONDITIONING + BASE GENERATION", "bounding": [665, 1675, 1135, 1025], "color": "#3f789e", "flags": {}},
        {"id": 6, "title": "06 · DASiWA QUALITY — LATENT 2×, DECODE, ORIGINAL-AUDIO EXPORT", "bounding": [1775, 1675, 2505, 1255], "color": "#7b4f32", "flags": {}},
    ]
    workflow.setdefault("extra", {}).setdefault("ds", {})
    workflow["extra"]["ds"] = {"scale": 0.42, "offset": [80, 80]}

    workflow["last_node_id"] = max(node["id"] for node in workflow["nodes"])
    workflow["last_link_id"] = max(link[0] for link in workflow["links"])
    output_path.write_text(json.dumps(workflow, separators=(",", ":")))
    print(f"Created {output_path}")


if __name__ == "__main__":
    main()
