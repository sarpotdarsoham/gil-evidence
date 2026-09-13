# Reproduction

## Portable development checks

From a checkout, run `python3 -I -S -B run_tests.py` and `python3 -I -S -B tests/model_oracle_v2.py`. The test runner discovers only this project's tests and fails if it finds none. The oracle writes `results/model_oracle_v2.json` with every generated case. Its finite synthetic model is not a proof of general soundness.

## Real CPython fixtures

The native fixture harness currently targets macOS with `/usr/bin/clang`. Supply ordinary and free-threaded CPython 3.14 interpreters with matching headers. The original experiment used 3.14.7 on macOS arm64 and pytest 9.1.1. A different release or platform is a replication, not the original experiment.

```sh
python3 validation/runtime/run.py --ft-python /path/to/python3.14t --normal-python /path/to/python3.14
/path/to/python3.14t -m pip install --target validation/runtime/pytestdeps --no-compile pytest==9.1.1
python3 validation/runtime/pytest_guard_matrix.py --ft-python /path/to/python3.14t --normal-python /path/to/python3.14
python3 validation/runtime/expanded_guard_matrix.py --ft-python /path/to/python3.14t
python3 validation/refined_matrix.py
```

The first command builds two small, stateless extension fixtures: one with no free-threading declaration, and one declaring that it does not require the GIL. They exist solely to trigger documented interpreter behavior. The commands execute these authored fixtures, not third-party package test suites.

The expanded matrix contains 36 templates run in two import contexts (72 pytest processes). It uses the frozen earlier analyzer. The refinement command evaluates the current analyzer against those same already observed outcomes; it is adaptive regression, not untouched validation. Preserve the frozen analyzer and matrix definitions.

Generated results contain local interpreter paths and diagnostics. They are ignored by Git; inspect and sanitize them before sharing. Compiled extensions, installed dependencies, private research records and manuscript drafts are not distributed in this repository. Public evidence summaries must state their provenance and limitations.
