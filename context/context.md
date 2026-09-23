# PS2 — STUMP THE MODEL
## Complete Implementation Context / Master Project Specification

## 1. PROBLEM STATEMENT

Build an image retrieval system that can identify an exact jewellery catalogue item from a photograph taken in the real world.

The system must contain a catalogue of at least 5,000 jewellery products/images collected from a public source.

Given a user photograph, the system should:
1. Convert the image into a visual embedding.
2. Search the catalogue for visually similar products.
3. Rank the candidates.
4. Return the Top-5 candidate products with similarity/confidence scores.
5. Decide whether the item is sufficiently similar to a catalogue item.
6. If the similarity is below an experimentally determined threshold, reject it as an UNKNOWN item rather than blindly returning the nearest catalogue item.

The project has TWO connected parts:

PART A:
Catalogue + retrieval/matching system.
This is the actual system under test.

PART B:
Stumper + evaluation system.
This deliberately tests Part A using difficult real-world photographs, measures failures, performs error analysis, and drives improvements.

The important principle is:

BUILD → ATTACK → MEASURE → ANALYZE → IMPROVE → RE-MEASURE

The goal is not merely to achieve a high accuracy number. The goal is to understand how the retrieval system behaves under real-world conditions, identify its weaknesses, test improvements, and provide evidence for engineering decisions.


# 2. ASSIGNMENT REQUIREMENTS

The system must satisfy the following core requirements:

- Catalogue contains at least 5,000 images.
- Catalogue should be assembled from a public source.
- Jewellery is the selected product category.
- Input is a photograph of a jewellery item.
- Return Top-5 candidate catalogue items.
- Return similarity/confidence scores.
- Build a real retrieval system rather than a fixed 5,000-class classifier.
- Collect at least 100 difficult photographs personally using a phone.
- Difficult photographs should include conditions such as:
  - bad/difficult lighting
  - unusual angles
  - partial occlusion
  - cluttered backgrounds
  - motion blur
  - reflections
  - hand/wrist appearing in frame
- Every hard image must have ground-truth product identification and failure-condition labels.
- Evaluation must report accuracy broken down by failure condition.
- Measure lookup latency.
- Analyze failure cases.
- Explain what was tried and what did/did not work.
- Use evidence from experiments to justify improvements.

Optional harder direction:
- Unknown/no-match detection using items that are not present in the catalogue.
- Report false accept/reject behaviour for unknown items.

The project should prioritize solving one difficult problem properly rather than implementing many optional features superficially.


# 3. CORE ARCHITECTURAL PRINCIPLE

The system is NOT a traditional classification model with 5,000 output classes.

Instead:

IMAGE
  ↓
VISION ENCODER
  ↓
EMBEDDING VECTOR
  ↓
VECTOR SIMILARITY SEARCH
  ↓
RANKED CANDIDATES
  ↓
MATCH / UNKNOWN DECISION

This is an image retrieval / nearest-neighbour matching architecture.

The catalogue embeddings are generated offline.

The query embedding is generated at runtime.

Both must use the same vision embedding model and compatible preprocessing.


# 4. COMPLETE ARCHITECTURE

The architecture is divided into:

PART A — CATALOGUE & RETRIEVAL SYSTEM
PART B — STUMPER & EVALUATION SYSTEM

PART A is the SYSTEM UNDER TEST.

PART B invokes the exact same Part A matching pipeline and evaluates it.

------------------------------------------------------------
PART A — CATALOGUE & RETRIEVAL SYSTEM
------------------------------------------------------------

                    PUBLIC JEWELLERY SOURCE
                              |
                              v
                       +--------------+
                       | Web Scraper  |
                       +------+-------+
                              |
                              v
                    +-------------------+
                    | Catalogue Store   |
                    | 5,000+ products   |
                    | images            |
                    | product IDs       |
                    | metadata          |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | Image             |
                    | Preprocessing     |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | Pretrained Vision |
                    | Encoder           |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | Catalogue         |
                    | Embeddings        |
                    | Normalized        |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | FAISS Vector      |
                    | Index             |
                    +-------------------+


