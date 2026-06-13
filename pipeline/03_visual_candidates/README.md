# 03 Visual Candidates

## Purpose

This stage creates a visual generation plan, ComfyUI-ready prompt payloads, and a candidate manifest. It does not assume the first generated image is final. It creates a controlled candidate set for manager selection.

## Position in Pipeline

Inputs are the approved `brief.json` and `content-plan.json`. Outputs feed `04_admin_selection`.

## Primary Outputs

- `visual-plan.json`: strategy, style direction, candidate counts, safety notes
- `image-prompts.json`: structured prompt payloads for ComfyUI adapters
- `candidate-manifest.json`: expected candidate IDs, deliverable mapping, and review metadata

`candidate-manifest.json` also defines `regeneration_groups`. These groups are not descriptive metadata only; they are execution scopes used by `workflow.py --mode regenerate --group {group_id}` and later by `04_admin_selection` regeneration requests.

## Human Gate

The stage completes when candidates are generated or queued and are ready for selection.

## Extension Points

The service layer under `services/comfyui/` owns API queueing, workflow presets, prompt building, and postprocessing. This stage owns what should be generated and why.
