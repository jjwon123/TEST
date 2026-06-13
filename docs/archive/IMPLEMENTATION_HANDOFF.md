# Implementation Handoff

## Current Goal

Build an event content automation platform where one event intake becomes a staged multi-channel content production run. This is not a one-shot JSON generator. Each pipeline stage is an executable unit with schemas, state transitions, approval gates, and handoff contracts.

## Current UI Update

The local operator dashboard now exists as `Brand Event Console`.

Read the current console handoff first:

- `docs/BRAND_EVENT_CONSOLE_HANDOFF.md`
- `docs/HANDOFF_INDEX.md`

Active console files:

- `scripts/console_server.py`
- `scripts/run_manifest.py`
- `ui/console/index.html`
- `ui/console/app.js`
- `ui/console/styles.css`
- `start_brand_event_console.bat`

This dashboard wraps existing workflow scripts and reads/writes the same `runs/` JSON artifacts. It is not a public homepage.

## Source of Truth

Use `codex_pipeline_structure.md` as the product/architecture source of truth.

The implemented scaffold follows this structure:

- `core/`: shared schemas, models, states, channels, templates, policies, utilities
- `events/`: source event inputs
- `pipeline/`: stage specs and handlers
- `runs/`: generated run workspaces
- `assets/`: approved/rejected/reusable/exported/indexed assets
- `services/`: LLM, ComfyUI, Figma, storage, notification boundaries
- `ui/`: future operator screens
- `scripts/`: workflow orchestration
- `docs/`: architecture and process documentation

## Implemented Pipeline State

### 01_event_brief

Implemented as a deterministic handler:

- Handler: `pipeline/01_event_brief/handlers/generate_brief.py`
- Output: `runs/{run-id}/01_event_brief/brief.json`
- Notes: `runs/{run-id}/01_event_brief/notes.md`
- State after run: `stage_status.01_event_brief = review_pending`
- Run state after run: `brief_review`

The handler validates against:

- `pipeline/01_event_brief/input.schema.json`
- `pipeline/01_event_brief/output.schema.json`
- `core/schemas/brief.schema.json`

### 02_content_planning

Implemented as a data-driven handler:

- Handler: `pipeline/02_content_planning/handlers/generate_content_plan.py`
- Uses `core/utils/channel_registry.py`
- Uses `core/utils/template_registry.py`
- Output: `runs/{run-id}/02_content_planning/content-plan.json`
- State after run: `review_pending`
- Run state after run: `plan_review`

Important rule: channel/template mapping must stay in registry data, not handler code.

### 03_visual_candidates

Implemented as a manifest-first handler:

- Handler: `pipeline/03_visual_candidates/handlers/generate_visual_candidates.py`
- Does not call ComfyUI yet
- Creates:
  - `visual-plan.json`
  - `image-prompts.json`
  - `candidate-manifest.json`

Important rule: `regeneration_group` is an executable workflow key, not just metadata.

Manual regeneration:

```bash
python3 scripts/workflow.py --run runs/{run-id} --stage 03_visual_candidates --mode regenerate --group {group_id}
```

### 04_admin_selection

Schema and workflow integration are prepared, but the handler/UI is not implemented yet.

`selected-assets.json.regeneration_requests` is executable workflow input. Each request must include:

- `group_id`
- `reason`
- `requested_by`
- `requested_at`
- `status`

Workflow can read the requests:

```bash
python3 scripts/workflow.py --run runs/{run-id} --process-regeneration-requests
```

Or execute them:

```bash
python3 scripts/workflow.py --run runs/{run-id} --process-regeneration-requests --auto-regenerate
```

### 06_qa_packaging

Schema and workflow integration are prepared, but the QA handler is not implemented yet.

`qa-report.json` issues must include:

- `issue_id`
- `status`
- `suggested_fix_stage`
- `affected_item_id`
- `source_trace`

Workflow can process failed QA issues:

```bash
python3 scripts/workflow.py --run runs/{run-id} --process-qa-failures
```

Dry run:

