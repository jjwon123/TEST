# Transitions

## Run Flow

`created -> briefing -> brief_review -> planning -> plan_review -> candidate_generating -> selection_pending -> assembling -> qa_pending -> archived`

## Locking Rule

Stages after a human gate remain `locked` until the required approval is recorded in `approvals.json`.

## Regeneration Rule

Regeneration moves the target stage to `needs_regeneration`, then `in_progress`, then either `review_pending`, `done`, or `blocked`.
