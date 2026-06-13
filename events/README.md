# Events

Each event folder is operator-provided source input for a run.

```text
events/{event-id}/
├── event-input.json
├── brand-guide.json
├── references/
└── notes.md
```

Pipeline stages should not write generated outputs here. Generated outputs belong in `runs/{run-id}/`.
