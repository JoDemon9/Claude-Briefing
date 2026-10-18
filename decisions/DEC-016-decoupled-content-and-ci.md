# DEC-016 — Decoupled content generation and CI testing

The original Antigravity decision is the final entry in [Oracle DECISIONS.md](https://github.com/JoDemon9/oracle-briefing/blob/main/DECISIONS.md), labelled 16 October 2026, and is also reflected in [Oracle AGENTS.md](https://github.com/JoDemon9/oracle-briefing/blob/main/AGENTS.md).

It assigns research, source validation and schema-compliant content JSON to ChatGPT. GitHub Actions handles site compilation, schema validation, image preparation and Playwright browser checks. Editorial facts, image relevance/rights and publication verification still require real review; CI success alone does not prove factual accuracy or live publication.

The entry states an approximate 50% token-usage reduction. No supporting account observation was available in this review, so that percentage is retained as the original claim rather than adopted as a measured result.

[DEC-017](DEC-017-section-coverage-and-github-checks.md) implements the handoff in the maintained source workflow and actual prompts, adds tested-artifact reuse and separate International/Cyprus coverage requirements, and records verification/deployment status. The original DEC-016 identifier and its rationale are preserved.
