# Schemas

## Schema Strategy

Stage schemas live inside `pipeline/{stage}/` so the stage contract is self-contained. Shared canonical schemas live in `core/schemas/` and can be referenced by stage schemas as the project matures.

## Canonical Objects

- Event input
- Brand guide
- Brief
- Content plan
- Visual plan
- Image prompts
- Candidate manifest
- Selected assets
- Figma assembly plan
- Channel outputs
- QA report
- Final package manifest
- Asset archive
- Run status
- Approval

## Compatibility Rule

When a schema changes, downstream stages must either support the previous version or declare a migration path. Run artifacts should record schema version.
