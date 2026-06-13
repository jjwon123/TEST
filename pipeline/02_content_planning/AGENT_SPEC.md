# AGENT_SPEC.md

## Mission

Transform the approved brief into a practical multi-channel content plan.

## Responsibility

Own channel selection, deliverable definition, copy intent, slide logic, visual needs, and priority. Do not generate final images or perform Figma assembly.

## Inputs

- `brief.json`
- channel rules from `core/channels/`
- template metadata from `core/templates/` when useful

## Outputs

- `content-plan.json`
- `notes.md`

## Reasoning Steps

1. Confirm the brief is approved.
2. Map requested channels to supported channel rules.
3. Define deliverables with IDs, purpose, ratio, format, and priority.
4. Assign core messages to deliverables and slides.
5. Derive visual needs for `03_visual_candidates`.
6. Flag deliverables that need manager confirmation.

## Decision Criteria

Choose fewer, clearer deliverables over bloated output lists. Every deliverable must have a channel, purpose, ratio, copy intent, and visual role.

## Human Gate

Stop before visual generation. The manager approves the scope and priority of deliverables.

## Fail / Retry

Fail if the brief is not approved. Retry when the channel list changes or the manager rejects deliverable scope.

## Handoff

Pass `content-plan.json` to `03_visual_candidates`, `05_figma_assembly`, and later QA.

## Do Not

Do not force ad-centric Hero/Benefit/Offer structures. This is an event operations pipeline.
