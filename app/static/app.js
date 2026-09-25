/**
 * Thuli — Minimalist Jewellery Visual Search Client
 */

document.addEventListener("DOMContentLoaded", () => {
  // ── Tab Navigation ───────────────────────────────────────────────────────
  const tabButtons = document.querySelectorAll(".tab-btn");
  const tabViews = document.querySelectorAll(".view-pane");

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

  // Live Catalogue Size
  const statCatalogue = document.getElementById("stat-catalogue");
  async function refreshStats() {
    try {
      const res = await fetch("/api/stats");
      if (res.ok) {
        const data = await res.json();
        if (statCatalogue) {
          statCatalogue.textContent = `${data.total_items.toLocaleString()} Items`;
        }
      }
    } catch (e) {
      console.warn("Could not fetch stats:", e);
    }
  }
  refreshStats();

  // ── Tab 1: Visual Search ─────────────────────────────────────────────────
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
  const btnLabel = btnSearch ? btnSearch.querySelector(".btn-label") : null;

  const sampleGrid = document.getElementById("sample-grid");
  const telemetryTag = document.getElementById("telemetry-tag");

  const decisionBanner = document.getElementById("decision-banner");
  const decisionBadge = document.getElementById("decision-badge");
  const metricBestSim = document.getElementById("metric-best-sim");
  const metricLatency = document.getElementById("metric-latency");

  const emptyState = document.getElementById("empty-state");
  const candidatesList = document.getElementById("candidates-list");

  let currentSearchFile = null;

  // Sliders Sync
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

  // Dropzone Handlers
  if (dropzone && fileInput) {
    ["dragenter", "dragover"].forEach((evt) => {
      dropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        dropzone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach((evt) => {
      dropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
      });
    });

    dropzone.addEventListener("drop", (e) => {
      const files = e.dataTransfer.files;
      if (files && files.length > 0) handleSearchFile(files[0]);
    });

    fileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) handleSearchFile(e.target.files[0]);
    });
  }

  function handleSearchFile(file) {
    if (!file.type.startsWith("image/")) {
      alert("Please upload a valid image (JPEG, PNG, WebP).");
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

  // Load Samples
  async function loadSamples() {
    if (!sampleGrid) return;
    try {
      const res = await fetch("/api/samples");
      if (!res.ok) throw new Error("Could not load samples");
      const samples = await res.json();

      sampleGrid.innerHTML = "";
      samples.slice(0, 4).forEach((sample) => {
        const chip = document.createElement("div");
        chip.className = "sample-chip";
        chip.innerHTML = `
          <img src="${sample.image_path}" alt="${sample.product_name}" loading="lazy">
          <span>${sample.category}</span>
        `;
        chip.addEventListener("click", async () => {
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
        sampleGrid.appendChild(chip);
      });
    } catch (err) {
      sampleGrid.innerHTML = `<span class="samples-loading">Samples unavailable</span>`;
    }
  }
  loadSamples();

  // Search Action
  if (btnSearch) {
    btnSearch.addEventListener("click", () => {
      executeSearch();
    });
  }

  async function executeSearch() {
    if (!currentSearchFile) return;

    btnSearch.disabled = true;
    if (searchSpinner) searchSpinner.classList.remove("hidden");
    if (btnLabel) btnLabel.textContent = "Searching...";
    if (telemetryTag) telemetryTag.textContent = "Retrieving...";

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
      if (telemetryTag) telemetryTag.textContent = "Error";
    } finally {
      btnSearch.disabled = false;
      if (searchSpinner) searchSpinner.classList.add("hidden");
      if (btnLabel) btnLabel.textContent = "Find Matching Jewellery";
    }
  }

  function renderResults(data) {
    emptyState.classList.add("hidden");
    decisionBanner.classList.remove("hidden");
    candidatesList.classList.remove("hidden");

    if (telemetryTag) {
      telemetryTag.textContent = `${data.query_time_ms} ms (${data.top_k} results)`;
    }

    const isMatch = data.decision === "MATCH";
    decisionBadge.textContent = data.decision;
    if (isMatch) {
      decisionBanner.classList.remove("unknown");
    } else {
      decisionBanner.classList.add("unknown");
    }

    metricBestSim.textContent = `${(data.best_similarity * 100).toFixed(1)}%`;
    metricLatency.textContent = `${data.query_time_ms} ms`;

    candidatesList.innerHTML = "";
    data.results.forEach((item) => {
      const row = document.createElement("div");
      row.className = `match-item ${item.rank === 1 ? "top1" : ""}`;

      const simPercent = Math.max(0, Math.min(100, item.similarity * 100)).toFixed(1);
      const imgUrl = item.image_url || `/${item.image_path}`;

      row.innerHTML = `
        <span class="rank-num">#${item.rank}</span>
        <img class="match-thumb" src="${imgUrl}" alt="${item.product_name}" loading="lazy">
        <div class="match-details">
          <span class="match-title">${item.product_name}</span>
          <div class="match-sub">
            <span class="tag-cat">${item.category}</span>
            <span class="tag-id">${item.product_id}</span>
          </div>
        </div>
        <div class="match-score">
          <span class="score-text">${simPercent}%</span>
          <div class="score-track">
            <div class="score-bar" style="width: ${simPercent}%;"></div>
          </div>
        </div>
      `;
      candidatesList.appendChild(row);
    });
  }

  function resetResults() {
    if (emptyState) emptyState.classList.remove("hidden");
    if (decisionBanner) decisionBanner.classList.add("hidden");
    if (candidatesList) {
      candidatesList.classList.add("hidden");
      candidatesList.innerHTML = "";
    }
    if (telemetryTag) telemetryTag.textContent = "Ready";
  }

  // ── Tab 2: Add New Catalogue Item ────────────────────────────────────────
  const addDropzone = document.getElementById("add-dropzone");
  const addFileInput = document.getElementById("add-file-input");
  const addDropzonePrompt = document.getElementById("add-dropzone-prompt");
  const addPreviewContainer = document.getElementById("add-preview-container");
  const addImagePreview = document.getElementById("add-image-preview");
  const btnClearAddImage = document.getElementById("btn-clear-add-image");

  const addCategory = document.getElementById("add-category");
  const addName = document.getElementById("add-name");
  const btnAddSubmit = document.getElementById("btn-add-submit");
  const addSpinner = document.getElementById("add-spinner");
  const addTelemetryTag = document.getElementById("add-telemetry-tag");

  const addSuccessCard = document.getElementById("add-success-card");
  const addEmptyState = document.getElementById("add-empty-state");
  const addedThumb = document.getElementById("added-thumb");
  const addedTitle = document.getElementById("added-title");
  const addedCategory = document.getElementById("added-category");
  const addedId = document.getElementById("added-id");
  const btnTestInSearch = document.getElementById("btn-test-in-search");

  const recentAddedContainer = document.getElementById("recent-added-container");
  const recentList = document.getElementById("recent-list");

  let currentAddFile = null;
  let lastAddedItem = null;

  if (addDropzone && addFileInput) {
    ["dragenter", "dragover"].forEach((evt) => {
      addDropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        addDropzone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach((evt) => {
      addDropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        addDropzone.classList.remove("dragover");
      });
    });

    addDropzone.addEventListener("drop", (e) => {
      const files = e.dataTransfer.files;
      if (files && files.length > 0) handleAddFile(files[0]);
    });

    addFileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) handleAddFile(e.target.files[0]);
    });
  }

  function handleAddFile(file) {
    if (!file.type.startsWith("image/")) {
      alert("Please upload a valid image (JPEG, PNG, WebP).");
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

  if (btnAddSubmit) {
    btnAddSubmit.addEventListener("click", async () => {
      if (!currentAddFile) return;

      btnAddSubmit.disabled = true;
      if (addSpinner) addSpinner.classList.remove("hidden");
      const btnLabelEl = btnAddSubmit.querySelector(".btn-label");
      if (btnLabelEl) btnLabelEl.textContent = "Indexing...";
      if (addTelemetryTag) addTelemetryTag.textContent = "Indexing vector...";

      const formData = new FormData();
      formData.append("file", currentAddFile);
      formData.append("category", addCategory.value);
      if (addName && addName.value.trim()) {
        formData.append("product_name", addName.value.trim());
      }

      try {
        const response = await fetch("/api/catalogue/add", {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({ detail: response.statusText }));
          throw new Error(errData.detail || "Failed to add item.");
        }

        const data = await response.json();
        lastAddedItem = { ...data, fileBlob: currentAddFile };

        refreshStats();
        loadSamples();

        addEmptyState.classList.add("hidden");
        addSuccessCard.classList.remove("hidden");

        addedThumb.src = data.image_url;
        addedTitle.textContent = data.product_name;
        addedCategory.textContent = data.category;
        addedId.textContent = data.product_id;

        if (addTelemetryTag) {
          addTelemetryTag.textContent = `Indexed ${data.product_id}`;
        }

        renderRecentRow(data);

        // Reset Add inputs
        currentAddFile = null;
        addFileInput.value = "";
        addImagePreview.src = "";
        addPreviewContainer.classList.add("hidden");
        addDropzonePrompt.classList.remove("hidden");
        if (addName) addName.value = "";

      } catch (err) {
        alert(`Error adding to catalogue: ${err.message}`);
        if (addTelemetryTag) addTelemetryTag.textContent = "Failed";
      } finally {
        btnAddSubmit.disabled = false;
        if (addSpinner) addSpinner.classList.add("hidden");
        if (btnLabelEl) btnLabelEl.textContent = "Add to Catalogue & Index";
      }
    });
  }

  function renderRecentRow(item) {
    if (!recentAddedContainer || !recentList) return;
    recentAddedContainer.classList.remove("hidden");

    const row = document.createElement("div");
    row.className = "recent-row";
    row.innerHTML = `
      <img src="${item.image_url}" alt="${item.product_name}">
      <span>${item.product_name} (${item.category} • ${item.product_id})</span>
    `;
    recentList.prepend(row);
  }

  // "Search for this Item" Button
  if (btnTestInSearch) {
    btnTestInSearch.addEventListener("click", () => {
      if (!lastAddedItem) return;

      const searchTabBtn = document.getElementById("tab-search");
      if (searchTabBtn) searchTabBtn.click();

      if (lastAddedItem.fileBlob) {
        handleSearchFile(lastAddedItem.fileBlob);
        executeSearch();
      }
    });
  }

  // ── Phase 7: Evaluation Dashboard ───────────────────────────────────────────

  const btnRunEval     = document.getElementById("btn-run-eval");
  const btnRefreshEval = document.getElementById("btn-refresh-eval");
  const evalSpinner    = document.getElementById("eval-spinner");
  const runEvalLabel   = document.getElementById("run-eval-label");
  const evalEmpty      = document.getElementById("eval-empty");
  const evalContent    = document.getElementById("eval-content");

  // Auto-load existing results when user clicks Evaluation tab
  const tabEval = document.getElementById("tab-eval");
  if (tabEval) {
    tabEval.addEventListener("click", () => {
      loadEvalResults(false);
    });
  }

  if (btnRefreshEval) {
    btnRefreshEval.addEventListener("click", () => loadEvalResults(false));
  }

  if (btnRunEval) {
    btnRunEval.addEventListener("click", () => triggerEvaluation());
  }

  async function triggerEvaluation() {
    if (!btnRunEval) return;
    btnRunEval.disabled = true;
    if (runEvalLabel) runEvalLabel.textContent = "Running…";
    if (evalSpinner)  evalSpinner.classList.remove("hidden");

    try {
      const res = await fetch("/api/evaluation/run", { method: "POST" });
      if (!res.ok) {
        const err = await res.json();
        alert("Evaluation failed: " + (err.detail || "Unknown error"));
        return;
      }
      const data = await res.json();
      renderEvalDashboard(data.metrics);
    } catch (e) {
      alert("Network error during evaluation: " + e.message);
    } finally {
      btnRunEval.disabled = false;
      if (runEvalLabel) runEvalLabel.textContent = "▶ Run Evaluation";
      if (evalSpinner)  evalSpinner.classList.add("hidden");
    }
  }

  async function loadEvalResults(silent = true) {
    try {
      const res = await fetch("/api/evaluation/results");
      if (res.status === 404) {
        // No results yet — show empty state
        if (evalEmpty)   evalEmpty.classList.remove("hidden");
        if (evalContent) evalContent.classList.add("hidden");
        return;
      }
      if (!res.ok) return;
      const data = await res.json();
      renderEvalDashboard(data.metrics);
    } catch (e) {
      if (!silent) console.warn("Could not load eval results:", e);
    }
  }

  function renderEvalDashboard(metrics) {
    if (!metrics) return;
    if (evalEmpty)   evalEmpty.classList.add("hidden");
    if (evalContent) evalContent.classList.remove("hidden");

    // KPI Scoreboard
    setText("kpi-top1",      pct(metrics.top1_accuracy));
    setText("kpi-top5",      pct(metrics.top5_accuracy));
    setText("kpi-match",     metrics.match_count);
    setText("kpi-unknown",   metrics.unknown_count);
    setText("kpi-lat-med",   metrics.median_latency_ms + "ms");
    setText("kpi-lat-p95",   metrics.p95_latency_ms   + "ms");

    // Per-condition chart
    renderConditionChart(metrics.per_condition || {});

    // Dataset progress
    const prog = metrics.dataset_progress || {};
    setText("prog-current",  prog.current || 0);
    setText("progress-pct",  (prog.pct || 0) + "%");
    const fill = document.getElementById("progress-fill");
    if (fill) fill.style.width = Math.min(prog.pct || 0, 100) + "%";

    // Match / Unknown split bar
    const total = (metrics.match_count || 0) + (metrics.unknown_count || 0);
    const matchPct   = total > 0 ? (metrics.match_count / total * 100).toFixed(1) : 50;
    const unknownPct = total > 0 ? (metrics.unknown_count / total * 100).toFixed(1) : 50;
    setStyle("verdict-match-bar",   "width", matchPct + "%");
    setStyle("verdict-unknown-bar", "width", unknownPct + "%");
    setText("vs-match",   metrics.match_count   || 0);
    setText("vs-unknown", metrics.unknown_count || 0);

    // Failures table
    renderFailures(metrics.worst_failures || []);

    // Meta
    setText("eval-run-at", metrics.run_at ? new Date(metrics.run_at).toLocaleString() : "—");
    setText("eval-total",  metrics.total_images ?? "—");
  }

  function renderConditionChart(perCondition) {
    const container = document.getElementById("condition-chart");
    if (!container) return;

    const entries = Object.entries(perCondition).sort((a, b) =>
      b[1].top1_accuracy - a[1].top1_accuracy
    );

    container.innerHTML = `
      <div class="chart-legend">
        <div class="legend-item">
          <span class="legend-dot" style="background:var(--accent-gold)"></span> Top-1
        </div>
        <div class="legend-item">
          <span class="legend-dot" style="background:var(--accent-blue);opacity:0.7"></span> Top-5
        </div>
      </div>
    ` + entries.map(([cond, v]) => {
      const t1 = (v.top1_accuracy * 100).toFixed(0);
      const t5 = (v.top5_accuracy * 100).toFixed(0);
      return `
        <div class="cond-row">
          <span class="cond-name">${cond.replace(/_/g, " ")}</span>
          <div style="display:flex;flex-direction:column;gap:3px;">
            <div class="cond-bar-track">
              <div class="cond-bar-fill cond-bar-fill--top1" style="width:${t1}%"></div>
            </div>
            <div class="cond-bar-track">
              <div class="cond-bar-fill cond-bar-fill--top5" style="width:${t5}%"></div>
            </div>
          </div>
          <span class="cond-pct cond-pct--top1">${t1}%</span>
          <span class="cond-pct cond-pct--top5">${t5}%</span>
        </div>`;
    }).join("");
  }

  function renderFailures(failures) {
    const tbody = document.getElementById("failures-tbody");
    if (!tbody) return;

    if (!failures || failures.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="table-empty">🎉 No failures — the model nailed everything!</td></tr>`;
      return;
    }

    tbody.innerHTML = failures.map(r => {
      const simClass = r.top1_similarity < 0.5 ? "sim-low" : r.top1_similarity < 0.7 ? "sim-mid" : "sim-high";
      const decBadge = r.decision === "MATCH"
        ? `<span class="badge-match">MATCH</span>`
        : `<span class="badge-unknown">UNKNOWN</span>`;
      const gtRank = r.gt_rank > 0 ? `#${r.gt_rank}` : "Not in Top-5";
      const imgSrc = `/evaluation/images/${r.image_id}.jpeg`;

      return `<tr>
        <td><img src="${imgSrc}" class="failure-thumb" alt="${r.image_id}" onerror="this.style.display='none'"></td>
        <td style="font-family:monospace;color:var(--text-muted)">${r.image_id}</td>
        <td><span class="tag-cat">${r.ground_truth}</span></td>
        <td><span class="tag-cat" style="background:rgba(239,68,68,0.1);border-color:rgba(239,68,68,0.3);color:var(--accent-red)">${r.top1_category || "—"}</span></td>
        <td class="${simClass}">${r.top1_similarity.toFixed(4)}</td>
        <td style="color:var(--text-muted)">${gtRank}</td>
        <td><span class="tag-condition">${r.failure_condition.replace(/_/g, " ")}</span></td>
        <td>${decBadge}</td>
      </tr>`;
    }).join("");
  }

  // Helpers
  function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  function setStyle(id, prop, val) {
    const el = document.getElementById(id);
    if (el) el.style[prop] = val;
  }

  function pct(val) {
    return (val * 100).toFixed(1) + "%";
  }

  // Mount evaluation images for serving
  // Images are at /evaluation/images/* — handled via static mount below in main.py
});

