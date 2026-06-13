# Agent Spec

## Agent Stage Contract

Agent reasoning stages are responsible for reading approved upstream context, producing structured outputs, recording assumptions, and stopping at the correct human gate.

## Required Files

- `README.md`: operator-facing description
- `AGENT_SPEC.md`: mission, responsibility, reasoning flow, gates, and fail behavior
- `input.schema.json`: accepted input shape
- `output.schema.json`: required output shape
- `decision-rules.md`: local judgment rules
- `handoff.md`: downstream contract
- `fail-cases.md`: failure and retry behavior

## Execution Expectations

Agents should not silently continue across gates. They should record uncertainty in machine-readable outputs where possible and in notes where useful.

## Boundary Rule

Agents decide stage-specific structure. Services execute external operations. UI records human decisions. `workflow.py` coordinates state.
