Viewed config.py:32-52
Listed directory embeddings
Listed directory indexes

Here is a detailed breakdown of how the database works, how embeddings are stored locally, and an architectural evaluation of whether this is a good approach.

---

### 1. 🗄️ How the System "Database" Works

Our system does not rely on a heavy external database (like PostgreSQL, MySQL, or MongoDB). Instead, it uses a **three-tier local architecture** designed for high throughput, zero network overhead, and instant vector retrieval:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        THULI DATA ARCHITECTURE                         │
└────────────────────────────────────────────────────────────────────────┘

 1. Tabular Metadata Layer        2. Vector Index Layer         3. File Asset Layer
 ┌───────────────────────┐      ┌─────────────────────────┐   ┌───────────────────────┐
 │   data/catalogue.csv  │      │ artifacts/indexes/      │   │ data/catalogue/       │
 │   (6,190 items)       │      │   catalogue.faiss       │   │   jewelry_dataset/    │
 │                       │      │ (In-memory C++ index)   │   │                       │
 │ • product_id          │◄────►│                         │   │ • Raw JPEG/PNG image  │
 │ • category            │      │ artifacts/embeddings/   │   │   files on disk       │
 │ • product_name        │      │ • catalogue_embeddings  │   │                       │
 │ • image_path          │      │   .npy (512-d float32)  │   │                       │
 │ • dimensions          │      │ • product_ids.json      │   │                       │
 └───────────────────────┘      └─────────────────────────┘   └───────────────────────┘
```

1. **Tabular Metadata (`data/catalogue.csv`)**:
   - Holds item details (`product_id`, `category`, `subcategory`, `product_name`, `image_path`, `width`, `height`).
   - When the backend starts up, this CSV is loaded into a fast **in-memory Python dictionary** (`catalogue_lookup[product_id]`) for $O(1)$ constant-time metadata lookups.
2. **Raw Images (`data/catalogue/`)**:
   - High-resolution catalogue photos stored directly on disk and served as static assets.
3. **Vector Embeddings & Index (`artifacts/`)**:
   - Stores the mathematical neural representations of every jewellery item for visual search.

---

### 2. 🧠 How the Embeddings Are Stored Locally

#### A. Generation
- Every catalogue image is passed through the vision transformer `openai/clip-vit-base-patch32`.
- It outputs a **512-dimensional dense float vector** representing the visual style, shape, and gem arrangement.
- Each vector is **$L_2$-normalized** ($\|v\|_2 = 1.0$), which allows cosine similarity to be calculated using a fast dot product:
  $$\text{CosineSimilarity}(u, v) = u \cdot v$$

#### B. Storage Files on Disk
The embeddings live completely offline in the [artifacts/](file:///d:/PL/thuli/artifacts/) directory:

| File | Type & Size | Role |
| :--- | :--- | :--- |
| [catalogue_embeddings.npy](file:///d:/PL/thuli/artifacts/embeddings/catalogue_embeddings.npy) | NumPy Binary (`.npy`)<br>**~12.6 MB** | Raw float32 matrix of shape `(6190, 512)`. Memory-mappable directly by CPU/GPU. |
| [product_ids.json](file:///d:/PL/thuli/artifacts/embeddings/product_ids.json) | JSON List<br>**~99 KB** | Array mapping integer vector row index `0, 1, 2...` $\to$ catalogue SKU ID (`JW_000001`, `JW_000002`...). |
| [catalogue.faiss](file:///d:/PL/thuli/artifacts/indexes/catalogue.faiss) | Binary Index<br>**~12.6 MB** | Meta FAISS `IndexFlatIP` (Inner Product). Pre-built index loaded directly into RAM. |

#### C. How a Search Query Runs in Real-Time
1. **User drops a photo** $\to$ CLIP extracts a 512-d vector ($\sim 80\text{–}100\text{ ms}$).
2. **FAISS search** $\to$ Searches 6,190 vectors using SIMD AVX2 C++ instructions in **$1\text{–}3\text{ ms}$**.
3. **ID mapping** $\to$ Maps top-5 internal FAISS row IDs to catalogue `product_id`s in microseconds.
4. **Metadata match** $\to$ Pulls product name, category, and image URL from the in-memory lookup table.
5. **Threshold gate** $\to$ Compares `best_similarity >= 0.75` to decide `MATCH` or `UNKNOWN`.

---

### 3. ⚖️ Is This a Good Approach?

**Yes — for this scale (thousands to tens of thousands of items), it is an industry best-practice approach.**

#### ✅ Key Advantages:
1. **Extreme Speed ($1\text{–}3\text{ ms}$ search)**:
   - Because the FAISS index sits directly in process RAM, there are no TCP network roundtrips, no JSON serialization over sockets, and no database connection pooling delays.
2. **Zero Infrastructure Cost & Zero Maintenance**:
   - No Docker containers, no external daemon to maintain, and no expensive monthly cloud bills for managed vector databases (Pinecone, Weaviate, Milvus, Qdrant).
3. **100% Offline & Portable**:
   - The entire system can run completely air-gapped on a laptop without internet access. You can zip the repo and move it anywhere.
4. **Exact Mathematical Precision (`IndexFlatIP`)**:
   - Many large vector databases use approximate nearest neighbor graphs (HNSW) or quantization (IVF-PQ) that trade away recall accuracy for scale.
   - Our `FlatIP` index performs **exact brute-force cosine comparison**, guaranteeing that the true highest-similarity catalogue item is never missed.
5. **Tiny Footprint**:
   - 6,190 items at 512-d float32 takes only **~12.6 MB of RAM**. Even 50,000 items would only consume ~100 MB of RAM.

---

### 4. 🔮 When and What Would You Change in the Future?

While this approach is optimal today, here is when you should evolve it as your dataset expands:

| Scale | Recommended Storage Architecture | Why? |
| :--- | :--- | :--- |
| **Current (1K – 50K items)** | **Current Setup** (`catalogue.csv` + Local FAISS `IndexFlatIP`) | Optimal. Sub-millisecond latency, zero cost, exact accuracy. |
| **Medium (50K – 250K items)** | **SQLite + Local FAISS** | Replace CSV with SQLite to gain ACID transaction locks if multiple users write/upload items simultaneously. |
| **Large (500K – 10M+ items)** | **PostgreSQL + `pgvector` OR FAISS `IndexHNSW` / `IVFPQ`** | Flat brute-force search becomes CPU-heavy; vector quantization or graph indexing keeps search under 10ms. |

### Summary
The local FAISS + NumPy binary storage provides the fastest possible retrieval speed with zero operational complexity. For a jewellery visual retrieval engine of this size, it is a clean, robust, and cost-effective design.