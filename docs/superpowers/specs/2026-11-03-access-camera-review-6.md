# Camera r7 code: latency measurement and second security review (2026-11-04)

## Latency (T5), measured by the custodian on this host (WSL2 6.18.54.1, 128 CPUs)
Caller-side, around os.open, 10 s runs unless noted; "watched" is a file in a marked home.
- No camera, 20 threads in one process: p50 1.081 ms, p99 4.111 ms, max 10.860 ms.
- No camera, 20 processes: p50 0.005 ms, p99 0.008 ms, max 0.951 ms.
- Camera on, watched, 20 threads: p50 9.803, p99 12.262, max 14.255 ms.
- Camera on, watched, 20 processes: p50 9.890, p99 13.444, max 22.020 ms.
- Camera on, watched, 1 process (4 s): p50 0.173, p99 0.394, max 2.532 ms.
cProfile of the gate (scratch community, 5 s of 20 processes): 3.76 s of 9 s in posix.write (the
fanotify response), 0.39 ms per write; the rest idle in select. With one reader: 0.023 ms per write.
nice -n -15 and chrt -r 10 left the write cost at 0.39 ms. Conclusion: per-response cost grows with the
number of waiting openers, in the kernel; the gate cannot remove it. Consistent with all waiters sharing
one wait queue, not verified.

## Automated security review of 0c50c9b
1. Stale identity in the reader cache: a cached snapshot could exempt an open by a process that changed
   cgroup or uid within the cache window. r8: exemptions re-read uid and cgroup.
2. Rescan starvation: each members.json change restarted the rescan, so frequent changes could keep
   finish_rescan (unmarking, coverage) from ever running. r8: a change joins the rescan in progress.
