# Architecture

## System Definition

This repository is a multi-agent event content operations platform. One event intake becomes a controlled set of multi-channel content outputs through staged reasoning, human approvals, visual candidate generation (ComfyUI), QA, and archive indexing. Figma assembly stage has been removed.

## Architectural Layers

### Core

`core/` stores shared contracts: schemas, state machines, channel rules, template metadata, naming policy, QA policy, and utility conventions. Pipeline stages should read from core rather than duplicating business rules.

`core/channels/*.json` and `core/utils/channel_registry.py` are the single source of truth for channel identity. Aliases are accepted only at intake/planning boundaries; internal stage outputs, package manifests, archive records, tags, and reuse scoring use canonical channel IDs.

### Events

`events/{event-id}/` stores operator-provided source inputs. These files are not stage outputs. They are the starting context for a run.

### Pipeline

`pipeline/01~07/` stores executable stage specifications. Each stage is an agent unit, not just a folder. Stage specs define what to read, how to reason, where to stop for human approval, and what to hand off.

### Runs

`runs/{run-id}/` stores execution state and generated artifacts. A run is immutable enough for audit but supports versioned regeneration of stage outputs.

### Services

`services/` contains replaceable adapters. ComfyUI handles visual candidate generation. These adapters should not own pipeline decisions.

### UI

`ui/` is reserved for operator-facing review surfaces. UI screens should read and write the same JSON contracts used by CLI orchestration.

## Design Principle

JSON outputs are both results and next-stage context. The pipeline should remain inspectable and restartable at every approval gate.
