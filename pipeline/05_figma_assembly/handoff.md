# Handoff

`06_qa_packaging` receives channel output metadata and export expectations. QA should validate actual exported files against this plan.

`copy-map.json` is also handed off. It is not only a placement table; it is the traceability layer that tells QA where each text value originated.

## Required Handoff Fields

- `output_id`
- `deliverable_id`
- `channel_id`
- `template_id`
- `expected_export_path`
- `expected_dimensions`
- `copy_slots`
- `asset_slots`
- `copy-map.items[].source_stage`
- `copy-map.items[].source_field`
