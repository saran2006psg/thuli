Sure. For our **PS2 – Stump the Model (Jewellery Image Retrieval)** project, we can divide everything into these simple phases:

### Phase 1 — Catalogue Setup
**Goal:** Get the 5,000+ jewellery catalogue ready.

- Find public jewellery dataset/source
- Collect/download images
- Store product metadata
- Clean invalid/duplicate images
- Create `catalogue.csv`

**Output:** Clean catalogue with 5,000+ images.

---

### Phase 2 — Image Embedding
**Goal:** Convert every jewellery image into a numerical vector.

- Select pretrained vision model
- Preprocess images
- Generate embeddings
- Normalize embeddings
- Save embeddings

**Output:** Image → embedding vectors.

---

### Phase 3 — FAISS Retrieval
**Goal:** Make searching through 5,000+ images fast.

- Build FAISS index
- Store catalogue embeddings
- Implement similarity search
- Retrieve Top-5 candidates

**Output:** Query image → Top-5 similar catalogue images.

---

### Phase 4 — Baseline Matcher
**Goal:** Create the actual matching logic.

```text
Query Image
    ↓
Preprocessing
    ↓
Vision Encoder
    ↓
Embedding
    ↓
FAISS
    ↓
Top-5 Candidates
    ↓
Similarity + Threshold
    ↓
MATCH / UNKNOWN
```

**Output:** Working retrieval system.

---

### Phase 5 — API
**Goal:** Turn the matcher into a usable application.

- Build FastAPI
- `/match` endpoint
- Upload image
- Return Top-5 results
- Return similarity scores
- Handle errors

**Output:** Working API.

---

### Phase 6 — Clean Evaluation
**Goal:** Check how well the baseline works on normal images.

Measure:

- Top-1 accuracy
- Top-5 accuracy
- Retrieval latency
- Similarity scores

**Output:** Baseline results.

---

### Phase 7 — Stumper Dataset
**Goal:** Attack the model with difficult real-world images.

Take **100+ phone photos** with:

- Bad lighting
- Different angles
- Occlusion
- Clutter
- Motion blur
- Reflections
- Hand/wrist visible

Label each photo with:

```text
image → correct product → failure condition
```

**Output:** 100+ hard test images.

---

### Phase 8 — Stumper Evaluation
**Goal:** Find where the model fails.

Run the **same production matcher** on all stumper images.

Measure:

```text
Overall Top-1
Overall Top-5
↓
Bad lighting accuracy
Angle accuracy
Occlusion accuracy
Blur accuracy
Reflection accuracy
Clutter accuracy
```

Also measure latency.

**Output:** Failure analysis.

---

### Phase 9 — Improvement Experiment
**Goal:** Fix the biggest weakness we discovered.

Example:

```text
Observation:
Reflection causes many failures.

        ↓

Hypothesis:
Better preprocessing/model representation
may improve reflection robustness.

        ↓

Experiment

        ↓

Compare against baseline

        ↓

Keep or reject based on results
```

**Output:** Evidence-based improvement.

---

### Phase 10 — Unknown / No-Match
**Goal:** Prevent the system from confidently returning the wrong jewellery.

Test with **out-of-catalogue items**.

```text
Unknown jewellery
       ↓
FAISS
       ↓
Similarity score
       ↓
Threshold
       ↓
UNKNOWN
```

Measure false accepts/rejects.

---

### Phase 11 — Final Benchmark
**Goal:** Measure the final system properly.

Compare:

| Metric | Baseline | Improved |
|---|---:|---:|
| Top-1 | measured | measured |
| Top-5 | measured | measured |
| Latency | measured | measured |
| Hard-set accuracy | measured | measured |
| Unknown detection | measured | measured |

Only use **actual measured numbers**.

---

### Phase 12 — Documentation & Submission
**Goal:** Make the project evaluation-ready.

Prepare:

- `README.md`
- `DECISIONS.md`
- Experiment reports
- Evaluation results
- Error analysis
- Tests
- Docker setup
- AI coding logs in `/logs`
- Clean-machine verification

---

## Overall Flow

```text
PHASE 1
Catalogue
   ↓
PHASE 2
Embeddings
   ↓
PHASE 3
FAISS
   ↓
PHASE 4
Baseline Matcher
   ↓
PHASE 5
FastAPI
   ↓
PHASE 6
Baseline Evaluation
   ↓
PHASE 7
100+ Stumper Images
   ↓
PHASE 8
Failure Analysis
   ↓
PHASE 9
Improve
   ↓
PHASE 10
Unknown Detection
   ↓
PHASE 11
Final Benchmark
   ↓
PHASE 12
Documentation + Submission
```

We should go **Phase 1 → finish it → verify it → Phase 2 → finish it**, etc. This will also make your AI development logs and `DECISIONS.md` much easier to maintain.
 
---
 
## Evaluation Philosophy: Defending the 70% Real-World Reality
 
> *"A matcher that scores well on clean images and collapses on your own hard set is an honest and useful result, provided you diagnose why. Define your own evaluation methodology and defend it. Tell us which failure conditions hurt most, what you tried in response, and what did not work. We would rather read a clear-eyed account of a system at seventy percent than a claim of ninety-five with no error analysis."*
 
### Summary of Findings:
1. **The Gap & Automated Adversarial Generation**:
   - Clean / Holdout: **95.83% Top-1**
   - Real Hand-Shot Stumper (113 images): **72.57% Top-1** (Failure Rate: **27.43%**)
   - Hardest Stumper benchmark (39 images): **64.10% Top-1** (Failure Rate: **35.90%**)
   - **Automated Adversarial Stumper (900 tests)**: **52.22% Top-1** (Failure Rate: **47.78%**)
   - **Verdict**: Automated stumper **DEFEATED the matcher at a higher rate** (+20.35% higher failure rate than hand-shot)!
2. **Defending Our Methodology**:
   - Genuine phone photography capturing real optical flares, motion blur, and background textures.
   - 10-condition failure taxonomy.
   - Strict rejection threshold ($\tau = 0.75$): sub-threshold predictions strictly counted as misses (`UNKNOWN`) to prevent confident wrong matches in luxury jewellery visual search.
3. **Worst Failure Modes**:
   - Distance (35.0%) & Bad Lighting (5.0%): ViT-B/32 patch token dilution and dynamic range collapse.
   - Motion blur (59.0%) & Occlusion (56.0%): Loss of closed-loop continuity causes bracelets to be misclassified as necklaces/rings.
4. **What Was Tried & What Failed**:
   - Experiment 01 (Saliency-Aware Cropping): Helped compact rings (+6.4% to +12.9%), but severed continuous loops on necklaces and bracelets, causing Top-1 to crash to 41.03%.
   - **Decision**: Strictly rejected. Production system maintains the uncropped baseline with verified error boundaries.
5. **Full Reference**:
   - See [EVALUATION_METHODOLOGY_AND_GAP_ANALYSIS.md](file:///d:/PL/thuli/EVALUATION_METHODOLOGY_AND_GAP_ANALYSIS.md) and [DECISIONS.md](file:///d:/PL/thuli/DECISIONS.md) (D-011 to D-014).