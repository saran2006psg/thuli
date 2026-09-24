# Session Log 06 — Phase 6: Stumper Dataset & Evaluation Setup

**Date:** 2026-09-24  
**Focus:** Building Real-World Stumper Dataset Infrastructure, Validation Tools, Production Evaluation Pipeline & Tests  
**Status:** Completed & Tested (65/65 tests passing)

---

## 1. Objectives
1. Design and establish the directory structure and metadata schema for 100+ real-world phone-captured stumper queries.
2. Establish a standard taxonomy of 9 failure conditions + 1 clean control condition.
3. Implement `scripts/validate_stumper_dataset.py` to ensure dataset integrity (existence, PIL readability, valid catalogue IDs, allowed taxonomy).
4. Implement `scripts/evaluate.py` to run evaluation against the production `JewelleryMatcher` without altering the baseline architecture.
5. Create comprehensive unit tests in `tests/test_evaluation.py` for dataset validation and metric calculation logic.
6. Prepare documentation: `evaluation/README.md`, `phases/phase_06_stumper_evaluation.md`, `logs/session_06.md`, `phases/README.md`, `done.md`.

---

## 2. Work Done & Implementation Details

### A. Evaluation Directory Setup
- Created `evaluation/stumper.csv` template with columns: `image_id,product_id,failure_condition,notes,image_path`.
- Created `evaluation/images/` directory for phone-captured photos.
- Created `evaluation/README.md` providing clear instructions and guidelines for taking photos across all 9 failure categories.

### B. Validation Script (`scripts/validate_stumper_dataset.py`)
- Verified against `data/catalogue.csv` (6,157 valid product IDs).
- Enforces strict taxonomy of failure conditions:
  - `bad_lighting`
  - `unusual_angle`
  - `occlusion`
  - `cluttered_background`
  - `motion_blur`
  - `reflection`
  - `hand_wrist_visible`
  - `distance_scale`
  - `multiple_items`
  - `clean_control`
- Verifies image files with PIL (`Image.open().verify()`) and catches missing or corrupted files.

### C. Evaluation Pipeline (`scripts/evaluate.py`)
- Integrates production `JewelleryMatcher` from `app.retrieval.matcher`.
- Calculates:
  - Overall Top-1 & Top-5 accuracy percentages and counts
  - Decision breakdown (`MATCH` vs `UNKNOWN`)
  - Per-condition Top-1 and Top-5 accuracy breakdown + mean cosine similarities
  - Retrieval latency percentiles (mean, median, p95, p99, min, max)
- Saves outputs:
  - `evaluation/results.csv` (per-query rankings, ground truth, top-1 similarity, latency)
  - `evaluation/metrics.json` (JSON metric structure)
  - `evaluation/analysis.md` (Markdown error analysis report listing Top-5 retrieval failures)

### D. Automated Unit Tests (`tests/test_evaluation.py`)
- `test_empty_template_handling`: Verifies template handling with `allow_empty=True/False`.
- `test_valid_stumper_dataset`: Validates correct stumper records.
- `test_missing_required_columns`: Rejects incomplete CSVs.
- `test_duplicate_image_id`: Rejects duplicate IDs.
- `test_nonexistent_product_id`: Rejects product IDs not present in catalogue.
- `test_invalid_failure_condition`: Rejects conditions outside the allowed taxonomy.
- `test_missing_image_file`: Rejects missing image files.
- `test_evaluate_matcher_with_mock`: End-to-end test of evaluation pipeline, metric calculations, and output files.

---

## 3. Test Suite Verification

Full test suite execution:
```bash
python -m pytest tests/ -v
```
Result: **65 passed in 44.86s** (100% passing across all modules).

---

## 4. Key Decisions & Guardrails
- **Zero Model Modifications:** Did not modify CLIP, FAISS index, or matcher parameters prior to measuring real baseline data.
- **No Fake Data / Synthetic Numbers:** Did not invent fake accuracy metrics. The pipeline is primed and ready for the user's real smartphone photos.
