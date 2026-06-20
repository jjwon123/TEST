# ComfyUI Service

## Purpose

This service isolates ComfyUI-specific queueing, workflow presets, prompt payload construction, and output postprocessing from pipeline reasoning.

## Responsibilities

- Convert `image-prompts.json` records into ComfyUI workflow payloads
- Submit jobs to a ComfyUI server
- Track queue IDs and output files
- Apply postprocessing such as crop previews, upscaling, and metadata embedding

## Extension Plan

The first implementation should support dry-run payload generation. The next step is queue submission through `client.py` and manifest updates through `queue.py`.

## Current Live Preset

`korean_poster_overlay_1024` is wired as the default `03_visual_candidates` preset.

The default light-background typography treatment uses a bold dark headline,
dark secondary copy, no automatic aspect-ratio badge, and a wider headline box.
Pass `badge`, `text_color`, `secondary_text_color`, or `footer_text_color` to
override those defaults for another background.

It builds this ComfyUI API graph:

```text
LoadImage(qwen_image_edit_1024.png)
-> KoreanTextOverlay
-> KoreanTextOverlay
-> KoreanTextOverlay
-> KoreanTextOverlay
-> KoreanTextOverlay
-> SaveImage
```

Required ComfyUI-side files:

```text
D:\CD\fc_comfyui\ComfyUI_windows_portable_soylab\ComfyUI\custom_nodes\ComfyUI-KoreanTextOverlay
D:\CD\fc_comfyui\ComfyUI_windows_portable_soylab\ComfyUI\input\qwen_image_edit_1024.png
```

Dry-run/default mode:

```powershell
python scripts\workflow.py --run runs\<run-id> --stage 03_visual_candidates
```

Live mode, after ComfyUI is already running at `http://127.0.0.1:8188`:

```powershell
$env:COMFYUI_GENERATION_MODE='live'
python scripts\workflow.py --run runs\<run-id> --stage 03_visual_candidates --mode regenerate --group <group-id>
```

Live mode writes the returned ComfyUI image into the candidate `preview_path` and records the ComfyUI prompt id under `candidate-manifest.json > candidates[].comfyui_submission`.

## Product Locked Ad Background Preset

`product_locked_ad_background_v1` is the first product-image workflow.

It is intentionally conservative:

```text
LoadImage(product image)
-> ProductLockedAdComposite
-> SaveImage
```

The product RGB is only resized and composited. V1 does not repaint labels, logos, or product texture. It creates a studio-style background and contact shadow around the product layer.

Transparent padding is cropped from the product mask before `product_scale` is
applied, so the scale represents the visible product rather than the source
canvas size.

Required ComfyUI-side custom node:

```text
D:\CD\fc_comfyui\ComfyUI_windows_portable_soylab\ComfyUI\custom_nodes\ComfyUI-ProductLockedAd
```

The product image must be placed in ComfyUI `input`.

Example payload fields:

```json
{
  "workflow_preset": "product_locked_ad_background_v1",
  "product_image": "product_input.png",
  "ratio": "1:1",
  "background_style": "pharma_blue_rank",
  "product_scale": 0.58,
  "product_x_percent": 0.5,
  "product_y_percent": 0.58
}
```

See `docs/product_locked_ad_background_workflow.md` for the V1/V2/V3 plan.