RUNTIME QUERY:

                     USER QUERY PHOTO
                              |
                              v
                    +-------------------+
                    | Image             |
                    | Preprocessing     |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | Vision Encoder    |
                    | SAME MODEL        |
                    +---------+---------+
                              |
                              v
                         Query Vector
                              |
                              v
                    +-------------------+
                    | Similarity Search |
                    | FAISS             |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | Ranking + Top-K   |
                    | Candidates        |
                    +---------+---------+
                              |
                              v
                       Score >= τ ?
                         /       \
                       YES       NO
                        |         |
                        v         v
               MATCH              UNKNOWN
               Top-5 +            Reject item
               scores


                     APPLICATION INTERFACE

                         FastAPI
                       /match endpoint
                              |
                              v
                         JSON response


IMPORTANT:
The catalogue-building pipeline and runtime query pipeline must use the
same compatible preprocessing and the same vision encoder.

The FAISS index is built offline from catalogue embeddings.

The query does NOT rebuild the catalogue index.


------------------------------------------------------------
PART B — STUMPER & EVALUATION SYSTEM
------------------------------------------------------------

                    100+ HARD PHOTOS
                   SELF-CAPTURED
                           |
                           v
       +-------------------------------------------+
       | Failure Conditions                         |
       |                                           |
       | Lighting                                  |
       | Angle                                     |
       | Occlusion                                 |
       | Clutter                                   |
       | Blur                                      |
       | Reflection                                |
       | Hand/Wrist                                |
       +--------------------+----------------------+
                            |
                            v
                 Ground Truth Labels
                 product_id + condition
                            |
                            v
                 +----------------------+
                 | Evaluation Harness   |
                 +----------+-----------+
                            |
                            | calls SAME
                            | Part A pipeline
                            v
                 +----------------------+
                 | Part A Matcher       |
                 | SAME production path |
                 +----------+-----------+
                            |
                            v
                 Predicted Product /
                 Unknown Decision
                            |
                            v
                    Compare with
                    Ground Truth
                            |
                            v
                 +----------------------+
                 | Metrics              |
                 |                      |
                 | Top-1 Accuracy       |
                 | Top-5 Accuracy       |
                 | Per-condition       |
                 | Accuracy             |
                 | Latency              |
                 | Unknown-item metrics |
                 | FAR / FRR            |
                 +----------+-----------+
                            |
                            v
                 Failure / Error Analysis
                 grouped by condition
                            |
                            v
                  Hypothesis
                            |
                            v
                     Experiment
                            |
                            v
                    Re-evaluate
                            |
                            v
             FEEDBACK TO PART A
             Improve:
             - model
             - preprocessing
             - retrieval
             - threshold
                            |
                            +-------> Re-run evaluation


# 5. PART A — DATA COLLECTION

Create a public-source jewellery catalogue.

Minimum:
5,000+ catalogue images.

Each catalogue item should have stable metadata.

Recommended catalogue schema:

product_id
product_name
category
image_path
source_url
additional_metadata

Example:

{
    "product_id": "JW_001234",
    "product_name": "Gold Ring",
    "category": "ring",
    "image_path": "catalogue/JW_001234.jpg",
    "source_url": "...",
    "metadata": {...}
}

Important:
The product_id is the ground-truth identity used throughout the system.

The catalogue should be cleaned before embedding generation.

Potential cleaning steps:
- remove broken images
- remove unusable images
- remove duplicates where possible
- validate metadata
- ensure every image has a product_id
- ensure product IDs are unique
- maintain a reproducible catalogue manifest


# 6. PART A — IMAGE PREPROCESSING

Catalogue images:

Raw image
  ↓
Validation
  ↓
Resize / normalize according to encoder requirements
  ↓
Vision encoder

Query images:

User image
  ↓
Validation
  ↓
Same compatible preprocessing
  ↓
