# Patches to existing ODT files

Six existing files need edits. Each is small; the risk column says what
breaks if it is wrong. Line-by-line explanations are in
`RigL_Implementation_Line_by_Line.pdf`, chapters 5–11.

---

## 1. `Linear.h` — add the mask field  (source §11.4)

```c
typedef struct linearConfig {
    /* ... existing fields, DO NOT retype them from the PDF: the two
       listings in §11.4 and §39.4 disagree. Edit the real header. ... */
    tensor_t *weightMask;   /* NEW: NULL = dense, non-NULL = RigL sparse */
} linearConfig_t;
```

In `linearInitConfig()`:

```c
cfg->weightMask = NULL;     /* dense by default — keeps every existing test green */
```

**Risk if wrong:** none if NULL-defaulted. Omitting the initialiser leaves the
pointer indeterminate and produces crashes that look random.

---

## 2. `Matmul.c` — mask-aware inner loop  (source §8.4)

```c
for (size_t i = 0; i < aColumns; i++) {

    size_t flatIdx = rowIndex * aColumns + i;

    if (weightMask != NULL && !tensorBoolGet(weightMask, flatIdx))
        continue;                       /* inactive: contributes nothing */

    float aVal = readBytesAsFloat(&A->data[aByteIdx]);
    float bVal = readBytesAsFloat(&B->data[bByteIdx]);
    result += aVal * bVal;
}
```

Thread `weightMask` down as a parameter (add `matmulFloat32TensorsWithMask()`
and have existing callers pass NULL). Do **not** use a file-scope global — it
is not re-entrant and a forgotten reset applies one layer's mask to another.

**⚠ Mask the FORWARD and LOSS-PROPAGATION matmuls only. Leave the
WEIGHT-GRADIENT matmul dense.** RigL grows connections using the gradients of
inactive weights; if those are masked to zero, GROW selects arbitrary
positions and you have static sparsity with extra steps. This is defect D3.

**Risk if wrong:** a misaligned `flatIdx` skips the wrong weights and the
model still trains — to a plausible but wrong result.

**Verify:** `getMatmulInstructionCounter()` should fall from 73,728 to ~7,373
on a 90%-sparse 64×1152 layer.

---

## 3. `Sgd.c` — mask-aware update  (source §12.4)

```c
for (size_t i = 0; i < nElem; i++) {

    if (mask != NULL && !tensorBoolGet(mask, i)) {
        out[i]  = 0.0f;
        grad[i] = 0.0f;
        /* also clear the momentum buffer entry here — defect D5 */
        continue;
    }

    float g = grad[i] + ctx->weightDecay * param[i];
    out[i]  = param[i] - ctx->lr * g;
}
```

`sgdUpdateCtx_t` needs a `tensor_t *weightMask` field, and whoever configures
the optimiser must copy it from `linearConfig_t`. The source does not spell
out this plumbing step; if you forget it, everything compiles and no masking
happens.

**Risk if wrong:** inactive weights drift off zero and the sparsity is a
fiction only the mask believes in.

---

## 4. `AdamW.c` — mask-aware update with moment clearing  (source §13.4)

```c
if (mask != NULL && !tensorBoolGet(mask, i)) {
    param[i] = 0.0f;
    grad[i]  = 0.0f;
    m[i]     = 0.0f;        /* clear first-moment history  */
    v[i]     = 0.0f;        /* clear second-moment history */
    continue;
}
```

Without clearing `m` and `v`, a weight dropped at step 1000 and regrown at
step 1500 takes its first update from stale moment history that no longer
applies.

**Memory warning (defect D6):** §13.4 quotes 88 KB by counting only the 7,373
*active* weights. `m` and `v` are allocated densely, so the real figure for
the 1152×64 layer is 1.13 MB — it does not fit in 320 KB of SRAM. Use SGD, or
shrink the layer.

---

## 5. `Serialize.c` — persist the mask  (source §17.5)

```c
void serializeSparsity(tensor_t *mask, FILE *fp) {
    if (mask == NULL || mask->quantization->type != BOOL) {
        uint8_t noMask = 0; fwrite(&noMask, 1, 1, fp); return;
    }
    uint8_t hasMask = 1; fwrite(&hasMask, 1, 1, fp);
    size_t n = calcNumberOfElementsByTensor(mask);
    fwrite(mask->data, 1, (n + 7) / 8, fp);
}

tensor_t *deserializeSparsity(size_t n, FILE *fp) {
    uint8_t hasMask = 0;
    fread(&hasMask, 1, 1, fp);
    if (!hasMask) return NULL;
    tensor_t *mask = allocBoolTensor(n);
    fread(mask->data, 1, (n + 7) / 8, fp);
    return mask;
}
```

Then thread the mask through `serializeTensor(t, mask, f)` and call it from
`serializeLinear()` as `serializeTensor(weights, cfg->weightMask, f)`.

**⚠ This changes the checkpoint format for dense models too** — one presence
byte per tensor record. Chapter 17 of the source calls the format "locked
v2"; bump it to v3 and have the reader accept both (defect D9). Neither
`fwrite` nor `fread` checks its return value; on an SD card, add that.

---

## 6. `UserAPI.c` — create the mask  (source §38.4)

```c
if (spec->sparse) {
    size_t maskBits = inFeat * outFeat;
    tensor_t *mask  = createBoolTensor(maskBits);
    bernoulliFillMask(mask, 1.0f - spec->sparsity);  /* argument is P(ACTIVE) */
    zeroInactiveWeights(linearCfg, mask);            /* omitted in §11.4 */
    linearCfg->weightMask = mask;
}
```

Call `rngSetSeed()` before this **and** before the training loop — the mask
draw consumes RNG state that stochastic rounding would otherwise use, so
reproducibility depends on the order of operations.

Nothing in the source says who frees this tensor. `linearConfig_t` already
has an `ownsQuantizations` flag for exactly this question; the mask needs the
same treatment or it leaks on every model teardown.

---

## 7. `TrainingLoopApi.c` — call it  (source §39.9)

```c
#define RIGL_INTERVAL 100

forward(model, b->input);
backward(model, b->label);

if (step % RIGL_INTERVAL == 0)
    rigLStep(model, nLayers, 0.3f, step, (size_t)(0.8f * totalSteps));

optimizerFunctions[SGD_M].step(&optim);     /* mask-aware update */
step++;
```

**Ordering (defect D4):** §37.4 says call rigLStep *after* the optimiser;
§39.9 says *before*, and its code does that. **Before is correct** — the
optimiser zeroes the gradients of inactive weights, which are exactly the
gradients GROW ranks.

**Pass `0.8 * totalSteps`, not `totalSteps`** (defect D9), or the mask keeps
swapping into the final epoch — the thing the cosine schedule exists to
prevent.

`trainingConfig_t` needs: `useRigL`, `rigLInterval`, `rigLTEnd`,
`rigLAlphaInit`.
