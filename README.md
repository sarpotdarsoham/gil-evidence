# GIL Evidence

Experimental static checks for GIL-state evidence in free-threaded Python tests. The analyzers read source without importing or executing the input.

**Research status: prototype; novelty and publication readiness are not established.** This is not a thread-safety checker or a package compatibility certificate.

## Install and try

Python 3.10+; the analyzers have no runtime dependencies.

```sh
git clone https://github.com/sarpotdarsoham/gil-evidence.git
cd gil-evidence
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/gil-evidence examples/after_import.py --line 4
.venv/bin/gil-evidence examples/too_early.py --line 4
.venv/bin/python -m ci_evidence examples/separate_processes.sh
.venv/bin/python -m guard_evidence examples/masked_guard.py
```

The first checkpoint example reports `CHECK_COVERS_CHECKPOINT`; the second reports `CHECK_NOT_ESTABLISHED`, because an import occurs after the check. The checkpoint CLI exits 0 for coverage and 2 for other outcomes. The process and guard commands emit JSON reports; their exit codes do not indicate finding severity.

The example files are analysis inputs. Their illustrative native-extension names are not installed or executed. `masked_guard.py` illustrates a skip guard that suppresses precisely the enabled-GIL state its assertion would reject.

## Three checks

| Analyzer | Question | Limits |
| --- | --- | --- |
| `gil_evidence` | Does disabled-GIL evidence survive to the instant before a selected statement on every modeled path? | Small AST subset; no general control-flow or call-graph analysis |
| `ci_evidence` | Are a GIL query and a direct test invocation in the same Python process? | Restricted POSIX commands; no full workflow, plugin, or shell model |
| `guard_evidence` | Does a supported skip guard hide the GIL state rejected by a test assertion? | Reports source candidates under restricted expression and binding assumptions |

Use `--optimized` to model removal of assertions under `-O`; explicit raising guards survive that removal. `--column` selects a zero-based AST byte offset when statements share a line. `--function` analyzes one top-level function in isolation, without inherited global aliases.

Positive checkpoint evidence assumes standard unmodified APIs/import semantics, unchanged relevant bindings, no external concurrent GIL-state changes or tracing hooks, and normal continuation. It concerns the instant **before** the checkpoint, not execution inside a called test. Unsupported constructs yield unknown results. Missing evidence does not prove the GIL is enabled. A skip-guard finding does not prove the whole suite misses a defect.

## Verify

```sh
python3 -I -S -B run_tests.py
python3 -I -S -B tests/model_oracle_v2.py
```

The generated oracle explores 258 programs, 516 analysis cases and 16,512 simulated executions. These are finite development checks, not independent field accuracy estimates or a soundness proof. See [reproduction instructions](REPRODUCIBILITY.md) for real free-threaded CPython fixtures and [research assessment](ASSESSMENT.md) for competing tools and unmet evidence requirements.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CHANGELOG.md](CHANGELOG.md). Code and initial experiments were developed with substantial AI assistance; this repository does not represent independent human review. No publication, maintainer endorsement, or acceptance is claimed.