Same vision encoder

The preprocessing pipeline should be centralized so that catalogue and query preprocessing do not accidentally diverge.

Preprocessing choices should be documented because they may become an experimental variable later.


# 7. PART A — VISION ENCODER

Use a pretrained vision embedding model.

The initial implementation should avoid training a model from scratch.

The encoder converts:

Image
  ↓
Dense numerical vector

Example concept:

image
→ pretrained vision encoder
→ embedding vector
→ normalization

The exact model should be selected experimentally and recorded in DECISIONS.md / experiment notes.

Important properties:
- same model for catalogue and query
- deterministic/reproducible inference where practical
- embeddings should be normalized if using cosine similarity through normalized vectors


# 8. PART A — CATALOGUE EMBEDDING PIPELINE

This is an OFFLINE process.

For every catalogue image:

for image in catalogue:
    processed = preprocess(image)
    embedding = encoder(processed)
    embedding = normalize(embedding)
    store embedding with product_id

Result:

product_id → embedding

Example:

JW_001 → vector
JW_002 → vector
JW_003 → vector
...
JW_5000 → vector


# 9. PART A — FAISS INDEX

Build a FAISS vector index over the normalized catalogue embeddings.

Concept:

Catalogue embeddings
        ↓
FAISS index

Runtime:

Query embedding
        ↓
FAISS similarity search
        ↓
Nearest catalogue vectors


The index should store enough information to map vector positions back to product IDs.

Conceptually:

FAISS vector position
        ↓
catalogue metadata
        ↓
product_id


The initial implementation should prioritize correctness and measurable performance.

If later scaling experiments are performed, index type and search parameters can become experimental variables.


# 10. PART A — QUERY MATCHING PIPELINE

Runtime flow:

User uploads image
        ↓
Validate image
        ↓
Preprocess image
        ↓
Vision encoder
        ↓
Query embedding
        ↓
Normalize
        ↓
FAISS similarity search
        ↓
Top-K candidates
        ↓
Ranking
        ↓
Threshold decision
        ↓
Match or Unknown
        ↓
Top-5 JSON response


The matcher should be implemented as a reusable internal service/function.

The FastAPI endpoint should call the matcher rather than duplicating retrieval logic.


# 11. TOP-K RETRIEVAL

FAISS should retrieve at least the number of candidates required to produce the final Top-5.

The matcher should return:

product_id
product_name
similarity score
rank

Example:

{
    "rank": 1,
    "product_id": "JW_10231",
    "product_name": "Gold Diamond Ring",
    "score": 0.92
}

The response should contain up to five candidates.


# 12. MATCH / UNKNOWN DECISION

Nearest-neighbour search always returns something.

Therefore the system must not automatically assume:

nearest item = correct item.

Use a threshold τ.

Concept:

best_similarity >= τ
        ↓
      MATCH

best_similarity < τ
        ↓
     UNKNOWN


The threshold should NOT simply be guessed.

It should be selected/validated using appropriate labelled data.

The unknown-item extension should use objects that genuinely do not exist in the catalogue.

The threshold becomes an important experiment.


# 13. FASTAPI APPLICATION

Expose the matcher through an API.

Primary endpoint:

POST /match

Input:
- image

Processing:
- validate image
- preprocess
- encode
- search
- rank
- threshold
- return result

Output should contain:
- match status
- Top-5 candidates
- product IDs
- product names/metadata
- similarity scores

Example:

{
    "status": "match",
    "results": [
        {
            "rank": 1,
            "product_id": "JW_10231",
            "score": 0.92
        },
        {
            "rank": 2,
            "product_id": "JW_08321",
            "score": 0.88
        }
    ]
}

Unknown:

{
    "status": "unknown",
    "results": []
}

The exact response structure can evolve during implementation.


# 14. PART B — STUMPER DATASET

Create at least 100 hard images personally using a phone.

These images must correspond to real catalogue products.

The purpose is to create a realistic distribution shift between catalogue/reference images and user photographs.

