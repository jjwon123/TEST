# Handoff Index

Use this file as the first stop when resuming work. The repository has several handoff-style files, but they serve different purposes.

## Read First

1. `docs/BRAND_EVENT_CONSOLE_HANDOFF.md`
   - Current local web dashboard state.
   - What was built, how to run it, ComfyUI connection behavior, and next fixes.

2. `docs/IMPLEMENTATION_HANDOFF.md`
   - Older but still useful whole-pipeline architecture and workflow handoff.
   - Treat stage details as broad context; verify against current code before changing behavior.

3. `services/comfyui/README.md`
   - ComfyUI live generation requirements and command-line mode.

## Stage Contract Files

These are not general project handoffs. They document stage-to-stage contracts:

- `pipeline/01_event_brief/handoff.md`
- `pipeline/02_content_planning/handoff.md`
- `pipeline/03_visual_candidates/handoff.md`
- `pipeline/04_admin_selection/handoff.md`
- `pipeline/06_qa_packaging/handoff.md`
- ~~`pipeline/05_figma_assembly/handoff.md`~~ (단계 제거됨, 파일은 archive 참고용으로 보존)

Read these only when changing that stage's inputs, outputs, approval behavior, or regeneration contract.

## UI Files

- `ui/console/README.md`: how to start the current local console.
- `ui/README.md`: UI layer overview.
- `ui/dashboard/README.md`, `ui/candidate-selection/README.md`, etc.: earlier screen placeholders, not the active implementation.

## Low-Trust / Legacy Notes

- The old root `CLAUDE_PROGRESS.MD` and `CLAUDE_PROGRESS.txt` files were removed after the current handoff documents became the source of truth.
- Root-level old stage folders such as `01_event_brief/` and `03_image_candidates/` may contain examples or legacy outputs. The canonical executable stage implementation is under `pipeline/`.

## Current Source Of Truth For The Console

- Server: `scripts/console_server.py`
- Manifest builder: `scripts/run_manifest.py`
- UI: `ui/console/index.html`, `ui/console/app.js`, `ui/console/styles.css`
- Launcher: `start_brand_event_console.bat`
