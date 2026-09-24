/**
 * Thuli Jewellery Retrieval — Web Test Client
 */

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
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
  const btnText = document.querySelector(".btn-text");

  const sampleGrid = document.getElementById("sample-grid");
  const telemetryTag = document.getElementById("telemetry-tag");

  const decisionBanner = document.getElementById("decision-banner");
  const decisionBadge = document.getElementById("decision-badge");
  const metricBestSim = document.getElementById("metric-best-sim");
  const metricThreshold = document.getElementById("metric-threshold");
  const metricLatency = document.getElementById("metric-latency");

  const emptyState = document.getElementById("empty-state");
  const candidatesList = document.getElementById("candidates-list");

  let currentFile = null;

  // 1. Controls Sync
  sliderTopk.addEventListener("input", (e) => {
    valTopk.textContent = e.target.value;
  });

  sliderThreshold.addEventListener("input", (e) => {
    valThreshold.textContent = parseFloat(e.target.value).toFixed(2);
  });

  // 2. Drag & Drop File Handling
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
      handleSelectedFile(files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleSelectedFile(e.target.files[0]);
    }
  });

  function handleSelectedFile(file) {
    if (!file.type.startsWith("image/")) {
      alert("Please upload a valid image file (JPEG, PNG, WebP).");
      return;
    }
    currentFile = file;
    const reader = new FileReader();
    reader.onload = (event) => {
      imagePreview.src = event.target.result;
      dropzonePrompt.classList.add("hidden");
      previewContainer.classList.remove("hidden");
      btnSearch.disabled = false;
    };
    reader.readAsDataURL(file);
  }

  btnClearImage.addEventListener("click", (e) => {
    e.stopPropagation();
    currentFile = null;
    fileInput.value = "";
    imagePreview.src = "";
    previewContainer.classList.add("hidden");
    dropzonePrompt.classList.remove("hidden");
    btnSearch.disabled = true;
    resetResults();
  });

  // 3. Load Sample Catalogue Images
  async function loadSamples() {
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
          // Fetch image blob and populate input
          try {
            const imgRes = await fetch(sample.image_path);
            const blob = await imgRes.blob();
            const file = new File([blob], `${sample.product_id}.jpg`, { type: "image/jpeg" });
            handleSelectedFile(file);
            // Auto search on sample click
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

  // 4. Search Execution
  btnSearch.addEventListener("click", () => {
    executeSearch();
  });

  async function executeSearch() {
    if (!currentFile) return;

    // UI Loading state
    btnSearch.disabled = true;
    searchSpinner.classList.remove("hidden");
    btnText.textContent = "Matching...";
    telemetryTag.textContent = "Processing query...";

    const formData = new FormData();
    formData.append("file", currentFile);
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
      telemetryTag.textContent = "Query failed";
    } finally {
      btnSearch.disabled = false;
      searchSpinner.classList.add("hidden");
      btnText.textContent = "Search Catalogue";
    }
  }

  // 5. Render Matching Results
  function renderResults(data) {
    emptyState.classList.add("hidden");
    decisionBanner.classList.remove("hidden");
    candidatesList.classList.remove("hidden");

    // Telemetry tag
    telemetryTag.textContent = `Completed in ${data.query_time_ms} ms (${data.top_k} results)`;

    // Decision Banner
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

    // Render Candidate Cards
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
    emptyState.classList.remove("hidden");
    decisionBanner.classList.add("hidden");
    candidatesList.classList.add("hidden");
    candidatesList.innerHTML = "";
    telemetryTag.textContent = "Ready for query";
  }
});
