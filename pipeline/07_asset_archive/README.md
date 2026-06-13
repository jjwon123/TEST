# 07 Asset Archive

## Purpose

This archive/index stage turns final event outputs into reusable operating assets. It records where files came from, how they were used, what passed QA, and what can be reused in future events.

## Position in Pipeline

Inputs are the final package manifest, QA report, selected assets, and copy map. Outputs become searchable archive metadata.

## Primary Outputs

- `asset-archive.json`
- `reuse-notes.md`

## Extension Points

Future handlers can write to a database, vector index, asset library UI, or object storage. The JSON archive remains the portable source of truth.
