# source: github.com/fsgeek/tessera README.md (origin/main@fd7c91e)

# Project Tessera

An AWS-native attestation service, built as a public demonstration of
principled engineering with AI as collaborator rather than substitute.

The primary objective is not the product alone. It is evidence that a
senior engineer can close a real knowledge gap quickly—using AI for
mechanics while owning architecture, judgment, and every decision that
must be defended cold. The secondary objective is commercial viability
as attestation-as-a-service; that upside is measured separately and is
not allowed to expand the demonstration’s scope.

**Credibility line** (as registered, `docs/phase-0-prereg.md` §1):
every architecture decision here is the human author (Tony) in
collaboration with AI agents. The purpose of the AI agents is to
accelerate the typing, push back on my decisions, clarify them, but not
to _make_ those decisions without consultation.

Since 17 September 2026 an AI instance owns the project day to day, by
the author's delegation; decisions it makes are labelled OWNER DECISION
in the record, and the author's are labelled as his. An earlier wording
of this paragraph, which was not the registered text, was read as
requiring the author to reconstruct every decision unaided. The author
never intended that requirement, and it is not one.

Tony Mason  
Initiated 10 June 2026  
This README's status was refreshed on 27 October 2026 by the owner instance; the credibility line and reading order are the author's.

---

## What this repository is

Tessera provides a neutral third party’s cryptographic binding to a
package of information at a fixed point in time. Attestation here means:
*this is what was presented in a bundle*, tied to a temporal anchor that
cannot be trivially regenerated. It does not by itself vouch for the
authenticity or truth of the contents; those guarantees, if any, ride in
the package.

