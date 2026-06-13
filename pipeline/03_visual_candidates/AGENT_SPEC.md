# AGENT_SPEC.md

## Mission

Generate the visual candidate strategy and machine-readable prompt plan for ComfyUI.

## Responsibility

Own visual roles, candidate diversity, prompt constraints, text-safe area intent, and candidate metadata. Do not choose final assets.

## Inputs

- `brief.json`
- `content-plan.json`
- ComfyUI workflow presets from `services/comfyui/presets/`

## Outputs

- `visual-plan.json`
- `image-prompts.json`
- `candidate-manifest.json`

## Reasoning Steps

1. Confirm brief and content plan are approved.
2. Group deliverables by reusable visual role.
3. Choose candidate count and diversity axes per visual role.
4. Build prompt payloads with style, composition, ratio, and negative constraints.
5. Add text safety metadata for future Figma overlay.
6. Register candidate IDs and `regeneration_group` values in the manifest before generation.
7. Treat `regeneration_group` as the workflow execution key used by `04_admin_selection` and `workflow.py --mode regenerate --group`.

## Decision Criteria

Visual candidates must support channel assembly, not just look attractive. Prefer compositions with clean overlay zones, brand fit, and reusable campaign logic.

## Human Gate

Stop after candidate manifest and generated previews are ready. Manager selection happens in `04_admin_selection`.

## Fail / Retry

Fail if no approved content plan exists. Retry individual regeneration groups when candidates are off-brand, unusable for text, or visually redundant. A group may represent a deliverable, visual role, or another manifest-defined scope.

## Handoff

Pass `candidate-manifest.json`, preview file paths, and regeneration group membership to `04_admin_selection`.

## Do Not

Do not hard-code Midjourney as the primary engine. ComfyUI is the target visual generation adapter.
