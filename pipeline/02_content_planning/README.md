# 02 Content Planning

## Purpose

This stage converts the approved brief into a channel-by-channel production plan. It decides what needs to be made, why it exists, and what downstream visual and template requirements each deliverable creates.

## Position in Pipeline

Input is `runs/{run-id}/01_event_brief/brief.json`. Output is `runs/{run-id}/02_content_planning/content-plan.json`.

## Primary Outputs

- `content-plan.json`: channel plans, deliverables, copy intent, visual needs, priority
- `notes.md`: planning assumptions and unresolved channel questions

## Human Gate

The stage stops at `plan_review`. Approval means the deliverable list is operationally correct before visual candidate work starts.

## Extension Points

Channel rules should come from `core/channels/`. Template compatibility should reference `core/templates/` without directly creating Figma frames.

## Registry Use

This stage must not hardcode channel-to-template mappings. It resolves requested channels through `core/utils/channel_registry.py`, then reads template metadata through `core/utils/template_registry.py`. Adding a channel or template should require registry data changes, not handler code changes.
