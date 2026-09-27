# Implementation architecture and user flows

This document describes the implementation that is currently present in the
repository. It is intentionally separate from the experimental dossier in the
root README: it records runtime boundaries, persisted state, and operational
risks so the diagrams remain useful as the product changes.

## System context and implementation architecture

```mermaid
flowchart TB
    User([Shopper / catalogue operator / evaluator])

    subgraph Client[Browser clients]
        SPA[React 19 + Vite source\nfrontend/src/App.jsx]
        StaticUI[Server-served static UI\napp/static/index.html + app.js]
        SPA -->|dev proxy| API
        StaticUI -->|same origin| API
    end

    subgraph Service[FastAPI service: app/main.py]
        API[API router\napp/api/routes.py]
        Singleton[Thread-safe matcher singleton\nget_matcher]
        Collector[StumperCollector singleton\napp/collector.py]
        EvalJob[In-process background evaluation thread]
        API --> Singleton
        API --> Collector
        API --> EvalJob
    end

    subgraph Retrieval[Online retrieval path]
        Decode[PIL validation + RGB conversion\nload_and_preprocess_image]
        Clip[CLIP ViT-B/32\nJewelleryEncoder\n512-d L2-normalized vector]
        Faiss[FAISS IndexFlatIP\nexact inner-product search]
        Lookup[In-memory catalogue metadata lookup]
        Verdict{Best similarity >= threshold?}
        Decode --> Clip --> Faiss --> Lookup --> Verdict
    end

    subgraph Multi[Multi-item extension]
        SAM[FastSAM-s region proposals\nor full-image fallback]
        Grid[Explicit overlapping grid strategy]
        Dedupe[Per-crop match then highest-score\nproduct-ID deduplication]
        SAM --> Dedupe
        Grid --> Dedupe
        Dedupe --> Decode
    end

    subgraph Persisted[Repository-local persisted state]
        Catalogue[data/catalogue.csv\nmetadata + relative image paths]
        CatalogueImages[data/catalogue/jewelry_dataset/...\nreference and operator-uploaded images]
        Vectors[artifacts/embeddings/catalogue_embeddings.npy\nartifacts/embeddings/product_ids.json]
        Index[artifacts/indexes/catalogue.faiss]
        StumperState[data/collected_stumpers.json + .csv\nevaluation/stumper.csv + evaluation/images]
        Reports[evaluation/results.csv + metrics.json + analysis.md\nautomated result files]
    end

    User --> SPA
    User --> StaticUI
    API --> Decode
    API --> SAM
    API --> Grid
    Lookup -.loads from.-> Catalogue
    Faiss -.loads from.-> Index
    Faiss -.aligned IDs.-> Vectors
    API --> CatalogueImages
    Collector --> StumperState
    EvalJob --> Retrieval
    EvalJob --> Reports
    API --> Reports
```

### Runtime responsibilities

| Area | Implementation | Responsibility |
| --- | --- | --- |
| Application bootstrap | `app/main.py` | Pre-warms the matcher, mounts `/data`, evaluation images, `/static`, and `/assets`, then serves the static UI from `/`. |
| API boundary | `app/api/routes.py` | Validates multipart uploads and exposes match, catalogue, stumper, health/statistics, and evaluation endpoints under `/api`. |
| Single-item retrieval | `app/retrieval/matcher.py` | Preprocesses an image, encodes it, queries FAISS, resolves product metadata, and emits `MATCH` or `UNKNOWN`. |
| Multi-item retrieval | `app/retrieval/multi_matcher.py` | Uses FastSAM proposals or the selected grid, calls the single-item matcher for each crop, and deduplicates successful top matches. |
| Data collection | `app/collector.py` | Stores one image per product/condition, synchronizes stumper metadata, and refreshes evaluation results in a background thread. |
| Evaluation | `app/evaluation/runner.py`, `automated_runner.py` | Scores the real-image and generated-image benchmarks and writes versioned-on-disk reports. |
| Offline preparation | `scripts/generate_embeddings.py`, `build_index.py`, `setup.py` | Creates normalized catalogue embeddings, the aligned product-ID mapping, and the FAISS index. |

## User-flow diagram

