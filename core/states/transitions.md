# Transitions

## Run Flow

`created -> briefing -> brief_review -> planning -> plan_review -> reference_research -> reference_ready -> candidate_generating -> selection_pending -> qa_pending -> review_pending -> archived|archived_no_assets`

## Locking Rule

Stages after a human gate remain `locked` until the required approval is recorded in `approvals.json`.

## Regeneration Rule

Regeneration moves the target stage to `needs_regeneration`, then `in_progress`, then either `review_pending`, `done`, or `blocked`.
