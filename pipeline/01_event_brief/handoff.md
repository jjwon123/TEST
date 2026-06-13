# Handoff

`02_content_planning` receives `brief.json` and must not reinterpret the raw event input unless the brief records a gap. The planning stage may propose channel deliverables only inside the approved channel scope.

## Required Handoff Fields

- `event_id`
- `event_name`
- `brand`
- `objective`
- `target`
- `schedule`
- `offer`
- `channels`
- `core_messages`
- `constraints`
- `approval_status`

## Handoff Risk

If the brief is not approved, downstream stages may generate assets from unverified assumptions. `workflow.py` should keep later stages locked until approval is recorded.