Each image must have:

image_id
product_id
failure_condition
capture information/notes where useful

Example:

image_id: ST_001
product_id: JW_10231
condition: bad_lighting

image_id: ST_002
product_id: JW_08122
condition: occlusion


# 15. STUMPER FAILURE CONDITIONS

Required/important difficult conditions:

1. Bad/difficult lighting
2. Odd/unusual angle
3. Partial occlusion
4. Cluttered background
5. Motion blur
6. Reflections
7. Hand/wrist in frame

The dataset should contain enough examples per condition to make comparisons meaningful.

Avoid creating a dataset where almost every condition has only one or two examples.


# 16. STUMPER DATA ORGANIZATION

Recommended:

evaluation/
    stumper.csv
    images/
        ST_001.jpg
        ST_002.jpg
        ...
    results.csv
    metrics.json
    analysis.md

stumper.csv:

image_id,product_id,condition,image_path

Example:

ST_001,JW_10231,bad_lighting,images/ST_001.jpg
ST_002,JW_08122,occlusion,images/ST_002.jpg
ST_003,JW_01982,reflection,images/ST_003.jpg


# 17. CRITICAL EVALUATION RULE

The evaluation harness MUST call the SAME Part A matcher used by the actual API.

Do NOT create a separate "evaluation-only" retrieval implementation.

Correct:

Stumper image
    ↓
same preprocessing
    ↓
same encoder
    ↓
same FAISS index
    ↓
same ranking
    ↓
same threshold
    ↓
prediction


This ensures that evaluation measures the actual system.


# 18. EVALUATION METRICS

## Top-1 Accuracy

Correct product is ranked first.

Top-1 accuracy:

correct_top1 / total_queries


## Top-5 Accuracy

Correct product appears anywhere in Top-5.

Top-5 accuracy:

correct_top5 / total_queries


## Per-Condition Accuracy

Calculate performance separately for:

bad_lighting
odd_angle
occlusion
clutter
motion_blur
reflection
hand_wrist

Example output:

condition        samples    top1    top5
------------------------------------------------
normal             20       XX%     XX%
bad_lighting       15       XX%     XX%
odd_angle          15       XX%     XX%
occlusion          15       XX%     XX%
clutter            15       XX%     XX%
motion_blur        15       XX%     XX%
reflection         15       XX%     XX%
hand_wrist         15       XX%     XX%


# 19. LATENCY

Measure end-to-end single-query latency.

At minimum track:

preprocessing
+
embedding
+
FAISS search
+
decision
=
total lookup latency

Preferably record each component separately.

Example:

preprocess: 10 ms
embedding: 80 ms
FAISS: 5 ms
decision: <1 ms
total: ~95 ms

Actual values must come from measurement, not assumptions.

Also distinguish:
- model warm-up time
- one-time index loading
- actual per-query inference time

The final reported methodology should explain what is included in latency.


# 20. UNKNOWN-ITEM EVALUATION

Optional but important extension.

Collect approximately 20 jewellery items that are NOT present in the catalogue.

For each unknown query:

query
  ↓
Part A matcher
  ↓
best similarity
  ↓
threshold
  ↓
unknown / false accept


Metrics:

False Accept Rate (FAR):
unknown items incorrectly accepted as catalogue items.

False Reject Rate (FRR):
known catalogue items incorrectly rejected as unknown.

The threshold should be evaluated using both:
- known catalogue items
- unknown items


# 21. ERROR ANALYSIS

Do not stop at accuracy.

For every incorrect prediction, preserve enough information to inspect:

query image
ground-truth product
predicted product
rank
similarity score
failure condition


Example:

Ground truth:
JW_10231

Prediction:
JW_10482

Condition:
reflection

Similarity:
0.87

Then inspect why the error happened.


# 22. FAILURE ANALYSIS PROCESS

Use:

Evaluation
    ↓
Incorrect predictions
    ↓
Group by condition
    ↓
Inspect examples
    ↓
