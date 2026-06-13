---
name: category-campaign-review
description: Use when reviewing campaign briefs for skincare, lab-grown diamond jewelry, or gold exchange/precious metals categories. Applies evidence-backed negative failure patterns, category-specific yes/no judgment questions, regulatory risk checks, CEP/persona validation, channel-persona fit, and brand-vs-activation balance. Use before approving 01_event_brief or 02_content_planning outputs for these categories.
---

# Category Campaign Review

## Purpose

This skill reviews campaign briefs by asking why a plan should fail before asking how it could work. Do not role-play as a creative director. Apply category-specific failure conditions and require evidence-backed judgment.

Use this skill for:

- skincare campaigns
- lab-grown diamond jewelry campaigns
- gold exchange, bullion, silver, gold bar, coin, or precious metals campaigns

## Core Method

For each brief, produce a review in this structure:

1. Category detected
2. Pass / revise / reject decision
3. Failure-pattern matches
4. Yes/no judgment answers
5. Evidence basis
6. Required repairs before approval
7. Channel and persona fit notes
8. Brand-vs-activation balance warning

## Universal Gates

Reject or require revision when any of these are true:

- Target is only demographic shorthand such as "MZ세대", "2030 women", "young office workers", or "high income consumers".
- The brief cannot answer a concrete Category Entry Point using the 7W frame: why, when, where, while, with whom, with what, how feeling.
- The campaign relies only on positive claims and has no negative risk screen.
- Legal, regulatory, certification, or substantiation-sensitive claims appear without evidence.
- Brand-building and activation roles are mixed without a budget or channel rationale.
- One asset/message is planned for all channels despite different channel buying logic.

## Effectiveness Principles

Use these as judgment heuristics, not rigid laws:

- Binet & Field 60:40: most consumer categories need a balance of long-term brand building and short-term activation.
- Financial or trust-asymmetric categories usually need heavier brand/trust investment than 60:40.
- Sharp/Romaniuk CEPs: a target is not useful unless the brief states the buying or consideration situation where the brand should come to mind.
- Kantar MDS: the brief should make the brand meaningful, different, and salient. Weak difference is a strategic warning.

## Category Selection

Load exactly one category reference unless the user explicitly asks for comparison:

- Skincare: `references/skincare.md`
- Lab-grown diamonds: `references/lab-grown-diamonds.md`
- Gold exchange / precious metals: `references/gold-exchange.md`

Do not merge category rules. If a brand spans categories, review each category separately and report conflicts.

## Output Requirements

Use yes/no questions for the decision surface. A good finding includes:

- situation: what in the brief triggered the concern
- judgment: why it fails or creates risk
- evidence basis: source class or named reference from the category file
- repair: what must change before approval

Never approve a brief only because it sounds polished.