The service is a cousin of [Willay](https://github.com/fsgeek/willay):
shared cryptographic and modeling ethos, forked edges for cloud-native
operation (KMS, S3 Object Lock, queues, observability, IaC).

The method is as load-bearing as the artifact:

1. **Pre-registration** — objectives, hypotheses, properties, and success
   criteria are written, signed, and OpenTimestamps-anchored *before*
   outcomes are known. The journal is measured against that record,
   including honest divergence.
2. **Formal foundation first (Band 0 / H0)** — machine-checked models of
   the core guarantees gate later code. No Phase 1 until the foundation
   holds or is amended on the record.
3. **Public, falsifiable process** — multi-round adversarial review,
   broken companions that must go red, named residuals, and a living
   property tracker. Theater is a failure mode, not a feature.

---

## Current status (27 October 2026)

| Layer | Status |
|-------|--------|
| Pre-registration | Signed, Amendments 1–11 in force. A9 sets the V1 scope; A10 covers time, authority capture and release custody (author rulings 2026-10-18); A11 (P3 profile, dependency sweeps, K-R enforcement by the signer role, slot-2 custody) was **signed 2026-10-29 at `f01e086`**. Its header still reads "DRAFT … Not signed" because signed text is never edited; the signing commit is its signing act (A11 preamble). A reviewer reading only the file will think it unsigned (Codex did, 2026-10-30, ISI-02). |
| V1 contract | `docs/V1-CONTRACT.md` says what a receipt establishes and what it does not. `docs/V1-SERVICE-CONTRACT.md` is the outside view, and `docs/V1-SERVICE-RESOLUTIONS.md` holds Tessera's answers to the open items. |
| V1 freeze | Signed 2026-10-24 (`formal/freeze-v1/FREEZE-RECORD.md`, commit `52ee179`), six days before the 30 Oct ceiling. Phase 1a (service code) is open. |
| Real receipts | Two TEST-pipeline receipts verified `VALID_STRICT`, using real AWS KMS (ML-DSA-65), a GCP HSM (P-256), live DNSSEC and Bitcoin anchoring (`prototype/e2e/`). |
| Service verifier | `service/verifier/`: agrees on 352/352 conformance cases and 69/69 E10 fixtures. |
| Issuer | `service/issuer/`: built and reviewed locally, VALID_STRICT end to end on stand-in signers. Not yet deployed to AWS. |
| Schedule | `docs/V1-SCHEDULE.md`: V1 issuing on AWS by 20 Nov; relying-party and dead-service tests, then ship or stop, by 4 Dec. |

Day-to-day ownership: an AI owner instance, by the author's delegation (see above). The latest handoff is in `docs/handoff-*.md`.

-------|--------|
| Phase 0 pre-registration | Signed and amended (Amendments 1–6 in force; A3 adopted 2026-08-08/09 after a four-model cold panel; A4 signed 2026-09-06 at `5188e7a`, precision repairs and discharge paths; A5 signed 2026-09-12 at `504e662`, the probe and cross-family findings: three verifier obligations, the waived-evidence reading, the §A4.6 boundary; A6 adopted 2026-09-12, P7's discharge path, signed at the commit carrying it; the 2026-08-29 author clarification records that "before any code" means code intended for the service) |
| Band 0 formal models | Active — TLA+ (P4, P5/P6, P5c issuance, bridge, floor-structure probe; non-discharging P9/P10 probes); ProVerif first-link spike complete, mechanism **decided** 2026-08-13 (`formal/spike/first-link/DECISION.md`); symbolic suite **built and run**: S-P3, S-P1, S-P2, S-P7, S-STANDING (`formal/suite/`), each cross-family reviewed by a non-author model, headers read by the author 2026-09-12; tracker: P1–P7 and P10 `checked` (P7 on Amendment 6), P8 and P9 open, standing row added `open` (Band 0 exit gated on it); capstone composition and P8 not begun |
| Named residual | The author has recorded (2026-08-29) that the first-link decision rests on symbolic results he cannot yet defend cold; accepted, not waived, with closing conditions |
| Cloud-independent crypto core | Not yet frozen (gated on Band 0) |
| LocalStack / AWS vertical slice | Not started |
| Application code | Minimal scaffolding only; one non-production design probe under `formal/spike/standing-probe/probe/` |

---

## How to read this repository

Recommended order for a new reader (human or collaborator instance):

1. **This file** — orientation and credibility line.
2. [`docs/phase-0-prereg.md`](docs/phase-0-prereg.md) — the signed intent
   and ranked objectives.
3. [`docs/phase-0-prereg-amendment-1.md`](docs/phase-0-prereg-amendment-1.md)
   — property list, adversary model, temporal-anchor semantics, agreement
   gate as falsification task.
4. [`docs/phase-0-prereg-amendment-2.md`](docs/phase-0-prereg-amendment-2.md)
   — refinement of confirmation, refusal, anchor standing, and the
   clock-roles ruling (adopted 2026-07-21, three review rounds).
5. [`docs/phase-0-prereg-amendment-3.md`](docs/phase-0-prereg-amendment-3.md)
   — identity boundary, linked evidence floors, the symbolic suite and
   capstone gate, survivability, standing as an orthogonal dimension
   (adopted 2026-08-08/09 after a four-model cold panel).
6. [`formal/spike/first-link/DECISION.md`](formal/spike/first-link/DECISION.md)
   — the first mechanism decision made under the method: criteria
   before evidence, provenance labels, the author's residual.
7. [`docs/tessera-cloud-demo-spec.md`](docs/tessera-cloud-demo-spec.md) —
   demonstration architecture and capability map.
8. [`docs/travelog.md`](docs/travelog.md) — contemporaneous journal of
   reality against the pre-registration.
9. [`formal/PROPERTIES.md`](formal/PROPERTIES.md) and `formal/tla/` —
   discharge status and the models themselves.
10. [`docs/reviews/`](docs/reviews/) — adversarial review artifacts and
    dispositions.

If the tracker and an amendment disagree, the **amendment wins**.

---

## Disciplines this repository enforces

- **GPG-signed commits** (author identity — *who*).
- **OpenTimestamps anchors** on commits (existence in time — *when*).
  These are two mechanisms; both are required for the public record.
- **Amend, do not silently rewrite** historical pre-registration
  documents.
- **AI as collaborator for mechanics and pushback; author owns all
  decisions** (division of labor is explicit in the pre-registration).
- **Falsification-style review** before load-bearing text is signed
  (see Amendment 1 §A1.7 and the review archive).

Setup for local hooks and OTS tooling lives under `scripts/` (see
`scripts/install-hooks.sh`).

---

## What this is not

- Not a highlight reel. Pre-registration exists so success and failure
  are both legible.
- Not formal-methods theater. Models state what they prove, what they
  assume, and what remains unclaimed (especially liveness vs. safety).
- Not an unbounded product fantasy. Commercial upside is secondary and
  deliberately constrained.

---

## License and contact

See repository metadata and commit history for authorship. The public
record of the work is the git history: signed, timestamped, and open to
scrutiny.

For the living narrative of how the work actually felt and where it
diverged from plan, start with the travelog.
