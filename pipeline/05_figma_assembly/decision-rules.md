# Decision Rules

## Template Fit

Use templates whose channel, ratio, text slots, and visual slots match the deliverable. If multiple templates fit, prefer the one with fewer manual overrides.

## Copy Fit

Text must fit within slot length and hierarchy rules. Rewrite only within approved brief constraints.

## Required Phrase Allocation

Distribute required phrases by slot role instead of concentrating them in the headline.

- `headline` / `title`: primary benefit or core message.
- `body` / `subcopy` / `details` / `caption`: supporting benefit or explanatory phrases.
- `cta`: action phrases such as 신청, 예약, 문의, 구매, 참여.
- `badge` / `label` / `info`: scarcity or urgency phrases such as 한정, 수량, 마감, 기간.

If a template has no badge-like slot, scarcity phrases may fall back to subtitle, body, subcopy, details, or caption as long as the slot fits.
Each copy-map item should record whether required phrases were applied and which allocation rule selected the text.

## Copy Refinement

After required phrase allocation, deterministic refinement may rewrite slot text for readability only if all guardrails pass:

- every applied required phrase remains verbatim in the refined text
- no event or brand banned word is introduced
- source trace remains unchanged
- `fit_status` must not become worse
- slot role is respected: CTA stays short and action-led, headline stays benefit-led, supporting slots may become short phrases or natural sentence fragments

This rule-based layer is intentionally replaceable by a later LLM refinement step that uses the same guardrails.

## Export Readiness

Every output must have an expected filename, channel folder, dimensions, and QA checks.
