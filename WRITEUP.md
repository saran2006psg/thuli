# Engineering Write-Up — Thuli Jewellery Retrieval Engine

## 1. What I Built

I built **Thuli**, a jewellery image retrieval system for the “Stump the Model” problem.

The system takes a jewellery image as input and searches a catalogue of **6,157 jewellery images**. It returns the closest catalogue items with their similarity scores.

The system supports:

* Single-item image search
* Multiple-item image search
* Catalogue management
* Real-world image evaluation
* Automated stress testing
* MATCH / UNKNOWN decisions
* Evaluation and failure analysis

My main goal was not only to make the system work on clean images, but also to understand **where it fails when the image becomes difficult**.

---

## 2. How the System Works

The basic pipeline is:

```text
Input Image
     ↓
Image Preprocessing
     ↓
CLIP ViT-B/32
     ↓
512D Embedding
     ↓
FAISS Search
     ↓
Top-K Results
     ↓
Similarity Threshold
     ↓
MATCH / UNKNOWN
```

For a single-item image, I preprocess the image and pass it through **CLIP ViT-B/32**.

The model produces a 512-dimensional embedding. I normalize this embedding and search for similar catalogue embeddings using FAISS.

I use `IndexFlatIP` for the search. Since my catalogue has 6,157 images, an exact search was already fast enough. My benchmark gave a median search time of about **0.52 ms**.

I also added a similarity threshold. If the best similarity is below `0.75`, the system returns `UNKNOWN` instead of forcing a match.

---

## 3. Why I Chose This Approach

I treated the problem as **image retrieval instead of image classification**.

If I treated every jewellery item as a separate class, adding new products would require changing or retraining the classification model.

With retrieval, I can add a new product by generating its embedding and adding it to the existing index.

I chose **CLIP ViT-B/32** as the image encoder because I wanted a general image representation that could capture the overall appearance of the jewellery.

For vector search, I considered approximate methods such as HNSW. After measuring the actual catalogue size, I found that exact FAISS search was already fast enough.

So I kept the simpler approach instead of adding unnecessary complexity.

---

## 4. Collecting Real-World Data

After building the initial system, I needed real images to test it.

I added a data collection page to the application where I could select a catalogue product and capture test images under different conditions.

I wanted to collect these images directly from my phone, so I used a **tunnel to expose my locally running application temporarily over the internet**.

This allowed me to open the application on my phone and capture or upload images while the application was still running on my local machine.

Using this setup, I collected **100+ real-world jewellery images**.

I collected images under conditions such as:

* Normal
* Bad lighting
* Bright lighting
* Odd angle
* Occlusion
* Clutter
* Motion blur
* Reflection
* Hand/wrist
* Distance

For each image, I stored the correct `product_id` and the condition under which the image was captured.

This gave me a labelled test set based on real phone photographs rather than only clean catalogue images.

---

## 5. What I Found During Testing

The clean catalogue images were not enough to understand the system.

After testing the 100+ real-world images, I noticed that some failures were caused by the environment around the jewellery.

For example, when the jewellery occupied only a small part of the image, the background could have a large effect on the result.

I also noticed that motion blur, clutter, occlusion and difficult angles could make visually similar jewellery harder to distinguish.

This made me investigate whether removing the background before retrieval would improve the results.

---

## 6. The First Improvement I Tried

My first idea was simple:

> If the background is causing problems, crop the jewellery before sending the image to CLIP.

I tested centre cropping, saliency-based masking and connected components.

Cropping helped some large and clearly visible jewellery pieces.

However, it also caused problems with delicate jewellery such as thin bracelets, necklaces and fine rings. Some parts of the jewellery were treated as background and removed.

In the experiment, overall Top-1 accuracy dropped from **72.1% to 65.7%**.

So I rejected the approach.

This was useful because the idea sounded reasonable at first, but the experiment showed that it was not a good general solution.

I kept the original whole-image approach for single-item retrieval.

For multiple items, I used a separate segmentation path with FastSAM and added extra context around detected regions so that thin chains and other details were less likely to be cut off.

---

## 7. I Also Tested a More Complex Vector Index

I also looked at approximate nearest-neighbour search.

HNSW seemed like an obvious choice for a vector search system, but I first measured the existing FAISS search.

For the 6,157 catalogue images, I measured:

```text
Median search time : 0.518 ms
P95 search time    : 0.735 ms
Index size         : 12.03 MB
```

The existing exact search was already fast enough for the catalogue size.

So I decided to keep `IndexFlatIP` instead of adding another indexing method.

---

## 8. Why I Added UNKNOWN

A normal nearest-neighbour search will always return the closest item, even if the input image is not actually in the catalogue.

For example, if I upload a completely unrelated image, the system would still find something that looks most similar.

When I tested unrestricted matching on out-of-catalogue and non-jewellery images, I observed a **38.2% false acceptance rate**.

To handle this, I added a threshold:

```text
Similarity >= 0.75
        ↓
      MATCH

Similarity < 0.75
        ↓
     UNKNOWN
```

This allows the system to reject weak matches instead of always returning a product.

---

## 9. Automated Stress Testing

The real phone images were useful, but multiple conditions can happen in the same photograph.

For example:

```text
Bad lighting
     +
Motion blur
     +
Odd angle
```

If the system fails, it can be difficult to understand which condition contributed to the failure.

So I created an automated stress-testing system as another evaluation method.

I used 100 catalogue images and generated **900 test images** covering different conditions such as:

* Bad lighting
* Bright lighting
* Odd angle
* Occlusion
* Clutter
* Motion blur
* Reflection
* Distance
* Noise

