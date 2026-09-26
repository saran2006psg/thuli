# Phase 7 — Baseline Evaluation Report

> Generated: 2026-09-26T10:01:26.948519+00:00
> Model: CLIP ViT-B/32 | Index: FAISS IndexFlatIP | Threshold: 0.75

## Summary

| Metric | Value |
|---|---|
| Total Images | 111 |
| Valid Images | 111 |
| **Top-1 Accuracy** | **73.0%** |
| **Top-5 Accuracy** | **89.2%** |
| MATCH decisions | 103 |
| UNKNOWN decisions | 8 |
| Mean Latency | 76.26 ms |
| Median Latency | 74.8 ms |
| P95 Latency | 93.11 ms |

## Per-Condition Accuracy

| Condition | N | Top-1 | Top-5 |
|---|---|---|---|
| `bad_lighting` | 7 | 85.7% | 100.0% |
| `bright_lighting` | 12 | 91.7% | 100.0% |
| `clutter` | 14 | 64.3% | 78.6% |
| `distance` | 12 | 58.3% | 75.0% |
| `hand` | 1 | 100.0% | 100.0% |
| `hand_wrist` | 11 | 81.8% | 100.0% |
| `motion_blur` | 12 | 75.0% | 100.0% |
| `motionblur` | 3 | 33.3% | 66.7% |
| `noise` | 1 | 0.0% | 0.0% |
| `normal` | 13 | 92.3% | 100.0% |
| `occlusion` | 12 | 58.3% | 75.0% |
| `odd_angle` | 12 | 66.7% | 91.7% |
| `reflection` | 1 | 100.0% | 100.0% |

## Worst Failures (Top-10)

| Image | Ground Truth | Predicted | Similarity | GT Rank | Condition |
|---|---|---|---|---|---|
| `id46` | `bracelet` | `bracelet` | 0.5646 | 1 | `distance` |
| `id04` | `ring` | `earring` | 0.6625 | -1 | `clutter` |
| `id05` | `necklace` | `ring` | 0.7171 | 4 | `noise` |
| `id76` | `bracelet` | `bracelet` | 0.7387 | 1 | `odd_angle` |
| `id113` | `bracelet` | `bracelet` | 0.7401 | 1 | `distance` |
| `id58` | `ring` | `ring` | 0.7403 | 1 | `clutter` |
| `id18` | `ring` | `earring` | 0.7421 | 2 | `occlusion` |
| `id14` | `ring` | `ring` | 0.7432 | 1 | `distance` |
| `id08` | `ring` | `bracelet` | 0.7587 | 3 | `motionblur` |
| `id03` | `bracelet` | `necklace` | 0.7667 | -1 | `motionblur` |

## Dataset Progress

- Current: 111 / 100 images
- Progress: 111.0%
