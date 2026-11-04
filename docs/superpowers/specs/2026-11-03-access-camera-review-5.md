# Camera r6 code: first root-test run and security review (2026-11-04)

Not a Codex round: the findings that moved r6 to r7.

## First run of T2-T7 against the house (2026-11-04 ~17:40Z)
All six failed at `systemctl reset-failed` on a unit never loaded (harness; enabling the unit loads it).
Second run: T3 and T7 passed. T2 and T4: "no syscall trace result". T5: caller p99 25.301 ms (bound 2 ms).
T6: a new member not marked within 10 s.
- T2/T4 cause, found by hand: the harness's ptrace helper sets PTRACE_SETOPTIONS data=0x80, which is
  PTRACE_O_TRACESECCOMP; PTRACE_O_TRACESYSGOOD is 0x1. Without it, syscall stops never carry SIGTRAP|0x80,
  so the helper skips every stop. With 0x1 in a scratch copy it reported the delivered event at once.
- T5 cause: a full /proc snapshot (about 20 file reads) per open, before each answer. r7 adds R4a.
- T6 cause: a member added just after a rescan began waited for the next cycle. r7 watches members.json.
- T1 not run: it stops the arango-apacheta container, the production store every door persists to.

## Automated security review of commit a0e17ce
1. Missing sender authentication: the scribe ran as uid 1000 and accepted any datagram, so any uid 1000
   process (every door's bash) could forge entries or beats; its read-write credentials were readable by
   uid 1000 as well. r7: scribe as system user hamutay-camera, SO_PASSCRED sender uid 0 only, credentials
   in /etc/hamutay-camera (R12).
2. Privileged write to a user-controlled path: the root gate sent to a socket inside a uid-1000 directory;
   a symlink there would redirect root's sends. r7: /run/hamutay-camera, owned by hamutay-camera, 0750.
