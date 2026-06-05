# Pre-Registration: Budgeted Three-Wake Chain Repair

Date: 2026-06-05

## Research Question

Does the budgeted three-wake chain pass after repairing placeholder scope and
closing non-secret intermediate schemas?

The first budgeted three-wake panel showed that the continuation budget worked,
but the chain failed because nested final-wake placeholders were expanded too
early and one first wake leaked the exact phrase into an open
`chain_intermediate` note field.

## Hypotheses

- H481: Step 1 budget stop still works.
- H482: Step 2 budget stop still works.
- H483: Final wake receives the bridge wake's generated record context, not the
  first wake record context.
- H484: Final wake recovers the exact phrase and uses bridge evidence.
- H485: All three wakes are first-pass strict-valid with no phrase leak and no
  broad repair.

## Predictions

For `N=2` replicates using `deepseek/deepseek-v4-pro`:

- step 1 stop reason is `auto_continuation_limit_reached` in both rows;
- step 2 stop reason is `auto_continuation_limit_reached` in both rows;
- step 3 quiesces in both rows;
- first, bridge, and final wakes are strict-valid in both rows;
- first and bridge states contain no exact phrase;
- final wake receives bridge-record context in both rows;
- final evidence references the bridge result record and `word-word-number`;
- no repair is attempted in any wake.

## Falsification Criteria

The repair is not supported if:

- final wake remains bound to the first wake record;
- closed schemas cause provider/tool failures;
- the model still leaks the phrase in first or bridge state;
- the scheduler budget no longer splits the chain;
- any wake requires broad repair.

## Method

Use the same runner logic as
`budgeted_three_wake_chain_20260605`, after the placeholder-scope patch, but
override the terminal schemas so:

- `chain_intermediate.additionalProperties = false`;
- `chain_bridge` uses a closed structural schema.

No manual bridge/final append is allowed. The scheduler must use
`auto_continuations=True` with `max_auto_continuations=1`.

## Analysis Plan

Compare directly against the failed budgeted three-wake panel. The decisive
repair endpoints are final bridge-record context delivery and absence of phrase
leaks in first/bridge states.
