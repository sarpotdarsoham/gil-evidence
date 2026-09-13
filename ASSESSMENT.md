# Research readiness assessment

Decision: **not ready for journal submission**. This is a software/research assessment, not a manuscript. A working implementation exists; a defensible novel contribution and external usefulness remain unestablished.

## What is already known

- Python documents GIL re-enabling on imports and the distinction between a free-threaded build and current runtime state: [official guidance](https://docs.python.org/3/howto/free-threading-python.html).
- [pytest-freethreaded](https://github.com/tonybaloney/pytest-freethreaded) offers runtime GIL checks and concurrent test execution.
- [pytest-run-parallel](https://github.com/Quansight-Labs/pytest-run-parallel) includes runtime handling of GIL re-enabling warnings.
- [ft-readiness](https://pypi.org/project/ft-readiness/0.1.0/) already checks imports in subprocesses and distinguishes build capability from runtime state. Its inspected 0.1.0 source is a particularly relevant comparator.
- General conditions that prevent tests from detecting defects are established test-smell territory, including [Conditional Test Logic](https://testsmells.org/pages/testsmells.html). That tool's described syntactic detection is broader and different from the restricted state relation considered here. This difference alone does not establish publication-worthy novelty.

The possible contribution is a narrowly scoped static audit of **existing** free-threaded tests, combining checkpoint placement, process separation, and skip/assertion state relations. No new general analysis algorithm is claimed. The comparison above is not an exhaustive literature review or an executed head-to-head benchmark.

## Evidence and its limits

| Evidence from private prototype development | What it supports | What it cannot establish |
| --- | --- | --- |
| 258 generated programs; 516 analyses; 16,512 simulated runs; no enabled-GIL counterexample among 137 positive cases | Agreement within a finite development grammar | General soundness or field accuracy |
| Eight real CPython fixture scenarios matched expected behavior | Reproduction of selected runtime mechanisms | A previously unknown interpreter defect |
| Six pytest scenarios matched expected skip/failure behavior | Mechanism behind state-masking guards | A defect in a third-party suite |
| 36-template matrix: frozen analyzer 10/24 masking cases; adapted analyzer 21/24; no false candidates in that matrix | Development coverage and limitations | Independent 87.5% recall in real projects |
| Reused selected sources: 233 Python files, one guard candidate | A source pattern worth investigating | Prevalence, maintainer confirmation, or practical impact |
| 616 selected workflow run steps; no recognized inline-test/check-separation findings | Current command recognizer has poor reach in this sample | Successful general CI auditing |

The one field candidate is in [a pinned tokenizers test file](https://github.com/huggingface/tokenizers/blob/6cfd9d385ca0ed91c10b49f0ce97d02cfde1b607/bindings/python/tests/test_freethreaded.py#L151). The suite was not executed for this assessment and no maintainer has confirmed a defect. Other checks may cover the same condition. It must not be advertised as a confirmed bug.

## What would change the decision

1. Freeze a specific contribution claim and compare it against runtime plugins, a simple textual/AST baseline, and related test-smell analysis. Demonstrate useful cases the baselines miss, with reasons.
2. Freeze a fresh evaluation sample before examining its outcomes. Retain eligible files and exclusions, not only positive findings. Classify positives, negatives and unknowns against executable counterexamples where feasible.
3. Verify multiple independently selected real-project cases, including whether existing suite checks already catch the problem. Do not equate a source warning with a missed suite failure.
4. Show someone other than the implementation process can install, reproduce and use the tool. Human review is currently absent, not silently supplied by AI.
5. Choose a venue only after matching its actual contribution and evidence requirements. A repository is evidence infrastructure, not proof of acceptance.

These are research decision criteria, not promised results. If fresh evidence shows no useful advantage over existing tools, stop this publication direction rather than inflate the contribution or merely enlarge the codebase.

## Venue decision

[JOSS submission criteria](https://joss.readthedocs.io/en/latest/submitting.html), checked during this assessment, require sustained public development history, demonstrated research use and more than a minor utility. This new repository does not satisfy the immediate submission criteria. Creating artificial history would not address that gap.

SoftwareX and Software Impacts remain possible formats to investigate, not approved targets. The previously inspected publisher material is insufficient to establish current eligibility or likely acceptance. No venue acceptance, publication date, or submission readiness is promised.
