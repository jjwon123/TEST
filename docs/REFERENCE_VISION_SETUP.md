# Reference Vision Setup

이 세팅은 Qwen-VL을 메인 분류기로 쓰지 않고, OpenCLIP + scikit-learn 랭킹 뒤에 설명용 비전 심사위원으로 붙인다.

## Runtime

- Python: `C:\tmp\Python311`
- Project venv: `.venv`
- Ollama CLI: `C:\tmp\ollama\ollama.exe`
- Ollama models: `C:\tmp\ollama-models`
- Local model: `qwen2.5vl:7b`

Ollama 서버 시작:

```powershell
$env:OLLAMA_MODELS="C:\tmp\ollama-models"
C:\tmp\ollama\ollama.exe serve
```

상태 확인:

```powershell
.venv\Scripts\python.exe scripts\reference_vision.py health
```

## Workflow

1. 후보 이미지를 임베딩한다.

```powershell
.venv\Scripts\python.exe scripts\reference_vision.py embed `
  --images runs\[run-dir]\03_visual_candidates\previews `
  --cache runs\[run-dir]\04_admin_selection\clip-embeddings.npz
```

2. 초기에는 좋은 레퍼런스 폴더와의 유사도로 랭킹한다.

```powershell
.venv\Scripts\python.exe scripts\reference_vision.py rank `
  --cache runs\[run-dir]\04_admin_selection\clip-embeddings.npz `
  --positive-reference-dir assets\references\approved `
  --output runs\[run-dir]\04_admin_selection\reference-ranking.json `
  --top-k 20
```

3. 피드백이 쌓이면 `feedback.jsonl`로 분류기를 학습한다.

```jsonl
{"file":"candidate_01.png","decision":"approved"}
{"file":"candidate_02.png","decision":"rejected"}
```

```powershell
.venv\Scripts\python.exe scripts\reference_vision.py train `
  --cache runs\[run-dir]\04_admin_selection\clip-embeddings.npz `
  --feedback assets\references\feedback.jsonl `
  --model-path assets\references\reference-classifier.joblib
```

4. 학습 모델로 랭킹한다.

```powershell
.venv\Scripts\python.exe scripts\reference_vision.py rank `
  --cache runs\[run-dir]\04_admin_selection\clip-embeddings.npz `
  --model-path assets\references\reference-classifier.joblib `
  --output runs\[run-dir]\04_admin_selection\reference-ranking.json `
  --top-k 20
```

5. 상위 후보만 Qwen2.5-VL로 설명 평가한다.

```powershell
.venv\Scripts\python.exe scripts\reference_vision.py review `
  --ranked runs\[run-dir]\04_admin_selection\reference-ranking.json `
  --output runs\[run-dir]\04_admin_selection\qwen-review.json `
  --limit 10
```

