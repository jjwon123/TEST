# Run Model

A run is one execution of the pipeline for one event. It owns `run-status.json`, `approvals.json`, logs, stage output folders, and versioned regenerated artifacts.

Runs should be restartable from any approved gate. They should not overwrite previous approved outputs without versioning.
