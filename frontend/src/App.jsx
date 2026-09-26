import React, { useState, useEffect, useRef } from 'react';
import {
  Search,
  Sparkles,
  BarChart3,
  PlusCircle,
  Sun,
  Moon,
  Upload,
  X,
  Play,
  RotateCw,
  Download,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Layers,
  ChevronRight,
  Database,
  Sliders,
  ShieldCheck,
  Check,
  AlertCircle,
  Camera
} from 'lucide-react';

import CollectDataTab from './components/CollectDataTab';
import CollectionsTab from './components/CollectionsTab';
import DatasetTab from './components/DatasetTab';

export default function App() {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('thuli-theme') || 'light';
  });
  const [activeTab, setActiveTab] = useState('search');
  const [stats, setStats] = useState({ total_items: 6157, categories: {} });
  const [collectProduct, setCollectProduct] = useState(null);

  // ── Sync Theme ─────────────────────────────────────────────────────────────
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('thuli-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => (prev === 'light' ? 'dark' : 'light'));
  };

  // ── Fetch Catalogue Stats ─────────────────────────────────────────────────
  const fetchStats = async () => {
    try {
      const res = await fetch('/api/stats');
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (err) {
      console.warn('Could not fetch stats:', err);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  // ── Tab 1: Visual Search State ─────────────────────────────────────────────
  const [searchImage, setSearchImage] = useState(null);
  const [searchFile, setSearchFile] = useState(null);
  const [topK, setTopK] = useState(5);
  const [threshold, setThreshold] = useState(0.75);
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState(null);
  const [samples, setSamples] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  // Load sample items
  useEffect(() => {
    const fetchSamples = async () => {
      try {
        const res = await fetch('/api/samples');
        if (res.ok) {
          const data = await res.json();
          setSamples(data);
        }
      } catch (err) {
        console.warn('Could not load samples:', err);
      }
    };
    fetchSamples();
  }, []);

  const handleSelectFile = (file) => {
    if (!file || !file.type.startsWith('image/')) {
      alert('Please select a valid image file (JPEG, PNG, WebP).');
      return;
    }
    setSearchFile(file);
    const reader = new FileReader();
    reader.onload = (e) => {
      setSearchImage(e.target.result);
      setSearchResults(null);
    };
    reader.readAsDataURL(file);
  };

  const handleClearImage = () => {
    setSearchImage(null);
    setSearchFile(null);
    setSearchResults(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const executeSearch = async (overrideFile = null) => {
    const fileToUse = overrideFile || searchFile;
    if (!fileToUse) return;

    setIsSearching(true);
    const formData = new FormData();
    formData.append('file', fileToUse);
    formData.append('top_k', topK);
    formData.append('threshold', threshold);

    try {
      const res = await fetch('/api/match', {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Visual search failed.');
      }
      const data = await res.json();
      setSearchResults(data);
    } catch (err) {
      alert('Search Error: ' + err.message);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSampleClick = async (sample) => {
    try {
      const res = await fetch(sample.image_path);
      const blob = await res.blob();
      const file = new File([blob], `${sample.product_id}.jpg`, { type: 'image/jpeg' });
      setSearchFile(file);
      setSearchImage(sample.image_path);
      executeSearch(file);
    } catch (err) {
      console.error('Error with sample:', err);
    }
  };

  // ── Tab 2: Evaluation Arena State ──────────────────────────────────────────
  const [evalMetrics, setEvalMetrics] = useState(null);
  const [isLoadingEval, setIsLoadingEval] = useState(false);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [evalFilter, setEvalFilter] = useState('all'); // 'all' | 'correct' | 'wrong'
  const [evalConditionFilter, setEvalConditionFilter] = useState('all');
  const [evalSearchText, setEvalSearchText] = useState('');

  const fetchEvalMetrics = async () => {
    setIsLoadingEval(true);
    try {
      const res = await fetch('/api/evaluation/results');
      if (res.status === 404) {
        setEvalMetrics(null);
      } else if (res.ok) {
        const data = await res.json();
        setEvalMetrics(data.metrics);
      }
    } catch (err) {
      console.warn('Eval results fetch failed:', err);
    } finally {
      setIsLoadingEval(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'eval') {
      fetchEvalMetrics();
    }
  }, [activeTab]);

  const triggerEvaluation = async () => {
    setIsEvaluating(true);
    try {
      const res = await fetch('/api/evaluation/run', { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Evaluation failed.');
      }
      const data = await res.json();
      setEvalMetrics(data.metrics);
    } catch (err) {
      alert('Evaluation error: ' + err.message);
    } finally {
      setIsEvaluating(false);
    }
  };

  // ── Tab 3: Add Item State ──────────────────────────────────────────────────
  const [addFile, setAddFile] = useState(null);
  const [addImagePreview, setAddImagePreview] = useState(null);
  const [addCategory, setAddCategory] = useState('ring');
  const [addName, setAddName] = useState('');
  const [isAdding, setIsAdding] = useState(false);
  const [lastAdded, setLastAdded] = useState(null);
  const [recentItems, setRecentItems] = useState([]);
  const addFileInputRef = useRef(null);

  const handleSelectAddFile = (file) => {
    if (!file || !file.type.startsWith('image/')) {
      alert('Please upload an image.');
      return;
    }
    setAddFile(file);
    const reader = new FileReader();
    reader.onload = (e) => setAddImagePreview(e.target.result);
    reader.readAsDataURL(file);
  };

  const handleClearAddImage = () => {
    setAddFile(null);
    setAddImagePreview(null);
    if (addFileInputRef.current) addFileInputRef.current.value = '';
  };

  const handleAddItem = async (e) => {
    e.preventDefault();
    if (!addFile) return;

    setIsAdding(true);
    const formData = new FormData();
    formData.append('file', addFile);
    formData.append('category', addCategory);
    if (addName.trim()) formData.append('product_name', addName.trim());

    try {
      const res = await fetch('/api/catalogue/add', {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Failed to add item');
      }
      const data = await res.json();
      const itemWithBlob = { ...data, fileBlob: addFile };
      setLastAdded(itemWithBlob);
      setRecentItems(prev => [itemWithBlob, ...prev.slice(0, 4)]);
      fetchStats();

      // Reset form
      handleClearAddImage();
      setAddName('');
    } catch (err) {
      alert('Error adding item: ' + err.message);
    } finally {
      setIsAdding(false);
    }
  };

  const handleTestProductInSearch = async (prod) => {
    if (!prod?.image_url) return;
    try {
      const res = await fetch(prod.image_url);
      const blob = await res.blob();
      const file = new File([blob], `${prod.product_id}.jpg`, { type: 'image/jpeg' });
      setSearchFile(file);
      setSearchImage(prod.image_url);
      setActiveTab('search');
      executeSearch(file);
    } catch (err) {
      console.error('Error initiating visual search:', err);
      setActiveTab('search');
      setSearchImage(prod.image_url);
    }
  };

  const testAddedInSearch = (item) => {
    if (!item?.fileBlob) return;
    setSearchFile(item.fileBlob);
    setSearchImage(item.image_url);
    setActiveTab('search');
    executeSearch(item.fileBlob);
  };

  return (
    <div className="app-wrapper">
      {/* ── Header ───────────────────────────────────────────────────────── */}
      <header className="app-header">
        <div className="header-inner">
          <div className="brand-section">
            <div className="brand-logo-icon">💎</div>
            <div>
              <div className="brand-title">
                THULI
                <span className="brand-badge">
                  {stats.total_items?.toLocaleString() || '6,157'} Items
                </span>
              </div>
            </div>
          </div>

          <nav className="nav-tabs">
            <button
              className={`nav-tab-btn ${activeTab === 'search' ? 'active' : ''}`}
              onClick={() => setActiveTab('search')}
            >
              <Search size={16} />
              <span>Visual Search</span>
            </button>
            <button
              className={`nav-tab-btn ${activeTab === 'collect' || activeTab === 'add' ? 'active' : ''}`}
              onClick={() => setActiveTab('collect')}
            >
              <Camera size={16} />
              <span>Collect Data</span>
            </button>
            <button
              className={`nav-tab-btn ${activeTab === 'collections' ? 'active' : ''}`}
              onClick={() => setActiveTab('collections')}
            >
              <Layers size={16} />
              <span>Collections</span>
            </button>
            <button
              className={`nav-tab-btn ${activeTab === 'dataset' ? 'active' : ''}`}
              onClick={() => setActiveTab('dataset')}
            >
              <Database size={16} />
              <span>Dataset</span>
            </button>
            <button
              className={`nav-tab-btn ${activeTab === 'eval' ? 'active' : ''}`}
              onClick={() => setActiveTab('eval')}
            >
              <BarChart3 size={16} />
              <span>Evaluation Arena</span>
              {evalMetrics && (
                <span style={{
                  fontSize: '0.7rem',
                  background: 'var(--primary-light)',
                  color: 'var(--primary)',
                  padding: '1px 6px',
                  borderRadius: '999px',
                  fontFamily: 'var(--font-mono)'
                }}>
                  {(evalMetrics.top1_accuracy * 100).toFixed(0)}%
                </span>
              )}
            </button>
          </nav>

          <div className="header-actions">
            <button
              className="icon-btn"
              onClick={toggleTheme}
              title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} theme`}
            >
              {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
            </button>
          </div>
        </div>
      </header>

      {/* ── Main Container ───────────────────────────────────────────────── */}
      <main className="app-container">
        {/* VIEW 1: VISUAL SEARCH */}
        {activeTab === 'search' && (
          <div className="two-col-grid">
            {/* Left Column: Query Card */}
            <div className="ui-card">
              <div className="card-title-row">
                <h2 className="card-title">
                  <Sparkles size={18} style={{ color: 'var(--primary)' }} />
                  Query Photograph
                </h2>
                {searchImage && (
                  <button className="btn-secondary" onClick={handleClearImage}>
                    Clear
                  </button>
                )}
              </div>

              {/* Dropzone */}
              {!searchImage ? (
                <div
                  className={`dropzone-container ${isDragging ? 'is-dragover' : ''}`}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setIsDragging(true);
                  }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setIsDragging(false);
                    if (e.dataTransfer.files?.length > 0) {
                      handleSelectFile(e.dataTransfer.files[0]);
                    }
                  }}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    type="file"
                    ref={fileInputRef}
                    accept="image/*"
                    style={{ display: 'none' }}
                    onChange={(e) => {
                      if (e.target.files?.length > 0) {
                        handleSelectFile(e.target.files[0]);
                      }
                    }}
                  />
                  <div className="drop-icon-box">
                    <Upload size={24} />
                  </div>
                  <div className="drop-text-main">Click or drop jewellery photo</div>
                  <div className="drop-text-sub">Supports JPEG, PNG, WebP</div>
                </div>
              ) : (
                <div className="preview-container">
                  <img src={searchImage} alt="Query preview" className="preview-image" />
                  <button
                    className="btn-clear-preview"
                    onClick={handleClearImage}
                    title="Remove photo"
                  >
                    <X size={16} />
                  </button>
                </div>
              )}

              {/* Action Button */}
              <div style={{ marginTop: '1.25rem' }}>
                <button
                  className="btn-primary"
                  disabled={!searchFile || isSearching}
                  onClick={() => executeSearch()}
                >
                  {isSearching ? (
                    <>
                      <RotateCw size={18} className="spin-anim" />
                      Retrieving Top Matches...
                    </>
                  ) : (
                    <>
                      <Search size={18} />
                      Find Matching Jewellery
                    </>
                  )}
                </button>
              </div>

              {/* Sample catalogue chips */}
              {samples.length > 0 && (
                <div className="sample-section">
                  <span className="sample-title">Or Try Catalogue Samples:</span>
                  <div className="sample-pills-row">
                    {samples.slice(0, 4).map((sample) => (
                      <div
                        key={sample.product_id}
                        className="sample-pill"
                        onClick={() => handleSampleClick(sample)}
                      >
                        <img src={sample.image_path} alt={sample.product_name} />
                        <span>{sample.category}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Settings Accordion */}
              <div className="settings-box">
                <div className="setting-row">
                  <div className="setting-header">
                    <span>Candidates (Top-K)</span>
                    <span className="setting-val">{topK}</span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    value={topK}
                    onChange={(e) => setTopK(Number(e.target.value))}
                    className="slider-input"
                  />
                </div>
                <div className="setting-row">
                  <div className="setting-header">
                    <span>Match Threshold (τ)</span>
                    <span className="setting-val">{threshold.toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min="0.50"
                    max="0.95"
                    step="0.01"
                    value={threshold}
                    onChange={(e) => setThreshold(Number(e.target.value))}
                    className="slider-input"
                  />
                </div>
              </div>
            </div>

            {/* Right Column: Results Card */}
            <div className="ui-card">
              <div className="card-title-row">
                <h2 className="card-title">
                  <Layers size={18} style={{ color: 'var(--primary)' }} />
                  Retrieval Candidates
                </h2>
                {searchResults && (
                  <span style={{
                    fontSize: '0.8rem',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-muted)'
                  }}>
                    {searchResults.query_time_ms} ms
                  </span>
                )}
              </div>

              {/* Results or Empty State */}
              {searchResults ? (
                <div>
                  {/* Verdict Banner */}
                  <div
                    className={`verdict-banner ${
                      searchResults.decision === 'MATCH' ? 'match' : 'unknown'
                    }`}
                  >
                    <div className="verdict-left">
                      <span className="verdict-badge">
                        {searchResults.decision === 'MATCH' ? 'MATCH' : 'UNKNOWN'}
                      </span>
                      <div>
                        <div className="verdict-text-main">
                          {searchResults.decision === 'MATCH'
                            ? 'Confident Match Identified'
                            : 'Unknown Jewellery Item'}
                        </div>
                        <div className="verdict-text-sub">
                          {searchResults.decision === 'MATCH'
                            ? `Similarity exceeds threshold ${threshold.toFixed(2)}`
                            : `Similarity ${(searchResults.best_similarity * 100).toFixed(1)}% is below ${threshold.toFixed(2)}`}
                        </div>
                      </div>
                    </div>
                    <div className="verdict-metrics">
                      <div className="verdict-metric-item">
                        <div className="verdict-metric-label">Best Match</div>
                        <div className="verdict-metric-value">
                          {(searchResults.best_similarity * 100).toFixed(1)}%
                        </div>
                      </div>
                      <div className="verdict-metric-item">
                        <div className="verdict-metric-label">Latency</div>
                        <div className="verdict-metric-value">
                          {searchResults.query_time_ms}ms
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Candidates List */}
                  <div className="candidates-grid">
                    {searchResults.results.map((item) => {
                      const simPct = (Math.max(0, Math.min(1, item.similarity)) * 100).toFixed(1);
                      const imgUrl = item.image_url || `/${item.image_path}`;
                      return (
                        <div
                          key={item.product_id}
                          className={`candidate-card ${item.rank === 1 ? 'top1' : ''}`}
                        >
                          <div className="rank-circle">#{item.rank}</div>
                          <img
                            src={imgUrl}
                            alt={item.product_name}
                            className="candidate-thumb"
                            onError={(e) => {
                              e.target.style.display = 'none';
                            }}
                          />
                          <div className="candidate-info">
                            <div className="candidate-title">{item.product_name}</div>
                            <div className="candidate-tags">
                              <span className="tag-badge">{item.category}</span>
                              <span className="tag-id">{item.product_id}</span>
                            </div>
                          </div>
                          <div className="candidate-score-block">
                            <div className="candidate-score-num">{simPct}%</div>
                            <div className="score-bar-bg">
                              <div
                                className="score-bar-fill"
                                style={{ width: `${simPct}%` }}
                              />
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div className="empty-placeholder">
                  <div className="empty-icon-box">
                    <Search size={32} />
                  </div>
                  <div className="empty-title">No Active Query</div>
                  <div className="empty-desc">
                    Upload a jewellery photo or pick one of the catalogue samples to view matching items.
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* VIEW 2: EVALUATION ARENA (PHASE 7) */}
        {activeTab === 'eval' && (
          <div>
            {/* Hero Header */}
            <div className="eval-hero-banner">
              <div className="eval-hero-info">
                <h1>Baseline Evaluation Arena</h1>
                <p>
                  Benchmarking CLIP ViT-B/32 against {evalMetrics?.total_images || 39} real-world stumper test cases (angle, blur, lighting, occlusion).
                </p>
              </div>
              <div className="eval-hero-actions">
                <button
                  className="btn-primary"
                  style={{ width: 'auto' }}
                  onClick={triggerEvaluation}
                  disabled={isEvaluating}
                >
                  {isEvaluating ? (
                    <>
                      <RotateCw size={16} className="spin-anim" />
                      Evaluating...
                    </>
                  ) : (
                    <>
                      <Play size={16} />
                      Run Evaluation
                    </>
                  )}
                </button>
                <button
                  className="btn-secondary"
                  onClick={fetchEvalMetrics}
                  disabled={isLoadingEval}
                  title="Refresh metrics"
                >
                  <RotateCw size={16} className={isLoadingEval ? 'spin-anim' : ''} />
                  Refresh
                </button>
                <a
                  href="/api/evaluation/download"
                  download
                  className="btn-secondary"
                  style={{ textDecoration: 'none' }}
                >
                  <Download size={16} />
                  Download CSV
                </a>
              </div>
            </div>

            {/* Dashboard Content */}
            {evalMetrics ? (
              <div>
                {/* KPI Cards */}
                <div className="kpi-grid">
                  <div className="kpi-card gold">
                    <div className="kpi-label">Top-1 Accuracy</div>
                    <div className="kpi-value">
                      {(evalMetrics.top1_accuracy * 100).toFixed(1)}%
                    </div>
                    <div className="kpi-sub">Exact primary match</div>
                  </div>

                  <div className="kpi-card blue">
                    <div className="kpi-label">Top-5 Accuracy</div>
                    <div className="kpi-value">
                      {(evalMetrics.top5_accuracy * 100).toFixed(1)}%
                    </div>
                    <div className="kpi-sub">Found in 5 candidates</div>
                  </div>

                  <div className="kpi-card red">
                    <div className="kpi-label">False Acceptance (FAR)</div>
                    <div className="kpi-value">
                      {(evalMetrics.far_pct !== undefined ? evalMetrics.far_pct : ((evalMetrics.false_acceptance_rate || 0) * 100)).toFixed(1)}%
                    </div>
                    <div className="kpi-sub">
                      Wrong match ({evalMetrics.wrong_matches_count ?? 0} queries)
                    </div>
                  </div>

                  <div className="kpi-card amber">
                    <div className="kpi-label">False Rejection (FRR)</div>
                    <div className="kpi-value">
                      {(evalMetrics.frr_pct !== undefined ? evalMetrics.frr_pct : ((evalMetrics.false_rejection_rate || 0) * 100)).toFixed(1)}%
                    </div>
                    <div className="kpi-sub">
                      Rejected as UNKNOWN ({evalMetrics.unknown_count ?? 0})
                    </div>
                  </div>

                  <div className="kpi-card green">
                    <div className="kpi-label">Match Verdicts</div>
                    <div className="kpi-value">{evalMetrics.match_count}</div>
                    <div className="kpi-sub">≥ 0.75 threshold</div>
                  </div>

                  <div className="kpi-card orange">
                    <div className="kpi-label">Unknown Verdicts</div>
                    <div className="kpi-value">{evalMetrics.unknown_count}</div>
                    <div className="kpi-sub">&lt; 0.75 threshold</div>
                  </div>

                  <div className="kpi-card purple">
                    <div className="kpi-label">Median Latency</div>
                    <div className="kpi-value">{evalMetrics.median_latency_ms}ms</div>
                    <div className="kpi-sub">P50 inference time</div>
                  </div>

                  <div className="kpi-card cyan">
                    <div className="kpi-label">P95 Latency</div>
                    <div className="kpi-value">{evalMetrics.p95_latency_ms}ms</div>
                    <div className="kpi-sub">95th percentile</div>
                  </div>
                </div>

                {/* Grid: Condition breakdown & Progress */}
                <div className="eval-charts-grid">
                  {/* Left: Per-Condition Accuracy */}
                  <div className="ui-card">
                    <div className="card-title-row">
                      <h3 className="card-title">
                        <BarChart3 size={18} style={{ color: 'var(--primary)' }} />
                        Accuracy by Real-World Condition
                      </h3>
                      <div style={{ display: 'flex', gap: '1rem', fontSize: '0.75rem' }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <span style={{ width: 8, height: 8, borderRadius: 2, background: '#d97706' }}></span>
                          Top-1
                        </span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <span style={{ width: 8, height: 8, borderRadius: 2, background: '#2563eb' }}></span>
                          Top-5
                        </span>
                      </div>
                    </div>

                    <div className="condition-list">
                      {Object.entries(evalMetrics.per_condition || {})
                        .sort((a, b) => b[1].top1_accuracy - a[1].top1_accuracy)
                        .map(([cond, vals]) => {
                          const t1 = (vals.top1_accuracy * 100).toFixed(0);
                          const t5 = (vals.top5_accuracy * 100).toFixed(0);
                          return (
                            <div key={cond} className="condition-row">
                              <span className="cond-name">{cond.replace(/_/g, ' ')}</span>
                              <div className="cond-bar-wrap">
                                <div className="cond-bar-track">
                                  <div className="cond-fill-top1" style={{ width: `${t1}%` }} />
                                </div>
                                <div className="cond-bar-track">
                                  <div className="cond-fill-top5" style={{ width: `${t5}%` }} />
                                </div>
                              </div>
                              <span className="cond-score-num top1">{t1}%</span>
                              <span className="cond-score-num top5">{t5}%</span>
                            </div>
                          );
                        })}
                    </div>
                  </div>

                  {/* Right: Dataset Milestone & Verdict Ratio */}
                  <div className="ui-card">
                    <div className="card-title-row">
                      <h3 className="card-title">
                        <Database size={18} style={{ color: 'var(--primary)' }} />
                        Stumper Dataset Progress
                      </h3>
                      <span className="brand-badge">
                        {evalMetrics.dataset_progress?.current || 39} / 100
                      </span>
                    </div>

                    <div className="progress-card-content">
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.85rem' }}>
                          <span style={{ color: 'var(--text-secondary)' }}>Collected Test Images</span>
                          <strong style={{ fontFamily: 'var(--font-mono)' }}>
                            {evalMetrics.dataset_progress?.pct || 39}%
                          </strong>
                        </div>
                        <div className="progress-track-lg">
                          <div
                            className="progress-fill-lg"
                            style={{ width: `${evalMetrics.dataset_progress?.pct || 39}%` }}
                          />
                        </div>
                      </div>

                      <div style={{
                        padding: '1rem',
                        background: 'var(--bg-surface-alt)',
                        borderRadius: '12px',
                        border: '1px solid var(--border)'
                      }}>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                          DECISION SPLIT (0.75 THRESHOLD)
                        </div>
                        <div style={{ display: 'flex', height: '10px', borderRadius: '5px', overflow: 'hidden', marginBottom: '0.5rem' }}>
                          <div
                            style={{
                              width: `${(evalMetrics.match_count / evalMetrics.total_images) * 100}%`,
                              background: '#059669'
                            }}
                          />
                          <div
                            style={{
                              width: `${(evalMetrics.unknown_count / evalMetrics.total_images) * 100}%`,
                              background: '#dc2626'
                            }}
                          />
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontFamily: 'var(--font-mono)' }}>
                          <span style={{ color: '#059669', fontWeight: 700 }}>
                            {evalMetrics.match_count} MATCH
                          </span>
                          <span style={{ color: '#dc2626', fontWeight: 700 }}>
                            {evalMetrics.unknown_count} UNKNOWN
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Prediction Results & Performance Breakdown (All Data Points) */}
                {(() => {
                  const allPoints = evalMetrics.all_results || evalMetrics.worst_failures || [];
                  const checkCorrect = (p) => p.decision === 'MATCH' && (p.top1_correct === 1 || p.ground_truth === p.top1_category);
                  const checkFA = (p) => p.decision === 'MATCH' && !checkCorrect(p);
                  const checkFR = (p) => p.decision === 'UNKNOWN';
                  const correctPoints = allPoints.filter(checkCorrect);
                  const faPoints = allPoints.filter(checkFA);
                  const frPoints = allPoints.filter(checkFR);
                  const wrongPoints = allPoints.filter(p => !checkCorrect(p));
                  const conditions = Array.from(new Set(allPoints.map(p => p.failure_condition))).filter(Boolean).sort();

                  let displayedPoints = allPoints;
                  if (evalFilter === 'correct') displayedPoints = correctPoints;
                  if (evalFilter === 'wrong') displayedPoints = wrongPoints;
                  if (evalFilter === 'fa') displayedPoints = faPoints;
                  if (evalFilter === 'fr') displayedPoints = frPoints;

                  if (evalConditionFilter !== 'all') {
                    displayedPoints = displayedPoints.filter(p => p.failure_condition === evalConditionFilter);
                  }

                  if (evalSearchText.trim()) {
                    const q = evalSearchText.toLowerCase();
                    displayedPoints = displayedPoints.filter(p =>
                      p.image_id.toLowerCase().includes(q) ||
                      p.ground_truth.toLowerCase().includes(q) ||
                      (p.top1_category && p.top1_category.toLowerCase().includes(q)) ||
                      (p.failure_condition && p.failure_condition.toLowerCase().includes(q))
                    );
                  }

                  return (
                    <div className="ui-card">
                      <div className="card-title-row">
                        <h3 className="card-title">
                          <BarChart3 size={18} style={{ color: 'var(--primary)' }} />
                          Prediction Performance & Data Points ({displayedPoints.length} of {allPoints.length})
                        </h3>
                        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                            Hits: <strong style={{ color: 'var(--success)' }}>{correctPoints.length}</strong> | FA: <strong style={{ color: 'var(--danger)' }}>{faPoints.length}</strong> | FR: <strong style={{ color: '#d97706' }}>{frPoints.length}</strong>
                          </span>
                        </div>
                      </div>

                      {/* Filter Controls Bar */}
                      <div className="table-filter-bar">
                        <div className="table-filter-tabs">
                          <button
                            className={`filter-tab-btn ${evalFilter === 'all' ? 'active' : ''}`}
                            onClick={() => setEvalFilter('all')}
                          >
                            All ({allPoints.length})
                          </button>
                          <button
                            className={`filter-tab-btn filter-correct ${evalFilter === 'correct' ? 'active' : ''}`}
                            onClick={() => setEvalFilter('correct')}
                          >
                            <CheckCircle2 size={14} style={{ color: 'var(--success)' }} />
                            Correct ({correctPoints.length})
                          </button>
                          <button
                            className={`filter-tab-btn filter-wrong ${evalFilter === 'fa' ? 'active' : ''}`}
                            onClick={() => setEvalFilter('fa')}
                            title="False Acceptance: system accepted match with wrong product"
                          >
                            <X size={14} style={{ color: 'var(--danger)' }} />
                            False Acc ({faPoints.length})
                          </button>
                          <button
                            className={`filter-tab-btn ${evalFilter === 'fr' ? 'active' : ''}`}
                            onClick={() => setEvalFilter('fr')}
                            style={evalFilter === 'fr' ? { borderColor: '#d97706', color: '#d97706' } : {}}
                            title="False Rejection: genuine catalogue item rejected as UNKNOWN"
                          >
                            <AlertCircle size={14} style={{ color: '#d97706' }} />
                            False Rej ({frPoints.length})
                          </button>
                        </div>

                        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
                          <div className="filter-search-box">
                            <Search size={14} style={{ color: 'var(--text-muted)' }} />
                            <input
                              type="text"
                              placeholder="Search ID, category..."
                              value={evalSearchText}
                              onChange={(e) => setEvalSearchText(e.target.value)}
                              className="filter-search-input"
                            />
                            {evalSearchText && (
                              <button
                                onClick={() => setEvalSearchText('')}
                                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex' }}
                              >
                                <X size={12} />
                              </button>
                            )}
                          </div>

                          <select
                            value={evalConditionFilter}
                            onChange={(e) => setEvalConditionFilter(e.target.value)}
                            className="filter-select"
                          >
                            <option value="all">All Conditions ({conditions.length})</option>
                            {conditions.map((c) => (
                              <option key={c} value={c}>
                                {c.replace(/_/g, ' ')}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>

                      {/* Table */}
                      <div className="failures-table-wrap">
                        <table className="failures-table">
                          <thead>
                            <tr>
                              <th>Preview</th>
                              <th>Image ID</th>
                              <th>Outcome</th>
                              <th>Ground Truth</th>
                              <th>Top-1 Prediction</th>
                              <th>Similarity</th>
                              <th>GT Rank</th>
                              <th>Condition</th>
                              <th>Verdict</th>
                            </tr>
                          </thead>
                          <tbody>
                            {displayedPoints.length > 0 ? (
                              displayedPoints.map((row) => {
                                const isCorrect = checkCorrect(row);
                                const isFA = checkFA(row);
                                const rankDisplay = row.gt_rank === 1
                                  ? <span className="rank-badge-top1">#1 (Top-1)</span>
                                  : row.gt_rank > 1
                                  ? <span className="rank-badge-top5">#{row.gt_rank} (Top-5)</span>
                                  : <span className="rank-badge-miss">Not in Top-5</span>;

                                return (
                                  <tr key={row.image_id} className={isCorrect ? 'row-correct' : isFA ? 'row-wrong' : 'row-unknown'}>
                                    <td>
                                      <img
                                        src={`/evaluation/images/${row.image_id}.jpeg`}
                                        alt={row.image_id}
                                        className="fail-thumb"
                                        onError={(e) => {
                                          e.target.style.display = 'none';
                                        }}
                                      />
                                    </td>
                                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-main)' }}>
                                      {row.image_id}
                                    </td>
                                    <td>
                                      {isCorrect ? (
                                        <span className="badge-correct">
                                          <Check size={12} />
                                          CORRECT
                                        </span>
                                      ) : isFA ? (
                                        <span className="badge-wrong" title="False Acceptance: Accepted wrong product">
                                          <X size={12} />
                                          FALSE ACC.
                                        </span>
                                      ) : (
                                        <span className="badge-warning" style={{ background: 'rgba(217, 119, 6, 0.1)', color: '#d97706', border: '1px solid rgba(217, 119, 6, 0.25)', padding: '2px 8px', borderRadius: '12px', fontSize: '0.75rem', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px' }} title="False Rejection: Rejected as UNKNOWN">
                                          <AlertCircle size={12} />
                                          FALSE REJ.
                                        </span>
                                      )}
                                    </td>
                                    <td>
                                      <span className="tag-badge" style={{ fontWeight: 700 }}>
                                        {row.ground_truth}
                                      </span>
                                    </td>
                                    <td>
                                      {isCorrect ? (
                                        <span className="prediction-match-chip">
                                          <span className="tag-badge" style={{ background: 'var(--success-bg)', color: 'var(--success)', borderColor: 'var(--success-border)' }}>
                                            {row.top1_category}
                                          </span>
                                        </span>
                                      ) : (
                                        <span className="prediction-mismatch-chip">
                                          <span className="tag-badge" style={{ background: 'var(--danger-bg)', color: 'var(--danger)', borderColor: 'var(--danger-border)' }}>
                                            {row.top1_category || '—'}
                                          </span>
                                        </span>
                                      )}
                                    </td>
                                    <td>
                                      <span style={{
                                        fontFamily: 'var(--font-mono)',
                                        fontWeight: 700,
                                        color: row.top1_similarity >= 0.75 ? 'var(--success)' : 'var(--danger)'
                                      }}>
                                        {row.top1_similarity.toFixed(4)}
                                      </span>
                                    </td>
                                    <td>{rankDisplay}</td>
                                    <td>
                                      <span className="tag-badge">
                                        {row.failure_condition?.replace(/_/g, ' ')}
                                      </span>
                                    </td>
                                    <td>
                                      <span
                                        style={{
                                          fontSize: '0.75rem',
                                          fontWeight: 700,
                                          padding: '2px 8px',
                                          borderRadius: '6px',
                                          background: row.decision === 'MATCH' ? 'var(--success-bg)' : 'var(--danger-bg)',
                                          color: row.decision === 'MATCH' ? 'var(--success)' : 'var(--danger)'
                                        }}
                                      >
                                        {row.decision}
                                      </span>
                                    </td>
                                  </tr>
                                );
                              })
                            ) : (
                              <tr>
                                <td colSpan={9} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-muted)' }}>
                                  No matching data points found for this filter.
                                </td>
                              </tr>
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  );
                })()}
              </div>
            ) : (
              <div className="ui-card" style={{ textAlign: 'center', padding: '4rem 2rem' }}>
                <div className="empty-icon-box" style={{ margin: '0 auto 1rem auto' }}>
                  <BarChart3 size={32} />
                </div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '0.5rem' }}>
                  Arena Results Pending
                </h3>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', maxWidth: '400px', margin: '0 auto 1.5rem auto' }}>
                  Click below to evaluate CLIP ViT-B/32 against all 39 real-world stumper test cases.
                </p>
                <button
                  className="btn-primary"
                  style={{ width: 'auto', display: 'inline-flex' }}
                  onClick={triggerEvaluation}
                  disabled={isEvaluating}
                >
                  {isEvaluating ? (
                    <>
                      <RotateCw size={16} className="spin-anim" />
                      Evaluating...
                    </>
                  ) : (
                    <>
                      <Play size={16} />
                      Run Evaluation Now
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        )}

        {/* VIEW 2: COLLECT DATA */}
        {(activeTab === 'collect' || activeTab === 'add') && (
          <CollectDataTab
            selectedProduct={collectProduct}
            onProductSelected={setCollectProduct}
            onTestInSearch={handleTestProductInSearch}
            onStatsRefresh={fetchStats}
          />
        )}

        {/* VIEW 3: COLLECTIONS */}
        {activeTab === 'collections' && (
          <CollectionsTab
            onSelectProduct={(prod) => {
              setCollectProduct(prod);
              setActiveTab('collect');
            }}
            onTestInSearch={handleTestProductInSearch}
          />
        )}

        {/* VIEW 4: DATASET STATS */}
        {activeTab === 'dataset' && (
          <DatasetTab
            onSelectProductFromPhoto={(prod) => {
              setCollectProduct(prod);
              setActiveTab('collect');
            }}
          />
        )}
      </main>
    </div>
  );
}
