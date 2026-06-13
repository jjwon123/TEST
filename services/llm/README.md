# LLM Service

## Purpose

The LLM service is the adapter boundary for agent reasoning calls. Pipeline stages define the reasoning contract; this service will later provide model selection, prompt assembly, structured output validation, and retry policy.

## Current Scope

The service supports provider-neutral request envelopes plus two execution paths:

- local draft fallback when no provider is configured
- live HTTP JSON provider execution when `LLM_PROVIDER_URL` is configured

Stage handlers can:

- state their reasoning goal explicitly
- pass provider-neutral prompts and guardrails
- bind the intended output schema
- expose provider execution metadata in run artifacts
- perform bounded local repair passes when quality flags remain