```bash
python3 scripts/workflow.py --run runs/{run-id} --process-qa-failures --dry-run
```

Override:

```bash
python3 scripts/workflow.py --run runs/{run-id} --process-qa-failures --qa-override {issue_id}
```

### 07_asset_archive

Scaffold and schema are present. Handler is not implemented yet.

## Core Utilities

Implemented:

- `core/utils/json_io.py`
- `core/utils/schema_validation.py`
- `core/utils/module_loader.py`
- `core/utils/channel_registry.py`
- `core/utils/template_registry.py`

`workflow.py` uses file-path based dynamic loading via `module_loader.py` because stage folders are named like `01_event_brief`, which are not convenient Python package names.

## Workflow Orchestrator

Main file:

- `scripts/workflow.py`

Supported commands:

```bash
python3 scripts/workflow.py --setup --event events/sample
python3 scripts/workflow.py --list-stages
python3 scripts/workflow.py --run runs/{run-id} --stage 01_event_brief
python3 scripts/workflow.py --run runs/{run-id} --approve 01_event_brief
python3 scripts/workflow.py --run runs/{run-id} --stage 03_visual_candidates --mode regenerate --group {group_id}
python3 scripts/workflow.py --run runs/{run-id} --process-regeneration-requests
python3 scripts/workflow.py --run runs/{run-id} --process-qa-failures
```

Run state is stored in:

- `runs/{run-id}/run-status.json`
- `runs/{run-id}/approvals.json`
- `runs/{run-id}/logs/`

## Important Design Decisions

1. Stage output schemas and core canonical schemas should stay aligned.
2. JSON outputs are both final stage output and next-stage input context.
3. Human gates are represented in workflow state, not only in docs.
4. `regeneration_group` links `03_visual_candidates -> 04_admin_selection -> workflow regenerate`.
5. `qa-report.suggested_fix_stage` links `06_qa_packaging -> workflow needs_regeneration`.
6. `05_figma_assembly` has been removed. `04_admin_selection` now unlocks `06_qa_packaging` directly.
7. Handlers should stay thin. Shared loading/registry behavior belongs in `core/utils/`.
8. External integrations should stay behind `services/`.

## Next Implementation Priorities

1. Implement `04_admin_selection` handler or minimal CLI helper that creates `selected-assets.json`.
2. Implement `06_qa_packaging` handler using `selected-assets.json` and QA policies (no longer depends on figma outputs).
3. Add schema validation to every workflow stage boundary consistently.
4. Connect `03_visual_candidates` to `services/comfyui` dry-run payloads, then actual queue calls.
5. Implement `07_asset_archive` promotion and indexing.
6. Add `runs/{run-id}/handoff.md` auto-generation after each stage.

## Known Gaps

- `04_admin_selection` has schema and workflow hooks but no handler/UI.
- `06_qa_packaging` has schema and workflow hooks but no handler.
- `03_visual_candidates` does not call ComfyUI yet.
- `05_figma_assembly` folder/files still exist on disk but are no longer part of the active pipeline. Safe to archive or delete.
- Some older root-level folders still exist from the previous structure. The newer canonical structure is under `pipeline/`.
- Existing old `runs/` folders may not match the new `03_visual_candidates` naming and should be treated as migration references.

## Verification Commands

Use these after changes:

```bash
python3 -m py_compile scripts/workflow.py
find core pipeline -name '*.json' -print0 | xargs -0 -n 1 python3 -m json.tool >/dev/null
python3 scripts/workflow.py --list-stages
```

Basic end-to-end scaffold check:

```bash
python3 scripts/workflow.py --setup --event events/sample
python3 scripts/workflow.py --run runs/{run-id} --stage 01_event_brief
python3 scripts/workflow.py --run runs/{run-id} --approve 01_event_brief
python3 scripts/workflow.py --run runs/{run-id} --stage 02_content_planning
python3 scripts/workflow.py --run runs/{run-id} --approve 02_content_planning
python3 scripts/workflow.py --run runs/{run-id} --stage 03_visual_candidates
```
