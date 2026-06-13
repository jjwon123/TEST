# Fail Cases

## Blocking Failures

- Missing approved content plan
- No ComfyUI preset available for required visual role
- Candidate manifest cannot map to deliverable IDs

## Generation Failures

- ComfyUI queue timeout
- Output path missing after generation
- Generated image has wrong ratio or unsafe content

## Retry Rules

Regenerate by `candidate_id`, `deliverable_id`, or `visual_role`. Preserve the original manifest entry and write new files with versioned paths.
