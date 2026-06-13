# 04 Admin Selection

## Purpose

This is the human decision stage. The system presents visual candidates, but the manager decides which assets are selected, rejected, held, or sent back for regeneration.

## Position in Pipeline

Inputs are `candidate-manifest.json` and generated preview files. Outputs feed Figma assembly.

## Primary Outputs

- `selected-assets.json`: selected candidate-to-deliverable mapping
- `selection-notes.md`: manager rationale and regeneration notes

`selected-assets.json.regeneration_requests` is executable workflow input, not only review commentary. Each request points to a `regeneration_group` created by `03_visual_candidates`.

## Human Gate

Approval here means selected assets are ready to be used by Figma assembly. Without this approval, downstream assembly remains locked.

## Extension Points

Future UI should render a grid grouped by deliverable, expose side-by-side comparison, and write decisions back to the same output schema.
