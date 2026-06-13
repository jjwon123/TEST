# SELECTION_GUIDE.md

## Mission

Help the manager choose the visual assets that will actually be used in channel assembly.

## Inputs

- `candidate-manifest.json`
- preview image paths
- content plan deliverable metadata
- brief constraints

## Selection Options

- `selected`: use this candidate for the mapped deliverable
- `rejected`: do not use this candidate
- `regenerate`: request new candidates while preserving the deliverable
- `hold`: defer decision without blocking unrelated deliverables

## Selection Criteria

Prioritize brand fit, message fit, channel usability, text-safe area, ratio correctness, and reuse potential.

## Required Output Format

Write `selected-assets.json` with stable candidate IDs, selected file paths, deliverable mapping, manager notes, and regeneration requests.

Regeneration requests should reference `regeneration_group` from `candidate-manifest.json`. This lets the workflow regenerate a coherent candidate set instead of guessing from individual filenames.

Each request must include `group_id`, `reason`, `requested_by`, `requested_at`, and `status`. `workflow.py` reads these requests and can either print the exact regenerate command or execute it with `--auto-regenerate`.

## Handoff

`05_figma_assembly` reads selected assets and must not use rejected candidates.

If `regeneration_requests` contains requested groups, workflow should route them back to `03_visual_candidates` before assembly proceeds.

## Notes for UI

The UI should group candidates by deliverable, show crop previews, expose text overlay safe-area warnings, and support quick regeneration notes.
