# Handoff

`04_admin_selection` receives a candidate manifest and preview paths. Every candidate must link back to a deliverable or visual role so selected assets can map into Figma templates.

`regeneration_group` is the workflow key for scoped regeneration. When `04_admin_selection` requests "regenerate this group", it should pass the group ID to `workflow.py --mode regenerate --group {group_id}` rather than naming individual files manually.

## Required Handoff Fields

- `candidate_id`
- `deliverable_id`
- `regeneration_group`
- `visual_role`
- `channel_id`
- `ratio`
- `preview_path`
- `source_prompt_id`
- `text_safety`
- `generation_status`

## Handoff Risk

Missing candidate IDs make regeneration and asset archiving unreliable. IDs must remain stable across preview refreshes.

Missing regeneration groups make selective regeneration unreliable. Every candidate must belong to exactly one manifest-defined group.
