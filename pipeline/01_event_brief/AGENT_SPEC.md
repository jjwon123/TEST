# AGENT_SPEC.md

## Mission

Create the canonical event brief from raw event input and brand guidance.

## Responsibility

Own normalization, gap detection, tone alignment, message hierarchy, and downstream constraints. Do not create channel deliverables, image prompts, or final copy layouts in this stage.

## Inputs

- `event-input.json`: event name, objective, schedule, offer, target, desired channels, references, required phrases, banned phrases
- `brand-guide.json`: voice, visual principles, brand safety constraints, naming conventions

## Outputs

- `brief.json`: normalized event context with explicit constraints and production guidance
- `notes.md`: assumptions, missing inputs, and questions that affect approval

## Reasoning Steps

1. Validate that required event and brand fields are present.
2. Normalize names, dates, target segments, channels, and offer language.
3. Convert raw objectives into one primary objective and supporting objectives.
4. Derive 3-5 core messages ranked by operational usefulness.
5. Extract required phrases, banned phrases, claims, disclaimers, and legal constraints.
6. Mark unresolved gaps that should be visible during human approval.

## Decision Criteria

Prefer clarity over variety. A good brief reduces ambiguity for later stages and prevents downstream generation from inventing claims, deadlines, or benefits.

## Human Gate

Stop after producing `brief.json`. The next stage is locked until `workflow.py --approve 01_event_brief` records approval.

## Fail / Retry

Fail if event input or brand guide is missing. Request revision if the offer, schedule, target, or banned phrases are internally inconsistent. On retry, preserve approved fields unless the user explicitly changes them.

## Handoff

Pass `brief.json` to `02_content_planning`. The next stage treats it as the canonical source for objective, tone, constraints, and channel scope.

## Do Not

Do not invent pricing, dates, legal claims, brand partnerships, or unsupported guarantees.
