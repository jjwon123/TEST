# Console UX Redesign v1

Date: 2026-06-04

## Goal

Brand Event Console should feel like a creative operations review desk, not an AI experiment dashboard.

The interface should help a person answer three questions quickly:

1. What needs my review now?
2. What is blocked or risky?
3. What can be approved, summarized, or packaged next?

## Reference Direction

Use the pasted Figma marketing design notes as a visual direction, adapted for an internal production tool:

- Monochrome base: white canvas, black text, hairline borders.
- Pastel color blocks only for high-level workflow surfaces, not as random decoration.
- Pill buttons and pill navigation.
- Minimal shadows.
- Strong typography hierarchy, but keep operational screens dense enough for repeated work.
- Avoid "AI dashboard" styling: dark panels, glowing blue accents, sci-fi status cards, and overly technical labels.

## Page Architecture

### 1. Workboard

Purpose: current production queue.

Primary content:

- Today's work queue
- Review waiting sessions
- Runs that can move to next stage
- Blocked/risky runs
- Recent production packages

Secondary content:

- Total runs
- Reference count
- Generated image count
- Prompt-ready count

### 2. New Event

Purpose: create a structured event input.

Tone:

- Form as a quiet editorial worksheet.
- Product preview stays visible.
- Keep AI language out of field labels.

### 3. Pipeline

Purpose: inspect one run and move it through stages.

Primary content:

- Event name
- Current stage
- Next action
- Stage progress
- Links to References, Images, Package

### 4. References

Purpose: inspect and collect references.

Primary content:

- Candidate/selected reference grid
- Source folder actions
- Collection controls

### 5. Review Training

Purpose: review AI first-pass decisions against Kiwon's final decisions.

Primary content:

- Session picker with reviewed/accuracy/distribution
- Fast pair review
- AI decision -> final decision transition
- Reason tags
- Summary/compare actions

### 6. Prompt Sheet

Purpose: inspect generated image prompts.

Tone:

- Treat prompts as production copy specs, not AI chat outputs.

### 7. Image Selection

Purpose: choose generated candidates and request regeneration.

Primary content:

- Candidate grid
- Large preview
- Decision panel
- Generation group controls

### 8. Package

Purpose: final QA and production handoff.

Primary content:

- Selected assets
- QA evidence
- Package files
- Archive-ready state

## UX Principles

- Workflow language over AI language.
- Action-first dashboard.
- Use color for workflow state, not decoration.
- Show decision provenance where it matters: draft decision, final decision, transition.
- Keep review controls close to the asset being reviewed.
- Let summary and compare be natural completion actions after review.

## Visual Tokens

- Canvas: `#fbfaf7`
- Ink: `#111111`
- Hairline: `#dedbd2`
- Soft surface: `#f2f0e8`
- Lime block: `#d9ff66`
- Lilac block: `#dcd2ff`
- Cream block: `#fff1c7`
- Mint block: `#c9f4df`
- Coral block: `#ff8f70`
- Navy block: `#151633`

## Implementation Scope

1. Re-skin the console from dark AI dashboard to light creative operations desk.
2. Rename visible navigation/page concepts toward workflow language.
3. Redesign the dashboard as a work queue.
4. Keep existing functional APIs and handlers intact.
5. Preserve B track judgement-training features.

