# Camera r5: Codex review, round four (2026-11-03)

Read-only, against r5 (98436df). No Blocking findings. r6 answers it.

Round-three dispositions: R4-B1 partly (R9 still says the list goes in every beat). R4-S1..S6 resolved.
R4-S7 partly. R4-M1 resolved.

R5-S1. GateTracker.lost_in_channel has no return contract; whether beat() counts automatically is unstated.
R5-S2. split_coverage lacks gen and seq; adding the envelope afterward can exceed 8192 bytes.
R5-S3. The coverage digest's exact bytes are unspecified; no test vector.
R5-S4. Coalescer(max_keys=1) and replay-conflict counts are ambiguous.
R5-S5. The promised /proc fixture tests have no entry point.
R5-S6. R9 still says the coverage list goes in every beat.
R5-S7. 30 s retransmission is not a 30 s bound when the same part keeps being dropped.
R5-S8. A 256-directory budget cannot list every directory beyond it.
R5-M1. SO_RCVBUF has no effect on AF_UNIX sockets (unix(7)).
