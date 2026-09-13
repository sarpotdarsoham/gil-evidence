# Fixed-cohort field study 01

**Outcome: no demonstrated added practical value in this cohort. Submission remains a no-go.** The analyzer was frozen before source capture; no analyzer refinement followed inspection of these results. This is an agent-conducted purposive study, not an independently selected or human-labeled benchmark.

We selected eight established Python/native-extension repositories outside the earlier 30-package source inventory. We resolved each default branch to a commit once, captured that archive, and examined every eligible UTF-8 Python test-path file up to 1 MB. The eligibility rule uses `test` in any path component or `conftest.py`; it does not guarantee each file is an executable pytest test. No repository was replaced. The selection is not representative of all free-threaded Python projects.

The full [pre-capture plan](plan.json), [pinned revisions](revisions.json), [file inventory](files.jsonl), and [repository/exclusion records](repositories.json) are included. The plan hash was recorded locally before acquisition; this was not a publicly preregistered or independently witnessed study. The reproduction program uses the pinned archives and validates their hashes.

| Repository | Eligible files | Query text | Text co-occurrence | Direct AST | Analyzer-positive files | Parse failures (3.11) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cython/cython | 165 | 0 | 0 | 0 | 0 | 8 |
| h5py/h5py | 44 | 0 | 0 | 0 | 0 | 0 |
| numpy/numpy | 259 | 2 | 1 | 0 | 0 | 1 |
| pandas-dev/pandas | 1137 | 0 | 0 | 0 | 0 | 0 |
| pyca/cryptography | 117 | 0 | 0 | 0 | 0 | 0 |
| python-cffi/cffi | 73 | 1 | 0 | 0 | 0 | 0 |
| python-pillow/Pillow | 175 | 1 | 0 | 0 | 0 | 0 |
| scipy/scipy | 420 | 0 | 0 | 0 | 0 | 0 |
| **Total** | **2,390** | **4** | **1** | **0** | **0** | **9** |

Baselines are simple triage checks, not existing third-party tools: query text anywhere in the file; co-occurrence of query text, `skipif`, and `assert`; and direct function/class guard-query plus negated query assertion without helper/alias resolution. Counts are file-level warnings, not precision or recall. The analyzer ran only on files containing `skipif`, as specified in the plan. Zero candidates does not certify the remaining files, and no exhaustive ground truth was established. We did not execute a head-to-head comparison against runtime plugins or third-party test suites.

## Context inspection

The one co-occurrence file is [NumPy's f2py test file at the captured commit](https://github.com/numpy/numpy/blob/e80572f1407205a37182e3ec9a276f4ea698b163/numpy/f2py/tests/test_f2py2e.py#L842). It tests generated-extension behavior through subprocess commands. The visible skip conditions concern operating system and Python version; the commands assert GIL state after importing the generated extension. This is not evidence of the targeted state-selective skip masking. The narrow analyzer's silence here does not establish a useful advantage: the equally simple direct-AST baseline was also silent.

The remaining query-containing files are [NumPy's conftest](https://github.com/numpy/numpy/blob/e80572f1407205a37182e3ec9a276f4ea698b163/numpy/conftest.py#L100), [Pillow's conftest](https://github.com/python-pillow/Pillow/blob/a707c6b21c313880d0771e54965d142dd42358b6/Tests/conftest.py#L9), and [CFFI's conftest](https://github.com/python-cffi/cffi/blob/a8520676f8c45082a850ba8dc703d5bd936c30ce/testing/conftest.py#L28). They observe runtime GIL state at startup and/or the terminal summary. CFFI's visible summary hook explicitly exits with failure when it observes a transition to enabled. This reinforces the need to account for suite-level mechanisms before interpreting any local source warning. We make no defect claim about these projects.

## Parser sensitivity

Nine eligible files failed parsing under CPython 3.11, and remain explicitly recorded as errors. A separate post-hoc CPython 3.14 parse check succeeded on three; six still failed. None of the nine contains the literal query name. Some are deliberately invalid compiler fixtures or newer syntax. These files were not silently removed from the denominator, and the original analysis was not relabeled as a 3.14 run. See [the sensitivity record](parser_sensitivity.json).

## Reproduce

From the repository root, with Python 3.11:

```sh
python3 -B validation/field_study.py --cache /path/to/archive-cache --output /path/to/new-results-directory
```

This downloads the pinned public archives if absent and checks checksums. It parses source as data and never imports or executes it. Choose fresh output storage. Network availability and the continued availability of the pinned archives are prerequisites. Existing archive caches can reproduce the analysis offline. Local capture logs include retrieval times; timestamps will differ on replication. Compare per-file hashes and classifications, not timestamp fields.

## Decision

The data are too sparse in the target pattern to estimate effectiveness. There is no demonstrated added real-project finding, independently confirmed suite failure, or practical improvement over the simple baselines. The current evidence does not justify promoting this narrow prototype to a journal article. Keep it available as experimental software; do not write a manuscript or infer novelty from the absence of an identical tool. A further study would need a justified sampling frame with relevant opportunities, executable ground truth and a concrete advantage to test; simply increasing the number of unrelated files would not solve this gap.
