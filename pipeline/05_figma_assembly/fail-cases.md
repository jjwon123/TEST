# Fail Cases

## Blocking Failures

- Missing selected assets
- No matching Figma template
- Required template slot has no source
- Export checklist cannot be generated

## Review Failures

- Text too long for slot
- Selected image conflicts with safe area
- Channel output has ambiguous filename

## Retry Rules

Regenerate only affected `output_id` records. Preserve export names when downstream QA already references them.