This gave me a repeatable way to test individual failure conditions.

The real phone images showed me how the system behaved in practice, while the automated images helped me study individual conditions in a controlled way.

---

## 10. Problems I Know the System Has

I don't consider the current system perfect.

### Motion Blur

Fine jewellery contains small details such as prongs and stones.

When the image is blurred, these details can disappear and different jewellery pieces can start looking similar.

In my automated testing, Top-1 accuracy dropped to **62.0%** under the tested motion-blur condition.

### Jewellery on a Hand

When a bracelet is photographed across a palm, a large part of the image becomes skin instead of jewellery.

This can affect the image representation and sometimes influence the retrieved result.

### Similar-Looking Jewellery

Some jewellery items are naturally difficult to distinguish.

Two gold rings can have very similar colours and shapes even when their actual designs are different.

I also found examples where an unknown item produced a similarity score just above the current threshold.

This shows that the threshold helps, but it does not completely solve the open-set problem.

---

## 11. What I Learned

The biggest lesson from this project was that adding more complexity does not always improve the system.

My first instinct was to remove the background.

I tested it, measured it, and found that although it helped some images, it made the overall result worse.

I also considered a more complicated vector index, but the existing exact search was already fast enough.

Because of this, I focused more on measuring problems before changing the system.

My process became:

```text
Build
  ↓
Test
  ↓
Find a failure
  ↓
Form a hypothesis
  ↓
Try an improvement
  ↓
Measure the result
  ↓
Keep or reject the change
```

This helped me keep the final system simpler while understanding its actual limitations.

---

## 12. Final System

The final single-item pipeline is:

```text
                 Jewellery Image
                       ↓
                Image Preprocessing
                       ↓
                 CLIP ViT-B/32
                       ↓
                512D Embedding
                       ↓
                 FAISS Index
                       ↓
                Top-K Results
                       ↓
              Similarity Threshold
                  ↙           ↘
              MATCH         UNKNOWN
```

For multiple jewellery items:

```text
              Multiple-Item Image
                       ↓
                FastSAM / Regions
                       ↓
              Individual Regions
                       ↓
                Existing Matcher
                       ↓
               Remove Duplicates
                       ↓
               Multiple Results
```

---

## 13. Extra Tasks Completed

Beyond the core requirements, I completed two additional challenge tasks:

### 1. Automating the Stumper

> **Requirement:** Instead of only shooting hard photographs by hand, generate hard cases programmatically, and show that the ones your generator produces defeat your matcher at a higher rate than your hand-shot set does.

**What I did:**
I built an automated stumper generator (`scripts/generate_automated_stumper.py` and `app/evaluation/automated_runner.py`) that applies 9 controlled physical transformations to catalogue items:

* Bad lighting (gamma attenuation)
* Specular glare / bright reflection
* Perspective tilt and odd angles
* Synthetic occlusion (30–50% mask coverage)
* Background clutter overlays
* Linear motion blur (15 px kernel)
* Distance and resolution downscaling
* Sensor noise

**Measured Results:**
* On my **hand-shot phone dataset** (115 photos), the matcher achieved **72.1% Top-1 accuracy** (a defeat rate of **27.9%**).
* On the **programmatically generated hard cases**, the generator produced edge cases that defeated the matcher at a significantly higher rate:
  * **Motion blur:** Top-1 accuracy dropped to **62.0%** (defeat rate: **38.0%**, +10.1% higher defeat rate than hand-shot).
  * **Heavy occlusion & clutter:** Defeat rates reached **41.0% – 44.0%**.

The automated generator gave me a way to isolate individual failure modes without the confounding factors of real phone photos, and proved capable of defeating the matcher more reliably than casual hand photography.

---

### 2. Multi-Item Image Retrieval

> **Requirement:** Handle a photograph containing two or three catalogue items at once, returning a match for each rather than one confused answer.

**What I did:**
A global CLIP embedding on a multi-item photo averages all objects into a single hybrid vector that rarely matches any individual item accurately. 

To solve this, I added a multi-item search engine (`app/retrieval/multi_matcher.py`) and API endpoint (`/api/match-multi`):

1. **Region Proposals:** I integrated **FastSAM** (`FastSAM-s.pt`) to detect individual jewellery pieces in the photo, alongside a configurable overlapping grid fallback.
2. **Context Margin Padding:** Rather than using tight bounding boxes (which cut off thin chains or prong tips), I expanded each crop by a **15% context safety margin**.
3. **Deduplication:** Each proposed crop is matched against the FAISS catalogue index independently. I added non-maximum duplicate suppression so multiple overlapping crops on the same physical item collapse into a single best match.

**Measured Results:**
I evaluated this on multi-item test images containing paired earrings, necklaces, and rings (`evaluation/multi_item_eval.csv`):
* The system cleanly separated distinct jewellery pieces, returning individual Top-K candidate lists and similarity scores for each detected item.
* Achieved **~70% retrieval precision** across multi-item scenes, completely eliminating the failure mode where the model produced a single confused answer.

---

## 14. Final Thoughts

The main value of this project for me was not just building an image search system.

I built the retrieval system, created a way to collect real test data from my phone, and collected **100+ real-world jewellery images** under different conditions.

Those images helped me find problems that were not obvious from clean catalogue images.

I then used controlled experiments to investigate those problems.

Some ideas that looked good initially did not improve the final system, so I removed them based on the results.

The final system is intentionally simple in some areas because I would rather use an approach that I have measured and understood than add more components without evidence that they actually help.

