# Figma Service

## Purpose

This service isolates Figma-specific template resolution, text fitting, layer mapping, and export management from pipeline stage reasoning.

## Responsibilities

- Resolve template metadata to Figma file and node IDs
- Map copy and selected assets to template slots
- Check whether text can fit before writing to Figma
- Track expected and actual export files

## Extension Plan

The first implementation should validate template metadata locally. Later versions can add Figma MCP/API calls for frame duplication, text updates, image placement, and exports.
