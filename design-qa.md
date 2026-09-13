# Design QA — LoopStudio production board

- Source visual truth:
  - `C:\Users\jinkiwon\AppData\Local\Temp\codex-clipboard-f0ba90cc-5851-45d0-99c7-c35f2912e306.png` (Nexon design-system source)
  - `C:\Users\jinkiwon\.codex\generated_images\019f7430-d9bf-7172-946c-eda6ab126db8\exec-8106304e-a6d6-4bda-8af3-f07875393738.png` (approved hybrid product direction)
- Browser-rendered implementation: `C:\Users\jinkiwon\iCloudDrive\자동화 프로젝트\.tmp\ux-redesign-2026-07-18\implementation-1270.png`
- Mobile implementation: `C:\Users\jinkiwon\iCloudDrive\자동화 프로젝트\.tmp\ux-redesign-2026-07-18\implementation-mobile-fixed.png`
- Full-view comparison: `C:\Users\jinkiwon\iCloudDrive\자동화 프로젝트\.tmp\ux-redesign-2026-07-18\comparison.png`
- Focused comparison: `C:\Users\jinkiwon\iCloudDrive\자동화 프로젝트\.tmp\ux-redesign-2026-07-18\focused-comparison.png`
- Desktop viewport request: 1270 × 1072; captured content area: 1255 × 1059
- Mobile viewport: 768 × 900
- State: dashboard, `season-monsoon-barrier`, concept selected, copy review pending

## Findings

No actionable P0, P1, or P2 differences remain.

- Typography: display hierarchy, Korean body readability, weights, wrapping, and compact UI labels follow the source's bold-heading/calm-body split. NEXON Gothic is used when locally available, with Pretendard and Malgun Gothic fallbacks.
- Spacing and layout: the implementation preserves the hybrid's journey → current mission → evidence → sticky action order. Card comparison fields align, and the inspector remains visible at desktop width.
- Colors and tokens: the implementation uses white, `#17191d`, neutral grays, restrained borders, 4/8px radii, and `#00de5a` only for the current journey marker and primary CTA. The mock's repeated greens and gold recommendation were intentionally removed to comply with the Nexon source rules.
- Image and asset fidelity: this workflow screen requires no illustrative or photographic assets. No placeholder art, emoji, handcrafted SVG, or CSS-drawn icon substitutes are present.
- Copy and content: labels describe human decisions in Korean; the selected concept, evidence, risk, unlock message, and CTA are populated from live console data rather than placeholder copy.
- Interaction states: selected concept has a strong ink border; changing a card changes the selected concept and primary action; existing selections lead to copy review; new selections lead to copy generation.

## Comparison history

### Iteration 1

- Earlier finding: [P2] At 768px, the full sidebar consumed most of the first viewport and pushed the current mission below the fold.
- Fix: collapsed mobile chrome to a compact brand + “새 이벤트 시작” row, kept production context in the top action row, and let the six-step journey scroll horizontally.
- Post-fix evidence: `implementation-mobile-fixed.png` shows the current journey and mission header inside the first viewport without horizontal page overflow.

### Iteration 2

- Full-view and focused comparison found no remaining P0/P1/P2 issues.
- The implementation intentionally differs from the hybrid mock by using neutral completed states and a neutral recommendation label. This is required by the selected Nexon design system, not design drift.

## Primary interactions tested

- Selected `concept_02`; exactly one concept card became selected and the CTA changed to “선택하고 카피 만들기”.
- Opened “브리프 만들기”; page title changed to “브리프 만들기”.
- Returned to “홈”; page title changed to “제작 홈”.
- Final server/browser console errors and warnings: none.
- The final server-mutating concept confirmation was not submitted during QA, to preserve the user's benchmark data.

## Follow-up polish

- [P3] On very narrow desktop widths, long event names in the top selector truncate. This is intentional to preserve action visibility; a custom event switcher could improve scanability later.

## Copy-review follow-up — 2026-07-18

- Earlier finding: [P1] “카피 검수 시작” focused a review panel inside the closed advanced-details container, so the visible screen did not change and the user received no next-step instruction.
- Fix: the CTA now switches the current mission into a dedicated copy-review workspace with four explicit steps: read, edit, evaluate, save.
- The workspace shows four live channel outputs, per-card direct editing, a sticky final-decision inspector, approval versus revision guidance, and the exact save requirement.
- Browser evidence: `C:\Users\jinkiwon\iCloudDrive\자동화 프로젝트\.tmp\ux-redesign-2026-07-18\copy-review-final.png`.
- Combined source/implementation evidence: `C:\Users\jinkiwon\iCloudDrive\자동화 프로젝트\.tmp\ux-redesign-2026-07-18\copy-review-comparison.png`.
- State note: the Nexon artifact is a design-system source rather than the same application state, so comparison is limited to the selected typography, neutral palette, border/radius system, content density, and restrained primary action.
- Post-fix interactions: start copy review, render four guide steps, render four copy cards, render one decision inspector, return to concepts, and reject an incomplete save with the correct validation message.
- Browser console errors and warnings: none.
- Remaining P0/P1/P2 findings: none.

## Final-decision panel follow-up — 2026-07-18

- Earlier finding: [P1] Native checkbox inputs inherited the global `width: 100%` form rule. In the narrow right inspector, the checkbox consumed the row and pushed Korean reason labels into broken character-level wrapping.
- Fix: reason tags now use a one-column list; their native checkbox controls explicitly use intrinsic width, zero padding, and 16px height. Form labels and helper copy use compact inspector typography.
- Saved-result behavior: after a successful review API response, the UI presents a completion screen that states whether the decision was approval or revision, explains what was recorded, and offers image-candidate creation or reopening the just-saved review.
- Post-fix visual evidence: `C:\Users\jinkiwon\iCloudDrive\자동화 프로젝트\.tmp\ux-redesign-2026-07-18\copy-review-tag-final.png`.
- Browser console errors and warnings: none.
- Save-result server mutation was not exercised during visual QA, to avoid changing the user's approval record. The success transition is covered by the same API response branch used after a real save.

## Copy review handoff correction (2026-07-18)

- A saved copy review now hands off to the matching `prompt_ready` event run's image-candidate stage. The completion CTA is `이미지 후보 만들기`, not another benchmark review.

final result: passed
