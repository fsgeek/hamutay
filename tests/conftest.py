"""Suite-wide collection rule for the TurboQuant R1 evidence suites.

The R1 suites were written to FAIL, not skip, when their declared environment
is incomplete, so a run without the author checkout and CUDA 12.8 can never
look green (plan 2026-08-27, Task 7; clean validation 2026-09-18). That is
right inside the declared environment and wrong for a default `pytest` of the
house, whose shell selects CUDA 13.2. The declared environment is selected by
CUDA_HOME=/usr/local/cuda-12.8: with it, everything below is collected and
fails loudly if evidence is missing; without it, these tests are deselected,
and pytest reports them as deselected in its summary.
"""

import os

DECLARED_CUDA_HOME = "/usr/local/cuda-12.8"

# Tests that assert the declared environment itself rather than skipping.
_DECLARED_ENVIRONMENT_ONLY = (
    "tests/turboquant_clean_terminal/test_author_cuda_differential.py",
    "tests/turboquant_clean_terminal/test_process_determinism_artifacts.py",
    "tests/turboquant_clean_terminal/test_public_cli_terminal.py",
    "tests/turboquant/test_qualify_cli.py::test_real_cli_missing_author_checkout_is_nonzero_with_terminal_error_pair",
)


def pytest_collection_modifyitems(config, items):
    if os.environ.get("CUDA_HOME") == DECLARED_CUDA_HOME:
        return
    keep, drop = [], []
    for item in items:
        if item.nodeid.startswith(_DECLARED_ENVIRONMENT_ONLY):
            drop.append(item)
        else:
            keep.append(item)
    if drop:
        config.hook.pytest_deselected(items=drop)
        items[:] = keep
