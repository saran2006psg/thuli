/**
 * Thuli Jewellery Retrieval — Web Test Client
 * Handles Visual Search, Sample Testing, and Live Catalogue Ingestion.
 */

document.addEventListener("DOMContentLoaded", () => {
  // ── Global Stats & Tab Elements ──────────────────────────────────────────
  const statCatalogue = document.getElementById("stat-catalogue");
  const footerVectors = document.getElementById("footer-vectors");

  const tabButtons = document.querySelectorAll(".nav-tab");
  const tabViews = document.querySelectorAll(".tab-view");

  // Tab switching
  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-target");

      tabButtons.forEach((b) => b.classList.remove("active"));
      tabViews.forEach((v) => {
        v.classList.add("hidden");
        v.classList.remove("active");
      });

      btn.classList.add("active");
      const targetView = document.getElementById(targetId);
      if (targetView) {
        targetView.classList.remove("hidden");
        targetView.classList.add("active");
      }
    });
  });

  // Fetch initial live statistics
  async function refreshStats() {
    try {
      const res = await fetch("/api/stats");
      if (res.ok) {
        const data = await res.json();
        const formatted = `${data.total_items.toLocaleString()} Items`;
        if (statCatalogue) statCatalogue.textContent = formatted;
        if (footerVectors) footerVectors.textContent = `${data.total_items.toLocaleString()} items (512-d)`;
      }
    } catch (e) {
      console.warn("Could not fetch live stats:", e);
    }
  }
  refreshStats();

  // ── Tab 1: Visual Search Elements & Logic ────────────────────────────────
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const dropzonePrompt = document.getElementById("dropzone-prompt");
  const previewContainer = document.getElementById("preview-container");
  const imagePreview = document.getElementById("image-preview");
  const btnClearImage = document.getElementById("btn-clear-image");

  const sliderTopk = document.getElementById("slider-topk");
  const valTopk = document.getElementById("val-topk");
  const sliderThreshold = document.getElementById("slider-threshold");
  const valThreshold = document.getElementById("val-threshold");

  const btnSearch = document.getElementById("btn-search");
  const searchSpinner = document.getElementById("search-spinner");
  const btnText = btnSearch ? btnSearch.querySelector(".btn-text") : null;

  const sampleGrid = document.getElementById("sample-grid");
  const telemetryTag = document.getElementById("telemetry-tag");

  const decisionBanner = document.getElementById("decision-banner");
  const decisionBadge = document.getElementById("decision-badge");
  const metricBestSim = document.getElementById("metric-best-sim");
  const metricThreshold = document.getElementById("metric-threshold");
  const metricLatency = document.getElementById("metric-latency");

  const emptyState = document.getElementById("empty-state");
  const candidatesList = document.getElementById("candidates-list");

  let currentSearchFile = null;

  // Search Controls Sync
  if (sliderTopk && valTopk) {
    sliderTopk.addEventListener("input", (e) => {
      valTopk.textContent = e.target.value;
    });
  }

  if (sliderThreshold && valThreshold) {
    sliderThreshold.addEventListener("input", (e) => {
      valThreshold.textContent = parseFloat(e.target.value).toFixed(2);
    });
  }

  // Search Dropzone events
  if (dropzone && fileInput) {
    ["dragenter", "dragover"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropzone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
      });
    });

    dropzone.addEventListener("drop", (e) => {
      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        handleSearchFile(files[0]);
      }
    });

    fileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleSearchFile(e.target.files[0]);
      }
    });
  }

  function handleSearchFile(file) {
    if (!file.type.startsWith("image/")) {
      alert("Please upload a valid image file (JPEG, PNG, WebP).");
      return;
    }
    currentSearchFile = file;
    const reader = new FileReader();
    reader.onload = (event) => {
      imagePreview.src = event.target.result;
      dropzonePrompt.classList.add("hidden");
      previewContainer.classList.remove("hidden");
      btnSearch.disabled = false;
    };
    reader.readAsDataURL(file);
  }

  if (btnClearImage) {
    btnClearImage.addEventListener("click", (e) => {
      e.stopPropagation();
      currentSearchFile = null;
      fileInput.value = "";
      imagePreview.src = "";
      previewContainer.classList.add("hidden");
      dropzonePrompt.classList.remove("hidden");
      btnSearch.disabled = true;
      resetResults();
    });
  }

  // Load Catalogue Samples
  async function loadSamples() {
    if (!sampleGrid) return;
    try {
      const res = await fetch("/api/samples");
      if (!res.ok) throw new Error("Failed to load samples");
      const samples = await res.json();

      sampleGrid.innerHTML = "";
      samples.forEach((sample) => {
        const card = document.createElement("div");
        card.className = "sample-card";
        card.innerHTML = `
          <img src="${sample.image_path}" alt="${sample.product_name}" loading="lazy">
          <span class="sample-card-label">${sample.category}</span>
        `;
        card.addEventListener("click", async () => {
          try {
            const imgRes = await fetch(sample.image_path);
            const blob = await imgRes.blob();
            const file = new File([blob], `${sample.product_id}.jpg`, { type: "image/jpeg" });
            handleSearchFile(file);
            executeSearch();
          } catch (err) {
            console.error("Error loading sample:", err);
          }
        });
        sampleGrid.appendChild(card);
      });
    } catch (err) {
      sampleGrid.innerHTML = `<div class="sample-loading">Failed to load samples: ${err.message}</div>`;
    }
  }
  loadSamples();

  // Search Execution
  if (btnSearch) {
    btnSearch.addEventListener("click", () => {
      executeSearch();
    });
  }

  async function executeSearch() {
    if (!currentSearchFile) return;

    btnSearch.disabled = true;
    if (searchSpinner) searchSpinner.classList.remove("hidden");
    if (btnText) btnText.textContent = "Matching...";
    if (telemetryTag) telemetryTag.textContent = "Processing query...";

    const formData = new FormData();
    formData.append("file", currentSearchFile);
    formData.append("top_k", sliderTopk.value);
    formData.append("threshold", sliderThreshold.value);

    try {
      const response = await fetch("/api/match", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errData.detail || "Query matching failed.");
      }

      const data = await response.json();
      renderResults(data);
    } catch (err) {
      alert(`Search error: ${err.message}`);
      if (telemetryTag) telemetryTag.textContent = "Query failed";
    } finally {
      btnSearch.disabled = false;
      if (searchSpinner) searchSpinner.classList.add("hidden");
      if (btnText) btnText.textContent = "Search Catalogue";
    }
  }

  function renderResults(data) {
    emptyState.classList.add("hidden");
    decisionBanner.classList.remove("hidden");
    candidatesList.classList.remove("hidden");

    if (telemetryTag) {
      telemetryTag.textContent = `Completed in ${data.query_time_ms} ms (${data.top_k} results)`;
    }

    const isMatch = data.decision === "MATCH";
    decisionBadge.textContent = data.decision;
    if (isMatch) {
      decisionBanner.classList.remove("unknown");
    } else {
      decisionBanner.classList.add("unknown");
    }

    metricBestSim.textContent = data.best_similarity.toFixed(4);
    metricThreshold.textContent = data.threshold.toFixed(2);
    metricLatency.textContent = `${data.query_time_ms} ms`;

    candidatesList.innerHTML = "";
    data.results.forEach((item) => {
      const card = document.createElement("div");
      card.className = `candidate-card ${item.rank === 1 ? "top1" : ""}`;
      
      const simPercent = Math.max(0, Math.min(100, item.similarity * 100)).toFixed(1);
      const imgUrl = item.image_url || `/${item.image_path}`;

      card.innerHTML = `
        <div class="rank-badge">#${item.rank}</div>
        <img class="candidate-thumb" src="${imgUrl}" alt="${item.product_name}" loading="lazy">
        <div class="candidate-info">
          <div class="candidate-name">${item.product_name}</div>
          <div class="candidate-meta">
            <span class="badge-category">${item.category}</span>
            <span class="candidate-id">${item.product_id}</span>
            ${item.width ? `<span class="candidate-dimensions">${item.width}×${item.height}px</span>` : ""}
          </div>
        </div>
        <div class="candidate-sim-box">
          <div class="sim-score-label">${item.similarity.toFixed(4)}</div>
          <div class="sim-bar-bg">
            <div class="sim-bar-fill" style="width: ${simPercent}%;"></div>
          </div>
        </div>
      `;
      candidatesList.appendChild(card);
    });
  }

  function resetResults() {
    if (emptyState) emptyState.classList.remove("hidden");
    if (decisionBanner) decisionBanner.classList.add("hidden");
    if (candidatesList) {
      candidatesList.classList.add("hidden");
      candidatesList.innerHTML = "";
    }
    if (telemetryTag) telemetryTag.textContent = "Ready for query";
  }

  // ── Tab 2: Add New Catalogue Item Elements & Logic ───────────────────────
  const addDropzone = document.getElementById("add-dropzone");
  const addFileInput = document.getElementById("add-file-input");
  const addDropzonePrompt = document.getElementById("add-dropzone-prompt");
  const addPreviewContainer = document.getElementById("add-preview-container");
  const addImagePreview = document.getElementById("add-image-preview");
  const btnClearAddImage = document.getElementById("btn-clear-add-image");

  const addCategory = document.getElementById("add-category");
  const addName = document.getElementById("add-name");
  const addSubcategory = document.getElementById("add-subcategory");
  const btnAddSubmit = document.getElementById("btn-add-submit");
  const addSpinner = document.getElementById("add-spinner");
  const addTelemetryTag = document.getElementById("add-telemetry-tag");

  const addSuccessCard = document.getElementById("add-success-card");
  const addEmptyState = document.getElementById("add-empty-state");
  const addedThumb = document.getElementById("added-thumb");
  const addedTitle = document.getElementById("added-title");
  const addedCategory = document.getElementById("added-category");
  const addedId = document.getElementById("added-id");
  const addedDimensions = document.getElementById("added-dimensions");
  const btnTestInSearch = document.getElementById("btn-test-in-search");

  const recentAddedContainer = document.getElementById("recent-added-container");
  const recentList = document.getElementById("recent-list");

  let currentAddFile = null;
  let lastAddedItem = null;

  if (addDropzone && addFileInput) {
    ["dragenter", "dragover"].forEach((eventName) => {
      addDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        addDropzone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      addDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        addDropzone.classList.remove("dragover");
      });
    });

    addDropzone.addEventListener("drop", (e) => {
      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        handleAddFile(files[0]);
      }
    });

    addFileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleAddFile(e.target.files[0]);
      }
    });
  }

  function handleAddFile(file) {
    if (!file.type.startsWith("image/")) {
      alert("Please upload a valid image file (JPEG, PNG, WebP).");
      return;
    }
    currentAddFile = file;
    const reader = new FileReader();
    reader.onload = (event) => {
      addImagePreview.src = event.target.result;
      addDropzonePrompt.classList.add("hidden");
      addPreviewContainer.classList.remove("hidden");
      btnAddSubmit.disabled = false;
    };
    reader.readAsDataURL(file);
  }

  if (btnClearAddImage) {
    btnClearAddImage.addEventListener("click", (e) => {
      e.stopPropagation();
      currentAddFile = null;
      addFileInput.value = "";
      addImagePreview.src = "";
      addPreviewContainer.classList.add("hidden");
      addDropzonePrompt.classList.remove("hidden");
      btnAddSubmit.disabled = true;
    });
  }

  // Handle Add to Catalogue Submission
  if (btnAddSubmit) {
    btnAddSubmit.addEventListener("click", async () => {
      if (!currentAddFile) return;

      btnAddSubmit.disabled = true;
      addSpinner.classList.remove("hidden");
      const btnTextEl = btnAddSubmit.querySelector(".btn-text");
      if (btnTextEl) btnTextEl.textContent = "Processing & Indexing...";
      if (addTelemetryTag) addTelemetryTag.textContent = "Extracting CLIP vector & indexing in FAISS...";

      const formData = new FormData();
      formData.append("file", currentAddFile);
      formData.append("category", addCategory.value);
      if (addName.value.trim()) {
        formData.append("product_name", addName.value.trim());
      }
      if (addSubcategory.value.trim()) {
        formData.append("subcategory", addSubcategory.value.trim());
      }

      try {
        const response = await fetch("/api/catalogue/add", {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({ detail: response.statusText }));
          throw new Error(errData.detail || "Failed to add item to catalogue.");
        }

        const data = await response.json();
        lastAddedItem = { ...data, fileBlob: currentAddFile };

        // Update stats
        refreshStats();
        loadSamples();

        // Render success card
        addEmptyState.classList.add("hidden");
        addSuccessCard.classList.remove("hidden");

        addedThumb.src = data.image_url;
        addedTitle.textContent = data.product_name;
        addedCategory.textContent = data.category;
        addedId.textContent = data.product_id;
        addedDimensions.textContent = `${data.width}×${data.height}px`;

        if (addTelemetryTag) {
          addTelemetryTag.textContent = `Indexed ${data.product_id} (Catalogue: ${data.catalogue_size} items)`;
        }

        // Add to session feed
        renderRecentItem(data);

        // Reset add form input
        currentAddFile = null;
        addFileInput.value = "";
        addImagePreview.src = "";
        addPreviewContainer.classList.add("hidden");
        addDropzonePrompt.classList.remove("hidden");
        addName.value = "";
        addSubcategory.value = "";

      } catch (err) {
        alert(`Error adding to catalogue: ${err.message}`);
        if (addTelemetryTag) addTelemetryTag.textContent = "Ingestion failed";
      } finally {
        btnAddSubmit.disabled = false;
        addSpinner.classList.add("hidden");
        if (btnTextEl) btnTextEl.textContent = "Add to Catalogue & Index Vector";
      }
    });
  }

  function renderRecentItem(item) {
    if (!recentAddedContainer || !recentList) return;
    recentAddedContainer.classList.remove("hidden");

    const row = document.createElement("div");
    row.className = "recent-item";
    row.innerHTML = `
      <img src="${item.image_url}" alt="${item.product_name}">
      <div class="recent-meta">
        <span class="recent-name">${item.product_name}</span>
        <div class="recent-badges">
          <span class="badge-category">${item.category}</span>
          <span class="candidate-id">${item.product_id}</span>
        </div>
      </div>
    `;
    recentList.prepend(row);
  }

  // Wire "Test Search with this Item" button
  if (btnTestInSearch) {
    btnTestInSearch.addEventListener("click", () => {
      if (!lastAddedItem) return;

      // 1. Switch tab to Search
      const searchTabBtn = document.getElementById("tab-search");
      if (searchTabBtn) searchTabBtn.click();

      // 2. Preload into search
      if (lastAddedItem.fileBlob) {
        handleSearchFile(lastAddedItem.fileBlob);
        executeSearch();
      }
    });
  }

});
