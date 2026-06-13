# Fail Cases

## Blocking Failures

- Missing `event-input.json`
- Missing `brand-guide.json`
- Invalid JSON
- No event objective
- No event schedule when schedule is required by the offer

## Review Failures

- Conflicting dates
- Unclear benefit or offer
- Missing legal disclaimer for regulated claims
- Channel list conflicts with requested output types

## Retry Rules

Retry should produce a new version of `brief.json` while preserving the previous version. Approved fields should be reused unless the revised event input changes them.
