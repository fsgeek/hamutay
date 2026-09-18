# Executed commands

Both launched from `/home/tony/projects/hamutay`, using its current lease supervisor.

```bash
deploy/ayllu-gpu run --holder turboquant-r1-validation --purpose 'Replay frozen Gemini 3.8 suite; workload limit 15 minutes' --ttl 30m --wait-timeout 5m -- timeout --signal=TERM --kill-after=60s 15m env --chdir=/home/tony/projects/hamutay/.worktrees/turboquant-r1 CUDA_HOME=/usr/local/cuda-12.8 PATH=/usr/local/cuda-12.8/bin:/home/tony/projects/hamutay/.worktrees/turboquant-r1/.venv/bin:/home/tony/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/lib/wsl/lib QJL_AUTHOR_CHECKOUT=/home/tony/projects/hamutay/tmp/turboquant-remedy-20260918/QJL OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MAX_JOBS=2 /home/tony/projects/hamutay/.worktrees/turboquant-r1/.venv/bin/python -m pytest tests/turboquant_clean_r3 -q -ra > /home/tony/projects/hamutay/tmp/turboquant-remedy-20260918-r3/first-replay.txt 2>&1
```

Exit1: 30 passed, 9 failed, no skips.

```bash
deploy/ayllu-gpu run --holder turboquant-r1-validation --purpose 'CUDA-active implementer and corroborating suites with full device PATH; 15-minute limit' --ttl 30m --wait-timeout 5m -- timeout --signal=TERM --kill-after=60s 15m env --chdir=/home/tony/projects/hamutay/.worktrees/turboquant-r1 CUDA_HOME=/usr/local/cuda-12.8 PATH=/usr/local/cuda-12.8/bin:/home/tony/projects/hamutay/.worktrees/turboquant-r1/.venv/bin:/home/tony/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/lib/wsl/lib QJL_AUTHOR_CHECKOUT=/home/tony/projects/hamutay/tmp/turboquant-remedy-20260918/QJL OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MAX_JOBS=2 /home/tony/projects/hamutay/.worktrees/turboquant-r1/.venv/bin/python -m pytest tests/turboquant tests/turboquant_independent -q -ra > /home/tony/projects/hamutay/tmp/turboquant-remedy-20260918-r3/full-existing-suites.txt 2>&1
```

Exit0: 380 passed in 234.13 seconds, no skips. Lease `b03ca82a-43f1-4387-bed4-914c02d5d446` released; the heartbeat restored Qwen (see retained before/after status records). This establishes implementer and prior-suite corroboration, not the new independent gate.
