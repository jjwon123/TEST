# Reference Quality Review

Pinterest reference search now produces a reviewable quality table in addition to the image report.

## Benchmark With Quality Table

```powershell
.venv\Scripts\python.exe scripts\reference_search_benchmark.py --prepare --run --case tube-spring --query-limit 1 --per-query-limit 3 --select-count 2
```

Outputs:

- `runs/_reference_search_benchmark/benchmark-report.json`
- `runs/_reference_search_benchmark/benchmark-report.md`
- `runs/_reference_search_benchmark/benchmark-evaluation.csv`
- `runs/_reference_search_benchmark/benchmark-evaluation.json`
- `runs/_reference_search_benchmark/benchmark-feedback-template.jsonl`

The evaluation table includes search query, selected image path, image quality score, text relevance score, optional Qwen-VL scores, weighted quality grade, and blank human review fields.

## Local Program Files

Use these from the project root:

```powershell
start_reference_ai.bat
```

Starts the local Ollama Qwen-VL server and runs a health check.

```powershell
run_reference_ai_review.bat tube-spring 1 3 2 3
```

Runs Pinterest reference search and Qwen-VL review.

Arguments:

- `tube-spring`: benchmark case id
- `1`: query limit
- `3`: images per query
- `2`: selected image count
- `3`: Qwen review limit

```powershell
save_reference_feedback.bat runs\_reference_search_benchmark\benchmark-evaluation.csv assets\references\feedback.jsonl ai
```

Appends feedback rows. Use `ai` to seed feedback from Qwen decisions when human fields are blank. Omit the third argument to append only human-filled rows.

## Connected Event Automation

Use this when you want the real event pipeline to run through 03 visual candidates with AI-reviewed references:

```powershell
run_event_with_reference_ai.bat events\sample 1 2 1 1
```

Arguments:

- `events\sample`: event folder
- `1`: generated Pinterest queries to process
- `2`: images to collect per query
- `1`: selected references to keep
- `1`: candidates sent to Qwen-VL

This command:

1. Starts/uses the local Qwen-VL server.
2. Creates a new run from the event folder.
3. Runs and auto-approves `01_event_brief`.
4. Runs and auto-approves `02_content_planning`.
5. Runs Pinterest reference search and Qwen image review.
6. Regenerates `03_visual_candidates` with selected reference traces.
7. Writes `references/reference-ai-summary.json`.

Important outputs inside the created run:

- `references/reference-manifest.json`
- `references/qwen-reviewed-candidates.json`
- `references/selected/`
- `03_visual_candidates/visual-plan.json`
- `03_visual_candidates/image-prompts.json`
- `03_visual_candidates/candidate-manifest.json`

## Editable Criteria

The reviewer rubric lives here:

```txt
assets/references/review-criteria.json
```

You can change this file later without changing code. It controls:

- scoring dimensions
- positive/negative feedback tags
- hard reject rules
- minimum feedback counts for later tuning

## Qwen-VL Review

Start Ollama first, then run the benchmark with the Qwen reviewer:

```powershell
$env:OLLAMA_MODELS="C:\tmp\ollama-models"
C:\tmp\ollama\ollama.exe serve
```

```powershell
.venv\Scripts\python.exe scripts\reference_search_benchmark.py --prepare --run --case tube-spring --query-limit 1 --per-query-limit 3 --select-count 2 --reviewer qwen --review-limit 3
```

Qwen output is saved per run:

```txt
runs/[run-dir]/references/qwen-reviewed-candidates.json
```

The benchmark table copies these fields into each selected row when available:

- `review_decision`
- `review_score`
- `event_fit`
- `category_fit`
- `copy_space`
- `ai_role`
- `ai_reason`
- `ai_risk`

## Human Feedback Loop

Fill these columns in `benchmark-evaluation.csv`:

- `human_decision`: `approved`, `selected`, `shortlist`, `rejected`, `bad`, or `good`
- `human_score`: optional 1-100 score
- `human_notes`: why it worked or failed
- `feedback_tags`: comma-separated tags such as `off-category`, `good-copy-space`, `too-stock`

Append filled rows into the shared feedback log:

```powershell
.venv\Scripts\python.exe scripts\reference_vision.py feedback-from-table --table runs\_reference_search_benchmark\benchmark-evaluation.csv --output assets\references\feedback.jsonl
```

Seed feedback from AI decisions:

```powershell
.venv\Scripts\python.exe scripts\reference_vision.py feedback-from-table --table runs\_reference_search_benchmark\benchmark-evaluation.csv --output assets\references\feedback.jsonl --include-ai-decisions
```

Then train the CLIP feedback model when there are at least one positive and one negative records:

```powershell
.venv\Scripts\python.exe scripts\reference_vision.py train --cache runs\[run-dir]\04_admin_selection\clip-embeddings.npz --feedback assets\references\feedback.jsonl --model-path assets\references\reference-classifier.joblib
```
