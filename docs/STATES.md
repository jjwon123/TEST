# States

## Run States

- `created`: run workspace exists
- `briefing`: event brief is being prepared
- `brief_review`: brief is waiting for approval
- `planning`: content plan is being prepared
- `plan_review`: content plan is waiting for approval
- `candidate_generating`: visual candidates are being prepared
- `selection_pending`: manager selection is required
- `qa_pending`: QA needs review or approval
- `archived`: approved assets are archived
- `failed`: a blocking error stopped the run

## Stage States

- `locked`: upstream approval is missing
- `not_started`: stage is available but not started
- `in_progress`: stage is executing
- `review_pending`: stage output needs human review
- `approved`: stage is approved
- `rejected`: stage output was rejected
- `needs_regeneration`: stage requires scoped regeneration
- `done`: stage completed without an approval requirement
- `blocked`: stage cannot proceed due to missing input or failure

## Approval Records

Approvals live in `runs/{run-id}/approvals.json`. Each approval should include stage ID, approver, status, timestamp, and note.