Find recurring patterns
    ↓
Create hypothesis
    ↓
Design experiment
    ↓
Run experiment
    ↓
Re-evaluate
    ↓
Accept/reject based on evidence


Example:

Observation:
Reflection images produce many incorrect matches.

Hypothesis:
The visual embedding is sensitive to strong reflections and loses
fine-grained jewellery structure.

Experiment:
Test a preprocessing/model/retrieval change.

Measure:
Reflection Top-1 and Top-5 before vs after.

Decision:
Keep the change only if the evidence supports it without causing
unacceptable regression elsewhere.


# 23. EXPERIMENTATION PRINCIPLE

Do not randomly add techniques.

Every improvement should follow:

BASELINE
    ↓
OBSERVATION
    ↓
HYPOTHESIS
    ↓
CHANGE ONE IMPORTANT VARIABLE
    ↓
MEASURE
    ↓
COMPARE
    ↓
DECISION


Examples of variables that may be investigated:

- vision encoder
- image preprocessing
- image resizing/cropping
- embedding normalization
- similarity metric
- FAISS index configuration
- retrieval K
- threshold τ
- unknown-item strategy

Only implement experiments that are justified by observed problems.


# 24. BASELINE FIRST

The first working version should be intentionally simple:

Catalogue
    ↓
Preprocess
    ↓
Pretrained vision encoder
    ↓
Normalized embeddings
    ↓
FAISS
    ↓
Query encoder
    ↓
Top-5 retrieval
    ↓
Basic threshold


Then measure it.

Do not optimize before having a baseline.


# 25. IMPROVEMENT LOOP

After baseline:

Baseline results
      ↓
Find largest weakness
      ↓
Choose ONE important problem
      ↓
Experiment
      ↓
Compare with baseline
      ↓
Keep/reject
      ↓
Final evaluation


The project should be able to explain:

"What did the baseline do?"

"What failed?"

"Why did we think it failed?"

"What did we change?"

"Did the change actually help?"

"What trade-off did the change introduce?"


# 26. OPTIONAL SCALABILITY EXTENSION

If time permits, investigate growing from:

5,000 products
      ↓
100,000 products

while measuring lookup performance on an ordinary CPU/no GPU.

This should be treated as an experiment rather than assumed to be solved.

Possible variables:
- FAISS index type
- exact vs approximate search
- index parameters
- memory usage
- query latency

If this extension is not completed, do not claim it is solved.


# 27. OPTIONAL INCREMENTAL CATALOGUE EXTENSION

Another optional challenge is adding 1,000 new catalogue items without recomputing existing embeddings.

Desired concept:

Existing catalogue
      ↓
Existing embeddings/index
      +
New 1,000 images
      ↓
Generate only new embeddings
      ↓
Add new vectors to index


The goal is to avoid recomputing the entire catalogue.

This is optional and should only be implemented if the core system is already reliable.


# 28. OPTIONAL MULTI-ITEM IMAGE EXTENSION

Another possible extension:

One photograph
    ↓
Multiple jewellery items
    ↓
Detect/identify each item
    ↓
Return match for each


This should not be prioritized over the core single-item retrieval system unless the core requirements are already stable.


# 29. OPTIONAL PROGRAMMATIC STUMPER

Another optional challenge is to generate difficult examples programmatically.

Potential transformations:
- lighting changes
- rotation
- blur
- background clutter
- occlusion
- reflection-like effects

Compare:

hand-shot difficult images
vs
programmatically generated difficult images

Question:

Do synthetic/programmatic transformations create failures at a higher rate than the manually captured stumper set?

This is optional.


# 30. RECOMMENDED PROJECT STRUCTURE

stump-the-model/

