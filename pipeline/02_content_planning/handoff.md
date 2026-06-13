# Handoff

`03_visual_candidates` reads `content-plan.json` to decide which visual candidates are needed. `05_figma_assembly` later uses the same file to map selected assets into templates.

## Required Handoff Fields

- `deliverables[].deliverable_id`
- `deliverables[].channel_id`
- `deliverables[].format`
- `deliverables[].ratio`
- `deliverables[].purpose`
- `deliverables[].copy_intent`
- `deliverables[].visual_need`
- `deliverables[].priority`

## Handoff Risk

If deliverable IDs change after visual candidates are generated, selection and Figma mapping will break. Regeneration should preserve IDs whenever possible.
