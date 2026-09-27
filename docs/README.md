# Thuli — Complete Technical Documentation

Welcome to the comprehensive technical documentation for **Thuli**, a production-grade visual retrieval and similarity matching engine designed for fine jewellery catalogues (6,157 items).

This documentation hub covers the entire system from scratch: architecture, machine learning models, offline indexing pipelines, real-time query flows, REST API specifications, evaluation benchmarks, and full setup guides.

---

## Documentation Index

| Document | Description |
|---|---|
| [🎯 Master Assessment Write-Up](../WRITEUP.md) | **Core evaluator document:** Clean gate proof, "Why it is built this way", unexpected additions, empirical rejections, named weaknesses, and human-overrule logs. |
| [⚡ Setup Guide](../SETUP.md) | Quick 1-minute setup to run the complete system on any machine using Python only (Port 3000). |
| [📐 Architecture Decision Records (ADRs)](../DECISIONS.md) | 12 formal architectural decisions covering context, options, decisions, reasons, and rejected alternatives. |
| [Architecture Overview](file:///d:/PL/thuli/docs/ARCHITECTURE.md) | High-level system design, CLIP ViT-B/32 vision encoder, FAISS vector search, FastSAM segmentation, and data structures. |
| [Implementation architecture & user flows](IMPLEMENTATION_ARCHITECTURE_AND_USER_FLOWS.md) | Code-grounded runtime architecture, complete user flows, persisted state, and production-hardening recommendations. |
| [Pipeline & Ingestion](file:///d:/PL/thuli/docs/PIPELINE.md) | Step-by-step walkthrough of the offline embedding generation, FAISS index construction, and real-time query inference pipeline. |
| [REST API Reference](file:///d:/PL/thuli/docs/API_REFERENCE.md) | Complete OpenAPI/REST endpoint specifications, request/response JSON schemas, query parameters, and cURL examples. |
| [Evaluation & Benchmarks](file:///d:/PL/thuli/docs/EVALUATION_GUIDE.md) | Evaluation methodology, physical stumper conditions, metrics (Top-1/Top-5, FAR, FRR, Latency), and the 900 automated stumper benchmark. |
| [Setup & Run Guide](file:///d:/PL/thuli/docs/SETUP_AND_RUN.md) | Step-by-step installation, dependency configuration, dataset setup, and execution instructions from scratch. |

---

## Directory Readmes

Every directory in this project contains its own dedicated `README.md`:

- [`app/README.md`](file:///d:/PL/thuli/app/README.md): FastAPI backend, API routes, retrieval engine, image preprocessing, and evaluation runners.
- [`data/README.md`](file:///d:/PL/thuli/data/README.md): Catalogue image hierarchy (6,157 items), CSV metadata schema, and stumper collection.
- [`artifacts/README.md`](file:///d:/PL/thuli/artifacts/README.md): Generated CLIP `.npy` embeddings, FAISS `.faiss` vector indices, and product ID mappings.
- [`evaluation/README.md`](file:///d:/PL/thuli/evaluation/README.md): Handheld stumper dataset (115 images), automated benchmark (900 images), multi-item images, and analysis reports.
- [`experiments/README.md`](file:///d:/PL/thuli/experiments/README.md): Ablation studies comparing saliency/crop pre-processing with raw CLIP embeddings.
- [`frontend/README.md`](file:///d:/PL/thuli/frontend/README.md): React 18 + Vite single-page application, Visual Search UI, and Evaluation Arena dashboard.
- [`scripts/README.md`](file:///d:/PL/thuli/scripts/README.md): Offline CLI scripts for embedding generation, index building, synthetic dataset generation, and verification.
- [`tests/README.md`](file:///d:/PL/thuli/tests/README.md): Pytest unit, integration, and regression test suites.
- [`phases/README.md`](file:///d:/PL/thuli/phases/README.md): Phase-by-phase implementation log and engineering notes.

---

## Quick Architecture Summary

```
                      ┌────────────────────────────────────────┐
                      │          React 18 + Vite (SPA)         │
                      │  Visual Search | Evaluation Arena | UI │
                      └───────────────────┬────────────────────┘
                                          │ HTTP / JSON
                                          ▼
                      ┌────────────────────────────────────────┐
                      │            FastAPI Backend             │
                      │               (Port 3000)              │
                      └─────┬────────────────────────────┬─────┘
                            │                            │
             Single Item    │                            │ Multi-Item Image
                            ▼                            ▼
                 ┌──────────────────────┐    ┌──────────────────────┐
                 │    PIL Preprocess    │    │ FastSAM Segmentation │
                 │      RGB Convert     │    │  Bounding Box Crops  │
                 └──────────┬───────────┘    └──────────┬───────────┘
                            │                           │
                            └─────────────┬─────────────┘
                                          │
                                          ▼
                             ┌────────────────────────┐
                             │    CLIP ViT-B/32       │
                             │  512-d L2 Normalized   │
                             └────────────┬───────────┘
                                          │
                                          ▼
                             ┌────────────────────────┐
                             │   FAISS IndexFlatIP    │
                             │  6,157 Catalogue Items │
                             └────────────┬───────────┘
                                          │
                                          ▼
                             ┌────────────────────────┐
                             │  Confidence Threshold  │
                             │   sim >= 0.75 ? MATCH  │
                             │         : UNKNOWN      │
                             └────────────────────────┘
```