├── app/
│   ├── main.py
│   ├── api/
│   │   └── routes.py
│   ├── retrieval/
│   │   ├── encoder.py
│   │   ├── index.py
│   │   ├── matcher.py
│   │   └── ranking.py
│   ├── preprocessing/
│   │   └── image.py
│   └── config.py
│
├── data/
│   ├── catalogue/
│   ├── catalogue.csv
│   └── README.md
│
├── scripts/
│   ├── scrape.py
│   ├── clean_catalogue.py
│   ├── generate_embeddings.py
│   ├── build_index.py
│   └── evaluate.py
│
├── evaluation/
│   ├── stumper.csv
│   ├── images/
│   ├── results.csv
│   ├── metrics.json
│   └── analysis.md
│
├── experiments/
│   ├── baseline.md
│   ├── experiment_01.md
│   ├── experiment_02.md
│   └── final_results.md
│
├── tests/
│   ├── test_preprocessing.py
│   ├── test_encoder.py
│   ├── test_retrieval.py
│   └── test_api.py
│
├── logs/
│   └── AI coding session logs
│
├── artifacts/
│   ├── embeddings/
│   └── indexes/
│
├── README.md
├── DECISIONS.md
├── requirements.txt
├── Dockerfile
└── .env.example


# 31. COMPONENT RESPONSIBILITIES

## scraper.py

Responsible for:
- collecting public catalogue data
- downloading images
- extracting metadata
- creating catalogue manifest


## clean_catalogue.py

Responsible for:
- validating images
- removing invalid records
- detecting/removing duplicates where possible
- producing clean catalogue


## encoder.py

Responsible for:
- loading pretrained vision model
- preprocessing
- generating embeddings
- normalization


## generate_embeddings.py

Responsible for:
- processing catalogue images
- generating embeddings
- persisting embeddings


## index.py

Responsible for:
- loading/building FAISS index
- adding vectors
- searching vectors


## matcher.py

Responsible for:
- query image processing
- embedding generation
- FAISS retrieval
- ranking
- threshold decision
- returning structured match result


## routes.py

Responsible for:
- HTTP interface
- receiving image
- calling matcher
- returning JSON
- request/error validation


## evaluate.py

Responsible for:
- loading stumper dataset
- invoking the SAME matcher
- collecting predictions
- computing metrics
- recording latency
- writing results


# 32. DATA FLOW

OFFLINE:

Public source
    ↓
Scraper
    ↓
Raw catalogue
    ↓
Cleaning
    ↓
Clean catalogue
    ↓
Preprocessing
    ↓
Vision encoder
    ↓
Normalized embeddings
    ↓
FAISS index


ONLINE:

User image
    ↓
FastAPI
    ↓
Preprocessing
    ↓
Same vision encoder
    ↓
Query embedding
    ↓
FAISS
    ↓
Top-K
    ↓
Ranking
    ↓
Threshold
    ↓
MATCH / UNKNOWN
    ↓
JSON response


EVALUATION:

Stumper image
    ↓
Evaluation harness
    ↓
SAME matcher
    ↓
Prediction
    ↓
Ground truth comparison
    ↓
Metrics
    ↓
Error analysis
    ↓
Experiment
    ↓
Improvement
    ↓
Re-evaluation


# 33. IMPORTANT DESIGN DECISIONS

1. Retrieval instead of fixed classification.

Reason:
The catalogue is a set of individual products and may grow over time.
Embedding-based retrieval allows new products to be represented as vectors
without retraining a 5,000-class classifier.

2. Pretrained vision encoder for baseline.

Reason:
The assignment focuses on retrieval behaviour and real-world robustness.
A pretrained encoder provides a strong baseline without spending the
entire project on training a model from scratch.

3. FAISS for vector search.

Reason:
The task is fundamentally nearest-neighbour retrieval and FAISS provides
a direct vector-search implementation.

4. Same matcher for API and evaluation.

Reason:
Evaluation must represent actual production behaviour.

5. Threshold-based unknown detection.

Reason:
Nearest-neighbour systems always return a nearest item. A threshold is
required to reject sufficiently dissimilar inputs.

6. Experiment before optimization.

Reason:
The assignment values measured reasoning and failure analysis rather than
adding techniques without evidence.


