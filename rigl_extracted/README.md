# RigL implementation, extracted from `ODT_Complete_Reference_v2.pdf`

The RigL implementation in that reference is spread across 41 sections of 39
chapters — each chapter documents one ODT source file and ends with a
"Missing RigL Code" section. This directory consolidates every fragment into
build order.

The companion document **`RigL_Implementation_Line_by_Line.pdf`** (repository
root) explains every line of this code individually and lists the ten defects
found while consolidating.

## Files

| File | Contents |
|---|---|
| `RigL.h` | Public interface: `rigLStep()` and the two K-selection helpers |
| `RigL.c` | `rigLStep()` — the algorithm, with fixes D1, D2 and D9 applied and marked |
| `MinMax_rigl.c` | `findAbsKthSmallestActive()` / `findAbsKthLargestInactive()`, plus a fixed-memory histogram variant that resolves defect D8 |
| `PATCHES.md` | The edits to existing ODT files: Linear.h, Matmul.c, Sgd.c, AdamW.c, Serialize.c, UserAPI.c, TrainingLoopApi.c |

## Build order

1. `MinMax_rigl.c` — the two K-selection functions (no dependencies)
2. `Linear.h` — add the `weightMask` field (see `PATCHES.md`)
3. `Matmul.c`, `Sgd.c`, `AdamW.c` — mask-aware loops
4. `RigL.c` — the algorithm itself
5. `Serialize.c` — persist the mask
6. `UserAPI.c`, `TrainingLoopApi.c` — create the mask and call `rigLStep()`

## Status

This code is a faithful consolidation of the source's algorithm with three
defects repaired and the repairs labelled inline. **It has not been compiled
against the ODT headers.** It assumes two helpers the source does not
document — `cloneBoolTensor()` and `freeBoolTensor()` — which you may need to
write. Defect D8 (a 259 KB `malloc` on a 320 KB device) is resolved only if
you build the histogram variant in `MinMax_rigl.c`.

Read chapter 13 of the PDF before running any of this. Three defects — D3
(the gradients GROW needs may never be computed), D8 (heap exhaustion) and D4
(contradictory call ordering) — are the difference between RigL and an
expensive random mask.
