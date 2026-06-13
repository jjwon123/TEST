# 06 QA Packaging

## Purpose

This stage validates final channel outputs and prepares a package manifest for distribution. It is the last quality gate before assets become reusable archive material.

## Position in Pipeline

Inputs are `channel-outputs.json`, Figma exports, QA policies, and naming/export rules. Outputs feed `07_asset_archive`.

## Primary Outputs

- `qa-report.json`
- `final-package-manifest.json`
- `revision-needed.json`

## Human Gate

QA approval is required before archiving. Approval means the package is suitable for operational use or clearly marked with accepted warnings.

## Extension Points

Handlers can add image dimension checks, OCR text checks, forbidden phrase scans, file naming enforcement, and package copying.
