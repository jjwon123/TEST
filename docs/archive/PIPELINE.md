# Pipeline

## Stage Order

1. `01_event_brief`: normalize event and brand input into a brief
2. `02_content_planning`: define channel deliverables and visual needs
3. `03_visual_candidates`: create ComfyUI visual plan, prompts, and candidate manifest
4. `04_admin_selection`: record human selection, rejection, hold, or regeneration decisions
5. `05_figma_assembly`: map selected assets and copy into Figma templates
6. `06_qa_packaging`: validate exports and create the final package manifest
7. `07_asset_archive`: archive approved assets and index reusable knowledge

## Approval Gates

- Brief approval unlocks content planning.
- Content plan approval unlocks visual candidates.
- Candidate readiness unlocks admin selection.
- Admin selection approval unlocks Figma assembly.
- Channel output readiness unlocks QA.
- QA approval unlocks archive.

## Regeneration Model

Regeneration should be scoped. A single stage output, deliverable, candidate, or channel output should be regenerated without replacing approved upstream context. Existing files should remain versioned for audit.

## Channel Canonicalization

Operator inputs may use aliases such as `instagram`, `insta`, `blog`, `naver_blog`, or `community`. `core/utils/channel_registry.py` resolves those aliases through `core/channels/*.json` before downstream stages run. Stage outputs should store only canonical channel IDs such as `instagram_cardnews`, `instagram_feed`, `blog_thumbnail`, `blog_inline_image`, and `community_banner`.

## Current Implementation Level

The scaffold defines contracts, state transitions, and orchestration shape. External API calls are intentionally minimal until schema and approval behavior are stable.
