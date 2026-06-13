# 01 Event Brief

## Purpose

This stage turns the raw event intake and brand guide into a normalized operating brief. It is the first agent reasoning stage and establishes the shared truth used by content planning, visual generation, Figma assembly, QA, and archive indexing.

## Position in Pipeline

Input comes from `events/{event-id}/event-input.json` and `events/{event-id}/brand-guide.json`. Output is written to the active run folder as `runs/{run-id}/01_event_brief/brief.json`.

## Primary Outputs

- `brief.json`: canonical normalized brief
- `notes.md`: human approval review summary. It explains the brief, open questions, and assumptions for the operator, but downstream stages must consume `brief.json` rather than `notes.md`.

## Human Gate

The stage stops at `brief_review`. A manager must approve the brief before content planning starts. Approval means the event objective, target, offer, tone, required phrases, banned phrases, and channel intent are accurate enough to drive downstream work.

## Extension Points

Handlers in `handlers/` should eventually implement intake validation, brand guide normalization, and diffing between revised briefs. Prompt templates in `prompts/` should remain engine-agnostic so the same spec can run through different LLM providers.
