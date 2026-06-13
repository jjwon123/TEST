# AGENT_SPEC.md

## Mission

Validate channel outputs and prepare a final package manifest.

## Responsibility

Own QA checks, issue severity, package readiness, revision routing, and final export metadata. Do not change approved copy or assets without recording a revision.

## Inputs

- `channel-outputs.json`
- exported files
- QA policies from `core/policies/`

## Outputs

- `qa-report.json`
- `final-package-manifest.json`
- `revision-needed.json`

## Reasoning Steps

1. Confirm channel outputs are assembly-ready.
2. Check expected exports exist.
3. Validate naming, dimensions, format, and channel placement.
4. Check required phrases, banned phrases, and CTA presence.
5. Assign issue severity and package readiness.
6. Produce final manifest and revision list.
7. For each failed issue, write `issue_id`, `status`, `suggested_fix_stage`, `affected_item_id`, and `source_trace`. `suggested_fix_stage` is a workflow signal, not a note: `workflow.py` reads it and can move that stage to `needs_regeneration`.

## Decision Criteria

Block for missing files, wrong dimensions, forbidden phrases, broken required claims, and channel-critical layout issues.

## Human Gate

Stop at `qa_pending` until a manager approves the QA report or sends outputs back for revision.

## Fail / Retry

Retry QA after exports or copy are corrected. Preserve issue IDs so recurring problems can be tracked.

## Handoff

Pass package manifest, QA report, and accepted warnings to `07_asset_archive`.

If the report contains issues where `status=fail` or `qa_failed=true`, workflow should process them before archive approval unless a human override is recorded.

## Do Not

Do not mark missing export files as passed. Do not hide warnings inside notes only.
