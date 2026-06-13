# Templates

## Purpose

Template metadata lets the pipeline reason about Figma outputs before it touches a Figma file. It describes available frames, slots, constraints, ratios, and export rules.

## Required Metadata

- `template_id`
- `channel_id`
- `figma_file_key`
- `figma_node_id`
- `ratio`
- `text_slots`
- `visual_slots`
- `max_text_length`
- `safe_area`
- `cta_slot`
- `export_rule`

## Operating Rule

Figma automation should never guess slot meaning from layer names alone. Template metadata is the contract between planning, assembly, QA, and export.
