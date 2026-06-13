# Product Ad Image Workflow

## Goal

Create ad-ready product visuals while preserving the original product image as much as possible.

```text
product source image
-> alpha/mask based product lock
-> ad background
-> product placement
-> contact shadow
-> final visual candidate
```

## Version Plan

### V2: Qwen 2511 Concept Ad Generator

Implemented as a ComfyUI workflow file:

```text
D:\CD\fc_comfyui\ComfyUI_windows_portable_soylab\ComfyUI\user\default\workflows\product_ad_qwen_2511_concept_v2.workflow.json
```

Project copy:

```text
C:\Users\jinkiwon\iCloudDrive\자동화 프로젝트\services\comfyui\workflows\product_ad_qwen_2511_concept_v2.workflow.json
```

This is the main direction for the automation project.

```text
LoadImage(product/reference image)
-> Qwen Image Edit 2511 GGUF workflow
-> SaveImage
```

Model stack used by the local workflow:

```text
qwen-image-edit-2511-Q3_K_M.gguf
qwen_2.5_vl_7b_fp8_scaled.safetensors
qwen_image_vae.safetensors
```

Purpose:

```text
product/reference image + campaign concept prompt
-> varied product ad base visual
-> exact Korean typography/layout later
```

This workflow intentionally avoids final readable Korean text. Headlines, discount badges, legal copy, CTA, and channel-specific typography should be added by the existing Korean overlay/Figma stage.

### V1: Safe Composite

Implemented as `product_locked_ad_background_v1`.

This version does not repaint the product. It loads a product image from ComfyUI input, creates a studio-style background, places the product by mask/alpha, and adds contact shadow.

```text
LoadImage(product)
-> ProductLockedAdComposite
-> SaveImage
```

Best input:

```text
transparent PNG product image
```

Fallback input:

```text
clean product photo
```

If the source has no alpha channel, the whole rectangular image is treated as the product layer.

### V3: Ad Quality / Relight

Target next version.

```text
product lock
-> AI background generation
-> product composite
-> IC-Light/Product Relighting
-> contact shadow
-> edge repair
```

### V4: Delivery Quality

Target later version.

```text
V2
-> product detail transfer
-> upscale/sharpen
-> PSD/Figma handoff
```

## Product Preservation Rules

| Element | Rule |
| --- | --- |
| product shape | preserve source |
| logo/label | preserve source |
| package texture | preserve source |
| background | generated or composited |
| lighting | adjusted around product first |
| shadow | generated from product mask |
| product repaint | disabled in V1 |

## Payload Fields

```json
{
  "workflow_preset": "product_locked_ad_background_v1",
  "product_image": "product_input.png",
  "ratio": "1:1",
  "background_style": "pharma_blue_rank",
  "product_scale": 0.58,
  "product_x_percent": 0.5,
  "product_y_percent": 0.6,
  "shadow_opacity": 0.34,
  "shadow_blur": 46,
  "shadow_offset_y": 26,
  "accent_color": "#E8F0E8"
}
```

`product_image` must exist under:

```text
D:\CD\fc_comfyui\ComfyUI_windows_portable_soylab\ComfyUI\input
```

## ComfyUI Custom Node

```text
D:\CD\fc_comfyui\ComfyUI_windows_portable_soylab\ComfyUI\custom_nodes\ComfyUI-ProductLockedAd
```

ComfyUI must be restarted after installing this node.

## ComfyUI Workflow Files

Drag this file into ComfyUI:

```text
C:\Users\jinkiwon\Downloads\comfy-workflows\product_locked_ad_background_v1.workflow.json
```

Project copy:

```text
C:\Users\jinkiwon\iCloudDrive\자동화 프로젝트\services\comfyui\workflows\product_locked_ad_background_v1.workflow.json
```

API prompt copy:

```text
C:\Users\jinkiwon\iCloudDrive\자동화 프로젝트\services\comfyui\workflows\product_locked_ad_background_v1.api.json
```

Before running the workflow, put the product image here:

```text
D:\CD\fc_comfyui\ComfyUI_windows_portable_soylab\ComfyUI\input\product_input.png
```

## Current Quality Benchmark

For cosmetic/pharma ads, use:

```json
{
  "background_style": "pharma_blue_rank",
  "ratio": "4:5",
  "product_scale": 0.58,
  "product_x_percent": 0.5,
  "product_y_percent": 0.58,
  "accent_color": "#B9D9F2"
}
```

This style is tuned toward the reference direction:

```text
clean pale blue background
large translucent rank-number graphic
centered product
soft contact shadow
white legal/footer area
```

Headline, badges, and legal copy should still be handled by the text/layout overlay stage so the product background workflow does not repaint text or logos.
