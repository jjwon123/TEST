# QA

## QA Scope

QA checks whether final assets are publishable for their intended channel. It covers file existence, dimensions, naming, required phrases, forbidden phrases, CTA presence, export format, and package completeness.

## Severity

- `blocker`: cannot publish
- `major`: publish only after explicit manager override
- `minor`: publishable with warning
- `info`: record for future improvement

## Revision Routing

Brief or claim issues go back to `01_event_brief`. Scope issues go to `02_content_planning`. Reference-fit problems go to `03_reference_research`. Visual problems go to `04_visual_candidates` or `05_admin_selection`.

For text issues in legacy Figma-based runs, QA can still inspect `05_figma_assembly/output/copy-map.json`. In the active MVP flow, QA primarily inspects selected assets, prompts, required phrases, banned phrases, and source traces.

## Workflow Integration

`qa-report.json` issues with `status=fail` or `qa_failed=true` are workflow signals. `workflow.py --process-qa-failures` reads `suggested_fix_stage` and marks the corresponding stage as `needs_regeneration` in `run-status.json`. A human can override specific issue IDs with `--qa-override`.

## Approval

QA approval unlocks archive. Archive should not ingest unapproved final outputs as reusable assets.
