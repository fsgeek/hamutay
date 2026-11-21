# Camera r4: Codex review, round three (2026-11-03)

Read-only, against r4 (38574e8). r5 answers it. Codex ran no privileged command.

Round-two dispositions: N-B1, N-B2, N-S1, N-S2, N-S3, N-S4 resolved. N-S5 partly (a home's scan has no
bound). N-S6 partly (holds only if the full snapshot fits a message). N-S7 partly (R8's drops contradict
alive's certificate). N-S8 partly (callable names lack contracts).

R4-B1 (Blocking). Every beat must carry the complete coverage list within 8192 bytes; 100 marked paths of
~100 bytes exceed it, and no truncation or fragmentation is defined.
R4-S1. A crashed scribe leaves its socket path; the next bind() fails EADDRINUSE (unix(7)). Specify
stale-path handling and single-scribe ownership.
R4-S2. Left-truncated paths can merge two files with the same retained suffix under R5's key.
R4-S3. R9a rescans only direct subdirectories, so a deeper directory created after start is never marked.
R4-S4. alive cannot certify storage while R8 allows drops; define it as stored plus counted losses.
R4-S5. A gate restart within 10 s creates no gap, yet T7 requires one.
R4-S6. Spool retirement renames without fsyncing the directory.
R4-S7. Interfaces lack constructors, signatures, return shapes.
R4-M1. Rollout still says r3 and T1-T6.

Host facts it read: /run/user/1000 is 0700 uid 1000; wmem_default 212992; wmem_max 4194304;
net.unix.max_dgram_qlen 10. sendto results: path absent ENOENT; stale path ECONNREFUSED; bound with room
succeeds; queue full EAGAIN. An 8192-byte datagram fits; the 10-deep queue limits bursts.
