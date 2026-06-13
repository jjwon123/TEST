# Research Service

## Purpose

The research service is the adapter boundary for search-assisted planning.
Planning stages decide when external context is needed; this service records the
research intent and will later execute search providers behind the same contract.

## Current Scope

The service supports two execution paths:

- snapshot fallback from `research-evidence.json`
- live HTTP JSON provider execution when `RESEARCH_PROVIDER_URL` is configured

Each plan records:

- why outside context is needed
- which concrete queries should run
- whether each query is required or optional
- the stage context that motivated the request

Execution metadata is written into `research_context.provider_execution` so a
run artifact shows whether live lookup ran or the local snapshot fallback was used.
