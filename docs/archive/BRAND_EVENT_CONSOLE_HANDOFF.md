# Brand Event Console Handoff

## Purpose

This is a local operator dashboard, not a public homepage. It wraps the existing event automation scripts so an operator can create events, run stages, inspect references/prompts/images, and open generated folders without hunting through the filesystem.

URL when running:

```text
http://127.0.0.1:5177
```

Start command:

```bat
start_brand_event_console.bat
```

## Current Implementation

### Backend

Main file:

```text
scripts/console_server.py
```

Implemented endpoints:

- `GET /api/bootstrap`
- `GET /api/comfy/status`
- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/events`
- `GET /api/jobs`
- `POST /api/events`
- `POST /api/run-event`
- `POST /api/open-path`
- `POST /api/runs/{run_id}/references/run`
- `POST /api/runs/{run_id}/comfy/generate`
- `POST /api/runs/{run_id}/package`
- `POST /api/runs/{run_id}/stage`

The server is dependency-light: standard library HTTP server plus existing project modules.

### Manifest Builder

Main file:

```text
scripts/run_manifest.py
```

It reads existing run artifacts and writes:

```text
runs/{run-id}/run-manifest.json
```

The console uses the manifest for:

- run status
- completed steps
- reference counts
- prompt counts
- generated image counts
- preview image URLs
- folder open targets

### Frontend

Current files:

```text
ui/console/index.html
ui/console/app.js
ui/console/styles.css
```

Screens:

- Dashboard
- New Event
- Run Detail
- Reference Control
- Prompt Candidates
- Generated Images
- Output Package
- Settings

## ComfyUI Behavior

The UI checks:

```text
http://127.0.0.1:8188/system_stats
```

If ComfyUI is off, `Generated Images` shows a disconnected ComfyUI status.

Live generation requires ComfyUI running at:

```text
http://127.0.0.1:8188
```

Required ComfyUI-side assets:

```text
D:\CD\fc_comfyui\ComfyUI_windows_portable_soylab\ComfyUI\custom_nodes\ComfyUI-KoreanTextOverlay
D:\CD\fc_comfyui\ComfyUI_windows_portable_soylab\ComfyUI\input\qwen_image_edit_1024.png
```

The UI calls the same workflow as CLI with:

```text
COMFYUI_GENERATION_MODE=live
python scripts/workflow.py --mode regenerate --run {run_dir} --stage 03_visual_candidates --group {group_id}
```

If ComfyUI is not reachable, candidate manifest records `generation_status: failed`. The old gradient blocks are placeholder images, not real output.

## Important Current Limitation

The current default preset is `korean_poster_overlay_1024`, which is a simple overlay-oriented ComfyUI graph. It is not a full generative visual design pipeline. It can prove the queue/output loop, but the next quality step is replacing or expanding the workflow preset so it actually generates useful campaign visuals from reference images and prompts.

## Reference Control

The UI can rerun reference search and Qwen review for an existing run:

```text
POST /api/runs/{run_id}/references/run
```

Controls:

- query limit
- per-query image limit
- select count
- Qwen review limit

This maps to:

```text
python scripts/workflow.py --run {run_dir} --run-reference-pipeline --reference-update-03 --reference-reviewer qwen ...
```

## Folder Buttons

The console can open these folders through `POST /api/open-path`:

- run folder
- downloaded reference candidates
- selected references
- generated images
- production package

The backend only opens paths inside the project root.

## Verification Performed

Verified after the console changes:

```text
python -m py_compile scripts/run_manifest.py scripts/console_server.py
GET /api/bootstrap
GET /api/comfy/status
Browser render for Reference Control and Generated Images
No 404 responses or JavaScript errors during browser check
```

Additional cleanup pass on 2026-05-18:

```text
GET /api/jobs/{job_id}/log added for background job log inspection
UI job cards now expose a small log panel
.tmp/console-verify removed as stale browser verification output
legacy corrupted CLAUDE_PROGRESS files removed from the active workspace
```

ComfyUI status at last check:

```text
connected: false
url: http://127.0.0.1:8188
```

## Next Work

1. Replace the placeholder/overlay ComfyUI preset with a real campaign visual generation workflow.
2. Add stronger per-candidate selection summaries in `Generated Images`.
3. Persist UI control defaults per project or run.
4. Add a simple ComfyUI setup checklist panel when `/api/comfy/status` is disconnected.
5. Run one clean 04→06→07 end-to-end pass on the latest event (05_figma_assembly removed from pipeline).

## Pipeline Change Note (2026-05-18)

`05_figma_assembly` has been removed from the active pipeline. Stage order is now:
01 → 02 → 03 → 04 → 06 → 07

`04_admin_selection` now unlocks `06_qa_packaging` directly.
