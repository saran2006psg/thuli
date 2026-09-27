# Evaluation Methodology & Benchmark Guide

This document outlines the evaluation framework, physical perturbation conditions, scoring formulas, and automated benchmark results for the **Thuli Jewellery Retrieval Engine**.

---

## 1. Evaluation Philosophy: "Stump the Model"

Production visual retrieval systems encounter photos taken in uncontrolled conditions. Rather than testing on clean white-background catalogue images, Thuli is evaluated against real-world handheld camera captures designed specifically to "stump" retrieval models.

---

## 2. The 10 Physical Challenge Conditions

| Condition | Visual Perturbation Description | Real-World Origin |
|---|---|---|
| `hand` | Jewellery worn on fingers, wrist, or held across palm | Mobile photo taken by customer wearing the item |
| `clutter` | Jewellery surrounded by coins, keys, fabric, patterns | Cluttered table or jewellery drawer |
| `bad_lighting` | Under-exposed, dark ambient lighting | Dim indoor or evening retail lighting |
| `bright_lighting` | Over-exposure, washed out highlights | Direct sunlight or harsh flash photography |
| `odd_angle` | Extreme perspective, tilted, skewed 45° angle | Angled phone capture rather than top-down |
| `occlusion` | 30–50% of the jewellery piece covered by another object | Partial coverage by fingers or packaging |
| `motion_blur` | Hand tremor or rapid motion | Shaky handheld photography |
| `reflection` | Specular glare on polished gold/silver surfaces | Strong overhead showroom spot lights |
| `distance` | Item photographed far away (occupying <15% of frame) | Full-body or casual wide-shot selfie |
| `noise` | High ISO sensor grain and digital artifacts | Low-light camera sensor noise |

---

## 3. Mathematical Metric Definitions

### 1. Top-1 Accuracy
$$\text{Top-1 Accuracy} = \frac{1}{N} \sum_{i=1}^N \mathbb{I}(\text{Top1 Candidate Category} = \text{Ground Truth Category})$$

### 2. Top-5 Accuracy
$$\text{Top-5 Accuracy} = \frac{1}{N} \sum_{i=1}^N \mathbb{I}(\text{Ground Truth Category} \in \text{Top-5 Candidates})$$

### 3. False Acceptance Rate (FAR)
A query that the system accepted as a match ($\text{sim} \ge \tau$) but returned the wrong product:
$$\text{FAR} = \frac{\text{Count of Wrong Matches}}{\text{Total Scored Queries}}$$

### 4. False Rejection Rate (FRR)
A query where the genuine catalogue item was photographed, but the system returned `UNKNOWN` ($\text{sim} < \tau$):
$$\text{FRR} = \frac{\text{Count of UNKNOWN Verdicts}}{\text{Total Scored Queries}}$$

### 5. Latency Percentiles (P50, P95)
Measured from query byte reception to JSON response transmission:
- **P50 (Median):** Typical search speed experienced by 50% of users.
- **P95:** Tail latency for worst-case complex images.

---

## 4. Benchmark Performance Summary

| Benchmark | Total Images | Top-1 Accuracy | Top-5 Accuracy | FAR | FRR | Median Latency |
|---|---|---|---|---|---|---|
| **Handheld Stumper (Real)** | 115 | **72.1%** | **89.2%** | 20.7% | 7.2% | **89 ms** |
| **Automated Stumper (Synthetic)** | 900 | **68.4%** | **87.1%** | 23.1% | 8.5% | **92 ms** |
| **Clean Catalogue Validation** | 200 | **98.5%** | **100.0%** | 1.5% | 0.0% | **81 ms** |

---

## 5. Condition Robustness Ranking

Across 900 automated tests, performance by physical condition ranks as follows:
1. `bright_lighting`: **82.0%** Top-1 (CLIP features are largely invariant to luminance shift).
2. `distance`: **78.0%** Top-1.
3. `bad_lighting`: **74.0%** Top-1.
4. `noise`: **71.0%** Top-1.
5. `reflection`: **67.0%** Top-1.
6. `odd_angle`: **65.0%** Top-1.
7. `motion_blur`: **62.0%** Top-1 (Loss of fine diamond prong detail).
8. `occlusion`: **59.0%** Top-1 (Partial visibility alters overall global vector).
9. `clutter`: **58.0%** Top-1 (Background objects blend into global representation).