# 34. TESTING STRATEGY

Unit tests should cover:

- invalid image handling
- preprocessing output
- embedding shape
- embedding normalization
- index loading
- retrieval output format
- ranking order
- threshold behaviour
- unknown decision
- API response
- missing/corrupt files


Integration tests should verify:

query image
    ↓
preprocessing
    ↓
encoder
    ↓
FAISS
    ↓
matcher
    ↓
API response


Evaluation tests should verify:

- ground truth product exists
- stumper labels are valid
- evaluation invokes the same matcher
- Top-1 calculation
- Top-5 calculation
- condition grouping
- latency recording
- unknown metrics


# 35. REPRODUCIBILITY

The project should be reproducible.

Document:
- Python version
- dependencies
- model name/version
- embedding dimension
- preprocessing configuration
- FAISS configuration
- threshold
- dataset creation process
- random seeds where relevant
- evaluation methodology


# 36. PERFORMANCE MEASUREMENT

At minimum report:

Catalogue size
Embedding dimension
Index type
Model
Top-1 accuracy
Top-5 accuracy
Per-condition accuracy
Average latency
Relevant latency distribution if possible
Unknown-item FAR/FRR if implemented


Avoid reporting unsupported performance claims.

All final numbers must come from actual experiments.


# 37. DOCUMENTATION

README.md should explain:

1. Problem
2. Architecture
3. Setup
4. Dataset preparation
5. Model
6. Building embeddings
7. Building FAISS index
8. Starting API
9. Running a match
10. Running evaluation
11. Results
12. Limitations
13. Future work


DECISIONS.md should contain:

- architecture decisions
- rejected alternatives
- trade-offs
- testing decisions
- breakages
- lessons learned
- next steps


Experiment documentation should contain:

Experiment
Hypothesis
Method
Dataset
Metric
Baseline
Result
Interpretation
Decision


# 38. AI SESSION LOGGING

Every AI coding session must be logged under:

logs/

The logs should preserve the relevant development conversation/transcript.

The project should clearly show where AI suggestions were accepted,
modified, or rejected.

Important:
AI is a development assistant, not the decision-maker.

The implementation should document cases where an AI-generated approach
was changed because of technical evidence, project constraints, or testing.


# 39. CURRENT IMPLEMENTATION STATUS

CURRENTLY COMPLETED:

[x] Assignment reviewed
[x] PS2 selected
[x] Jewellery selected as target category
[x] Problem statement defined
[x] Part A architecture defined
[x] Part B architecture defined
[x] Retrieval architecture defined
[x] Evaluation architecture defined
[x] Unknown-item concept defined
[x] Feedback loop defined
[x] Repository architecture planned
[x] Evaluation metrics defined
[x] Main components identified


CURRENT PHASE:

PHASE 0 — ARCHITECTURE / PLANNING


NEXT:

1. Select public jewellery source.
2. Verify that at least 5,000 usable images/products can be collected.
3. Define catalogue schema.
4. Implement scraper.
5. Build and clean catalogue.
6. Select initial pretrained vision encoder.
7. Generate catalogue embeddings.
8. Build FAISS index.
9. Implement baseline matcher.
10. Implement /match API.
11. Create clean baseline evaluation.
12. Capture 100+ hard stumper images.
13. Run stumper evaluation.
14. Analyze failure conditions.
15. Select one major weakness.
16. Run an improvement experiment.
17. Re-evaluate.
18. Implement unknown-item detection if time permits.
19. Final benchmark.
20. Documentation and clean-machine validation.


# 40. IMPLEMENTATION PRIORITY

Priority 1 — MUST HAVE

- 5,000+ jewellery catalogue
- catalogue metadata
- preprocessing
- pretrained vision encoder
- catalogue embeddings
- FAISS index
- query matching
- Top-5 results
- similarity scores
- FastAPI /match
- 100+ hard images
- ground truth labels
- evaluation harness
- Top-1
- Top-5
- per-condition analysis
- latency measurement
- failure analysis
- README
- DECISIONS.md
- AI logs


