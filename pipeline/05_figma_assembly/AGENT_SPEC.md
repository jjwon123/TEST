# AGENT_SPEC.md

## Mission

Map selected assets and copy into channel templates and produce export-ready assembly instructions.

## Responsibility

Own template selection, text slot mapping, asset placement intent, export checklist, and channel output metadata. Do not bypass manager asset selection.

## Inputs

- `brief.json`
- `content-plan.json`
- `selected-assets.json`
- template metadata from `core/templates/`

## Outputs

- `figma-assembly-plan.json`
- `copy-map.json`
- `channel-outputs.json`

## Reasoning Steps

1. Confirm selected assets are approved.
2. Resolve each deliverable to a template.
3. Map copy slots from brief and content plan.
   Each `copy-map.json` item must include `source_stage` and `source_field` so QA can trace whether text came from `01_event_brief.core_messages`, `02_content_planning` planning fields, `04_admin_selection`, or a manual override.
4. Assign selected assets to visual slots.
5. Check text length, safe area, ratio, and export requirements.
6. Produce channel output records for QA.

## Decision Criteria

Template fit beats decorative ambition. A deliverable is assembly-ready only when every required text and visual slot has a mapped source.

## Human Gate

Pause when template metadata is missing, selected files are missing, or text cannot fit the target template.

## Fail / Retry

Retry affected deliverables after template updates, copy edits, or asset replacement.

## Handoff

Pass `channel-outputs.json`, `copy-map.json`, and expected export paths to `06_qa_packaging`. QA uses `source_stage` and `source_field` to decide whether a copy issue should route back to brief, planning, selection, or assembly.

## Do Not

Do not use rejected assets. Do not silently shrink text below template policy.
