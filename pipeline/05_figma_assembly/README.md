# 05 Figma Assembly

## Purpose

This stage maps selected assets and channel copy into Figma template metadata. It produces a concrete assembly plan before direct Figma automation is introduced.

## Position in Pipeline

Inputs are selected assets, content plan, brief, and template metadata. Outputs feed QA and packaging.

## Primary Outputs

- `figma-assembly-plan.json`
- `copy-map.json`: text-to-frame mapping with `source_stage` and `source_field` for QA traceability
- `channel-outputs.json`

## Human Gate

The stage can stop for template mismatch or missing export confirmation. Once Figma exports exist, QA can proceed.

## Extension Points

The service layer under `services/figma/` owns Figma API/MCP calls, text fitting, export management, and file registry resolution.
