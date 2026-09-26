# Phase 7 — Baseline Evaluation Report

> Generated: 2026-09-26T13:12:33.841982+00:00
> Model: CLIP ViT-B/32 | Index: FAISS IndexFlatIP | Threshold: 0.75

## Summary

| Metric | Value |
|---|---|
| Total Images | 117 |
| Valid Images | 117 |
| **Top-1 Accuracy** | **73.5%** |
| **Top-5 Accuracy** | **89.7%** |
| MATCH decisions | 109 |
| UNKNOWN decisions | 8 |
| Wrong Matches | 23 |
| **False Acceptance Rate (FAR)** | **19.66%** |
| **False Rejection Rate (FRR)** | **6.84%** |
| Mean Latency | 139.83 ms |
| Median Latency | 131.12 ms |
| P95 Latency | 231.71 ms |

## Per-Condition Accuracy

| Condition | N | Top-1 | Top-5 |
|---|---|---|---|
| `bad_lighting` | 10 | 100.0% | 100.0% |
| `bright_lighting` | 12 | 83.3% | 100.0% |
| `clutter` | 14 | 64.3% | 78.6% |
| `distance` | 12 | 58.3% | 75.0% |
| `hand` | 1 | 100.0% | 100.0% |
| `hand_wrist` | 11 | 72.7% | 100.0% |
| `motion_blur` | 12 | 75.0% | 100.0% |
| `motionblur` | 3 | 33.3% | 66.7% |
| `noise` | 1 | 0.0% | 0.0% |
| `normal` | 16 | 93.8% | 100.0% |
| `occlusion` | 12 | 58.3% | 75.0% |
| `odd_angle` | 12 | 66.7% | 91.7% |
| `reflection` | 1 | 100.0% | 100.0% |

## Worst Failures (Top-10)

| Image | Ground Truth | Predicted | Similarity | GT Rank | Condition |
|---|---|---|---|---|---|
| `id46` | `bracelet` | `bracelet` | 0.5594 | 1 | `distance` |
| `id04` | `ring` | `earring` | 0.6624 | -1 | `clutter` |
| `id18` | `ring` | `bracelet` | 0.6862 | 3 | `occlusion` |
| `id05` | `necklace` | `ring` | 0.7171 | 4 | `noise` |
| `id14` | `ring` | `ring` | 0.7270 | 1 | `distance` |
| `id58` | `ring` | `ring` | 0.7403 | 1 | `clutter` |
| `id113` | `bracelet` | `bracelet` | 0.7410 | 1 | `distance` |
| `id76` | `bracelet` | `bracelet` | 0.7411 | 1 | `odd_angle` |
| `id08` | `ring` | `bracelet` | 0.7578 | 3 | `motionblur` |
| `id03` | `bracelet` | `necklace` | 0.7668 | -1 | `motionblur` |

## Dataset Progress

- Current: 117 / 100 images
- Progress: 117.0%
