# Decision Rules

## Severity

- `blocker`: cannot publish
- `major`: publish only after explicit override
- `minor`: publishable with warning
- `info`: record for future improvement

## Package Readiness

A package is ready only when every required output has a valid file, channel mapping, dimensions, and QA decision.

## Revision Routing

Send reference-fit problems to `03_reference_research`, visual generation problems to `04_visual_candidates`, selection problems to `05_admin_selection`, and brief/copy constraints back to the earliest stage that introduced the issue. Legacy Figma template problems can still point to `05_figma_assembly` when a run contains old Figma outputs.

## Workflow Signal

Each failed issue must include `suggested_fix_stage`. Workflow uses this field to set the target stage to `needs_regeneration`. Use `source_trace` from `copy-map.json` when routing text issues.
