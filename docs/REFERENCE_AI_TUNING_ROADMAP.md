# Reference AI Tuning Roadmap

Goal: make the local reference collector learn what this project considers a good event-content visual reference.

## Phase 1: Program Setup

Status: active.

The program flow is:

1. Start local Qwen-VL server with `start_reference_ai.bat`.
2. Run search, download, heuristic ranking, Qwen review, and report generation with `run_reference_ai_review.bat`.
3. Review `runs/_reference_search_benchmark/benchmark-evaluation.csv`.
4. Save human or AI-seeded feedback with `save_reference_feedback.bat`.

The criteria are editable in:

```txt
assets/references/review-criteria.json
```

## Phase 2: Criteria Tuning

Change the criteria file when Qwen makes repeated mistakes.

Useful signals:

- Qwen selects visually attractive but off-category images.
- Qwen overvalues mood and undervalues product clarity.
- Qwen selects images with no copy space.
- Qwen rejects useful layouts because the product differs too much.
- Qwen misses Korean ad/detail-page practicality.

After each criteria change, run a small benchmark:

```powershell
run_reference_ai_review.bat tube-spring 1 3 2 3
```

Then compare:

- `review_decision`
- `event_fit`
- `category_fit`
- `copy_space`
- `layout_idea`
- `ai_reason`
- `human_decision`

## Phase 3: Feedback Learning

Feedback lives in:

```txt
assets/references/feedback.jsonl
```

Treat feedback strength like this:

- `source_type: human`: trusted training signal
- `source_type: ai`: useful bootstrap signal, but weaker than human confirmation

Minimum useful dataset:

- 30 positive human examples
- 30 negative human examples
- at least 3 product categories
- at least 3 common rejection reasons

Train the lightweight CLIP classifier:

```powershell
.venv\Scripts\python.exe scripts\reference_vision.py train --cache runs\[run-dir]\04_admin_selection\clip-embeddings.npz --feedback assets\references\feedback.jsonl --model-path assets\references\reference-classifier.joblib
```

Use it for ranking:

```powershell
.venv\Scripts\python.exe scripts\reference_vision.py rank --cache runs\[run-dir]\04_admin_selection\clip-embeddings.npz --model-path assets\references\reference-classifier.joblib --output runs\[run-dir]\04_admin_selection\reference-ranking.json --top-k 20
```

## Phase 4: Model Tuning Gate

Do not fine-tune Qwen-VL yet.

Only consider Qwen-VL LoRA after:

- 500 positive labeled images
- 500 negative labeled images
- labels are consistent across at least 5 event categories
- prompt/criteria tuning has plateaued
- CLIP classifier improves ranking but cannot solve visual reasoning mistakes

Before LoRA, export a dataset with:

- image path
- event context
- criteria version
- human decision
- human score
- tags
- short reason

## Current Recommendation

Keep Qwen-VL as the visual reviewer, keep criteria in JSON, and use feedback to tune ranking first. This gives the fastest improvement without heavy GPU training or fragile model fine-tuning.