```mermaid
flowchart TD
    Start([Open Thuli]) --> Choose{Choose workspace}

    Choose --> Search[Visual Search]
    Search --> Upload[Upload image, camera image, or sample]
    Upload --> Mode{Single or multiple items?}
    Mode -->|Single| MatchReq[POST /api/match\nfile + top_k + threshold]
    Mode -->|Multiple| MultiReq[POST /api/match/multi\nfile + grid/SAM settings]
    MatchReq --> Rank[CLIP → FAISS → ranked candidates]
    MultiReq --> Segment[Propose crops → run matching per crop → deduplicate]
    Segment --> MultiView[Show matched products and crop results]
    Rank --> Confidence{Best score meets threshold?}
    Confidence -->|Yes| MatchView[Show ranked MATCH candidates]
    Confidence -->|No| Unknown[Show UNKNOWN and request a clearer photo]
    MatchView --> Refine[Try another image or adjust Top-K / threshold]
    Unknown --> Refine
    MultiView --> Refine

    Choose --> Catalogue[Catalogue / Collect Data]
    Catalogue --> Browse[Search and filter products]
    Browse --> AddProduct{Add original product?}
    AddProduct -->|Yes| Create[POST /api/catalogue/add\nwrite image, CSV row, vector, ID map, FAISS index]
    Create --> Browse
    AddProduct -->|No| Capture[Select product + failure condition\nupload or capture a stumper image]
    Capture --> SaveStumper[POST /api/stumper/upload\nsave image and synchronize collection/evaluation metadata]
    SaveStumper --> CollectionStatus[Review collection progress]

    Choose --> Evaluation[Evaluation Arena / Automated Stumper]
    Evaluation --> Run{Run benchmark?}
    Run -->|Real-image suite| RealRun[POST /api/evaluation/run]
    Run -->|Automated suite| AutoRun[POST /api/automated-stumper/run]
    RealRun --> Poll[Poll status]
    AutoRun --> Poll
    Poll --> Results[Read metrics, condition breakdown, failures, CSV download]
    Results --> Capture
```

## Implementation-grounded review

The repository has the pieces of a capable local demonstration and evaluation
environment. These are the changes that would make it production-ready and
make its documentation more trustworthy.

1. **Make catalogue writes atomic and serialized.** `add_catalogue_item()` mutates an image, FAISS index, ID mapping, optional embedding matrix, CSV, and memory state in sequence. A process crash or concurrent request can leave these artifacts misaligned. Use one write lock, write each artifact to a temporary sibling file, validate the vector/ID/CSV counts, then atomically replace files. A database plus object storage is the stronger long-term boundary.
2. **Move background evaluation to a job worker.** The current in-process daemon thread and module-global progress are lost on restart and cannot safely coordinate multiple Uvicorn workers. Persist jobs and progress in a queue/database (for example, Redis + RQ/Celery/Arq), and return a stable job ID.
3. **Harden upload and API access.** The service has open CORS with credentials, no authentication/authorization, and no explicit upload size, image-pixel, or rate limits. Restrict origins, disable credentialed wildcard CORS, protect catalogue/evaluation mutations, and enforce MIME, byte, and decompressed-image limits.
4. **Make multi-item fallback truthful and deterministic.** `generate_sam_crops()` silently catches all FastSAM failures and returns one full-image crop; it does not automatically select the documented grid fallback. Either log/return a `fallback_used` field and explicitly run `generate_grid_crops()`, or show the operator that segmentation was unavailable. Also add and pin `ultralytics`, which is imported at runtime but is absent from `requirements.txt`.
5. **Choose one shipped frontend.** Both `frontend/` (React/Vite source) and `app/static/` (server-served HTML/JS plus multiple hashed bundles) exist, but the FastAPI entry point serves only `app/static`. Define a build-and-copy release command or serve the Vite build directory so source, production UI, and API contract cannot drift.
6. **Correct documentation and metric source-of-truth.** The checked-in `catalogue.csv` currently has 6,195 distinct product IDs, while project documents contain several different counts. Generate catalogue size and benchmark claims from artifacts/metrics during release, and keep one canonical architecture document—this one—for runtime behavior.
7. **Add operational observability.** Emit structured logs and metrics for model/index load failures, inference latency, request size, decision distribution, FAISS/ID-map length parity, fallback use, and background job errors. Add a readiness endpoint that fails when the model, index, mapping, and catalogue are inconsistent.

## Release invariants

Before release, verify all of the following:

- `len(product_ids) == faiss_index.ntotal == embedding_rows == distinct catalogue product IDs`.
- Every `image_path` is repository-relative and resolves to an image.
- A single-item upload returns either a ranked `MATCH` or an explicit `UNKNOWN`; it never exposes an unhandled exception.
- A failed FastSAM load is visible in the API response and follows the agreed grid/full-image fallback.
- Catalogue and stumper mutations require an authorized role and are recoverable from backups.
- The deployed frontend is generated from the same revision as the API.