Priority 2 — STRONGLY CONSIDER

- unknown-item/no-match detection
- FAR/FRR measurement
- threshold calibration
- detailed latency breakdown
- experiment comparing improvement against baseline


Priority 3 — ONLY IF CORE IS STABLE

- 100k catalogue scaling
- incremental catalogue updates
- multi-item images
- programmatic stumper generation


# 41. DEVELOPMENT STRATEGY

Do NOT start with every feature.

Implement vertically:

STEP 1:
One small catalogue subset
    ↓
Encoder
    ↓
Embedding
    ↓
FAISS
    ↓
Query
    ↓
Top-5


STEP 2:
Scale to full 5,000+ catalogue.


STEP 3:
Expose through FastAPI.


STEP 4:
Build baseline evaluation.


STEP 5:
Create 100+ stumper dataset.


STEP 6:
Measure failure conditions.


STEP 7:
Improve the biggest weakness.


STEP 8:
Add unknown detection.


STEP 9:
Run final evaluation.


# 42. SUCCESS CRITERIA

The project is successful when:

1. A clean machine can reproduce the system using the README.
2. The catalogue contains at least 5,000 jewellery images/products.
3. A query photograph can be matched against the catalogue.
4. The system returns Top-5 candidates and scores.
5. The system has a measurable latency.
6. The 100+ stumper dataset exists with ground-truth labels.
7. The evaluation harness runs the exact same matcher used by the API.
8. Performance is reported by failure condition.
9. Failure cases are inspected and explained.
10. At least one meaningful improvement is tested against the baseline.
11. Unknown/no-match behaviour is implemented if selected as the advanced challenge.
12. The final report clearly distinguishes measured results from assumptions.


# 43. CORE PROJECT PHILOSOPHY

This project is not:

"Build an image search API."

It is:

"Build an image retrieval system, deliberately attack it with difficult
real-world jewellery photographs, measure where it fails, understand why,
and use evidence to improve it."

The complete loop is:

                BUILD
                  ↓
              BASELINE
                  ↓
                ATTACK
                  ↓
               MEASURE
                  ↓
               ANALYZE
                  ↓
              HYPOTHESIS
                  ↓
              EXPERIMENT
                  ↓
              IMPROVEMENT
                  ↓
            RE-MEASURE
                  ↓
              DOCUMENT
                  ↓
             FINAL SYSTEM


# 44. MASTER ARCHITECTURE SUMMARY

PART A:

Public Jewellery Source
    ↓
Web Scraper
    ↓
5,000+ Catalogue
    ↓
Preprocessing
    ↓
Pretrained Vision Encoder
    ↓
Normalized Catalogue Embeddings
    ↓
FAISS Vector Index

User Photo
    ↓
Preprocessing
    ↓
Same Vision Encoder
    ↓
Query Vector
    ↓
FAISS Similarity Search
    ↓
Ranking
    ↓
Top-K
    ↓
Threshold τ
    ├── MATCH → Top-5 + scores
    └── UNKNOWN → reject

FastAPI /match
    ↓
JSON response


PART B:

100+ Self-Captured Hard Jewellery Photos
    ↓
Failure-condition labels
    ↓
Ground-truth product IDs
    ↓
Evaluation Harness
    ↓
SAME Part A Matcher
    ↓
Predictions
    ↓
Metrics
    ├── Top-1
    ├── Top-5
    ├── Per-condition accuracy
    ├── Latency
    └── FAR/FRR for unknown items
    ↓
Failure/Error Analysis
    ↓
Hypothesis
    ↓
Experiment
    ↓
Re-evaluate
    ↓
Improve Part A
    ↓
Repeat


FINAL PRINCIPLE:

Part A is the system being built.
Part B is the system used to challenge, measure, and improve Part A.

The evaluation system must never create a separate retrieval path.
It must invoke the same production matcher so that the reported results
represent the actual system.