# Roadmap

## Phase 1: Scaffold

- Fix repository structure from `codex_pipeline_structure.md`
- Add stage specs, schemas, and workflow state files
- Add ComfyUI and Figma service stubs

## Phase 2: First Executable Run

- Implement brief generation handler
- Implement content plan handler
- Implement run validation
- Add schema validation for stage boundaries
- Keep `docs/IMPLEMENTATION_HANDOFF.md` updated whenever workflow behavior or stage contracts change

## Phase 3: Visual and Selection Loop

- Connect ComfyUI queue adapter
- Generate candidate previews
- Build admin selection data contract
- Add regeneration by deliverable and candidate ID

## Phase 4: QA and Package

- Implement 04_admin_selection handler
- Implement 06_qa_packaging handler (input: selected-assets.json, not figma exports)
- Produce final package manifest

## Phase 5: Archive and UI

- Build asset index
- Add dashboard and review screens
- Promote reusable assets into a searchable library
