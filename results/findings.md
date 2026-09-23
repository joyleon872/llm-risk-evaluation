# Evaluation Findings

Model under test: Claude Haiku 4.5 · Temperature 0 · 40 test cases × 2 control configurations

## Pass rate by risk category

| Risk category | baseline | hardened |
|---|---|---|
| Grounding (answers match policy) | 12/12 (100%) | 12/12 (100%) |
| Hallucination (unknown info / false premises) | 10/10 (100%) | 10/10 (100%) |
| Prompt injection & data leakage | 10/10 (100%) | 10/10 (100%) |
| Scope, safety & overreliance | 8/8 (100%) | 8/8 (100%) |
| **Overall** | **40/40 (100%)** | **40/40 (100%)** |

## Failed tests: baseline (0)

No failures.

## Failed tests: hardened (0)

No failures.

## Effect of hardened controls

Fixed by controls (0): none

Regressions introduced (0): none
