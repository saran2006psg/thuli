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
import AutomatedStumperTab from './components/AutomatedStumperTab';

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
  const [multiResults, setMultiResults] = useState(null);
  const [searchMode, setSearchMode] = useState('single'); // 'single' | 'multi'
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
      setMultiResults(null);
    };
    reader.readAsDataURL(file);
  };

  const handleClearImage = () => {
    setSearchImage(null);
    setSearchFile(null);
    setSearchResults(null);
    setMultiResults(null);
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

    const isMulti = searchMode === 'multi';
    if (isMulti) {
      formData.append('rows', '2');
      formData.append('cols', '2');
      formData.append('overlap', '0.18');
    }

    const endpoint = isMulti ? '/api/match/multi' : '/api/match';
    try {
      const res = await fetch(endpoint, { method: 'POST', body: formData });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Visual search failed.');
      }
      const data = await res.json();
      if (isMulti) {
        setMultiResults(data);
        setSearchResults(null);
      } else {
        setSearchResults(data);
        setMultiResults(null);
      }
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

  const [evalProgress, setEvalProgress] = useState(null); // { progress, total }
  const [evalToast, setEvalToast] = useState(null); // success toast message

  const triggerEvaluation = async () => {
    if (isEvaluating) return;
    setIsEvaluating(true);
    setEvalProgress({ progress: 0, total: 115 }); // show immediately

    try {
      // 1. Snapshot current last_completed_at so we know when a NEW run finishes
      let prevCompletedAt = null;
      try {
        const snap = await fetch('/api/evaluation/status');
        if (snap.ok) {
          const s = await snap.json();
          prevCompletedAt = s.last_completed_at;
        }
      } catch (_) {}

      // 2. Start the background job
      const startRes = await fetch('/api/evaluation/run', { method: 'POST' });
      if (!startRes.ok) {
        const err = await startRes.json().catch(() => ({ detail: startRes.statusText }));
        throw new Error(err.detail || 'Failed to start evaluation.');
      }

      // 3. Poll until last_completed_at changes (new run finished) — timeout 120s
      const deadline = Date.now() + 120_000;
      await new Promise((resolve, reject) => {
        let seenRunning = false;
        const poll = setInterval(async () => {
          if (Date.now() > deadline) {
            clearInterval(poll);
            reject(new Error('Evaluation timed out after 120s.'));
            return;
          }
          try {
            const statusRes = await fetch('/api/evaluation/status');
            if (!statusRes.ok) return;
            const s = await statusRes.json();

            // Update progress bar
            if (s.total > 0) setEvalProgress({ progress: s.progress, total: s.total });
            if (s.running) seenRunning = true;
            if (s.error) { clearInterval(poll); reject(new Error(s.error)); return; }

            // Done when: (A) last_completed_at changed from snapshot, OR
            //            (B) we saw it running and now it stopped
            const newRun = s.last_completed_at && s.last_completed_at !== prevCompletedAt;
            const ranAndStopped = seenRunning && !s.running;
            if (newRun || ranAndStopped) {
              clearInterval(poll);
              resolve();
            }
          } catch (_) {}
        }, 800);
      });

      // 4. Fetch the final results
      const resultRes = await fetch('/api/evaluation/results');
      if (resultRes.ok) {
        const data = await resultRes.json();
        setEvalMetrics(data.metrics);
        const acc = (data.metrics.top1_accuracy * 100).toFixed(1);
        const n = data.metrics.total_images;
        setEvalToast(`✅ Evaluation complete — ${n} images · Top-1: ${acc}%`);
        setTimeout(() => setEvalToast(null), 5000);
      }
    } catch (err) {
      alert('Evaluation error: ' + err.message);
    } finally {
      setIsEvaluating(false);
      setEvalProgress(null);
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
            <button
              className={`nav-tab-btn ${activeTab === 'automated-stumper' ? 'active' : ''}`}
              onClick={() => setActiveTab('automated-stumper')}
            >
              <Sparkles size={16} />
              <span>Automated Stumper</span>
              <span style={{
                fontSize: '0.65rem',
                background: '#7c3aed20',
                color: '#7c3aed',
                padding: '1px 6px',
                borderRadius: '999px',
                fontFamily: 'var(--font-mono)',
                fontWeight: 700
              }}>
                900
              </span>
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

              {/* ── Search Mode Toggle ── */}
              <div style={{
                display: 'flex',
                gap: '0.5rem',
                marginBottom: '1rem',
                padding: '4px',
                background: 'var(--bg-surface-alt)',
                borderRadius: '10px',
                border: '1px solid var(--border)',
              }}>
                {[['single', '🔍 Single Item'], ['multi', '🪬 Multiple Items']].map(([val, label]) => (
                  <button
                    key={val}
                    onClick={() => { setSearchMode(val); setSearchResults(null); setMultiResults(null); }}
                    style={{
                      flex: 1,
                      padding: '6px 12px',
                      borderRadius: '7px',
                      border: 'none',
                      cursor: 'pointer',
                      fontSize: '0.8rem',
                      fontWeight: 600,
                      transition: 'all 0.15s ease',
                      background: searchMode === val ? 'var(--primary)' : 'transparent',
                      color: searchMode === val ? '#fff' : 'var(--text-secondary)',
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
              {searchMode === 'multi' && (
                <div style={{
                  fontSize: '0.75rem',
                  color: 'var(--text-muted)',
                  background: 'var(--bg-surface-alt)',
                  borderRadius: '8px',
                  padding: '8px 12px',
                  marginBottom: '1rem',
                  border: '1px solid var(--border)',
                  lineHeight: 1.5,
                }}>
                  ✨ Uses <strong>Segment Anything (SAM)</strong> to automatically detect and segment each individual jewellery item in the photograph.
                  Each piece is verified and matched independently against the catalogue using CLIP + FAISS.
                </div>
              )}


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
                  {searchMode === 'multi' ? 'Identified Jewellery Items' : 'Retrieval Candidates'}
                </h2>
                {(searchResults || multiResults) && (
                  <span style={{
                    fontSize: '0.8rem',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-muted)'
                  }}>
                    {(searchResults || multiResults).query_time_ms} ms
                  </span>
                )}
              </div>

              {/* ── SINGLE-ITEM RESULTS ── */}
              {searchMode === 'single' && searchResults ? (
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
                            onError={(e) => { e.target.style.display = 'none'; }}
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
                              <div className="score-bar-fill" style={{ width: `${simPct}%` }} />
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

              /* ── MULTI-ITEM RESULTS ── */
              ) : searchMode === 'multi' && multiResults ? (
                <div>
                  {/* ── Summary Banner ── */}
                  <div className={`verdict-banner ${multiResults.matched_count > 0 ? 'match' : 'unknown'}`}
                    style={{
                      background: multiResults.matched_count > 0
                        ? 'linear-gradient(135deg, rgba(5,150,105,0.12) 0%, rgba(16,185,129,0.05) 100%)'
                        : 'var(--bg-surface-alt)',
                      borderColor: multiResults.matched_count > 0 ? '#059669' : 'var(--border)',
                    }}
                  >
                    <div className="verdict-left">
                      <span className="verdict-badge" style={{
                        background: multiResults.matched_count > 0 ? '#059669' : '#64748b',
                        fontSize: '0.75rem', minWidth: 80, textAlign: 'center',
                      }}>
                        {multiResults.matched_count > 0 ? `${multiResults.matched_count} FOUND` : 'NO MATCH'}
                      </span>
                      <div>
                        <div className="verdict-text-main">
                          {multiResults.matched_count > 0
                            ? multiResults.matches.map(m => m.product_name).join(' · ')
                            : 'No products identified — all regions below threshold'}
                        </div>
                        <div className="verdict-text-sub">
                          {multiResults.total_crops} detected items · Segment Anything (SAM) · {multiResults.query_time_ms}ms
                        </div>
                      </div>
                    </div>
                    <div className="verdict-metrics">
                      <div className="verdict-metric-item">
                        <div className="verdict-metric-label">Detected</div>
                        <div className="verdict-metric-value">{multiResults.total_crops}</div>
                      </div>
                      <div className="verdict-metric-item">
                        <div className="verdict-metric-label">Found</div>
                        <div className="verdict-metric-value" style={{ color: multiResults.matched_count > 0 ? '#059669' : 'inherit' }}>
                          {multiResults.matched_count}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* ── Matched Products (PRIMARY output) ── */}
                  {multiResults.matches.length > 0 ? (
                    <div style={{ marginBottom: '1.25rem' }}>
                      <div style={{
                        fontSize: '0.72rem', fontWeight: 800, textTransform: 'uppercase',
                        letterSpacing: '0.08em', color: 'var(--text-muted)', marginBottom: '0.6rem',
                        display: 'flex', alignItems: 'center', gap: '0.4rem',
                      }}>
                        <span style={{
                          display: 'inline-block', width: 8, height: 8,
                          borderRadius: '50%', background: '#059669',
                        }} />
                        Identified Items ({multiResults.matched_count})
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                        {multiResults.matches.map((item) => {
                          const simPct = (Math.max(0, Math.min(1, item.similarity)) * 100).toFixed(1);
                          const imgUrl = item.image_url || (item.image_path ? `/${item.image_path}` : null);
                          return (
                            <div key={item.product_id} style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.85rem',
                              padding: '0.85rem 1rem',
                              borderRadius: '12px',
                              border: `2px solid ${item.rank === 1 ? '#059669' : 'var(--border)'}`,
                              background: item.rank === 1
                                ? 'linear-gradient(135deg, rgba(5,150,105,0.08) 0%, rgba(16,185,129,0.03) 100%)'
                                : 'var(--bg-surface-alt)',
                              transition: 'transform 0.15s ease, box-shadow 0.15s ease',
                            }}>
                              {/* Rank badge */}
                              <div style={{
                                width: 32, height: 32, borderRadius: '50%', flexShrink: 0,
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                background: item.rank === 1 ? '#059669' : 'var(--text-muted)',
                                color: '#fff', fontSize: '0.8rem', fontWeight: 800,
                              }}>
                                #{item.rank}
                              </div>

                              {/* Thumbnail */}
                              {imgUrl ? (
                                <img
                                  src={imgUrl}
                                  alt={item.product_name}
                                  style={{
                                    width: 64, height: 64, objectFit: 'contain',
                                    borderRadius: '8px', flexShrink: 0,
                                    border: '1px solid var(--border)',
                                    background: '#fff',
                                  }}
                                  onError={(e) => { e.target.style.display = 'none'; }}
                                />
                              ) : (
                                <div style={{
                                  width: 64, height: 64, borderRadius: '8px',
                                  background: 'var(--border)', flexShrink: 0,
                                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                                  fontSize: '1.5rem',
                                }}>💎</div>
                              )}

                              {/* Info */}
                              <div style={{ flex: 1, minWidth: 0 }}>
                                <div style={{
                                  fontWeight: 700, fontSize: '0.95rem',
                                  color: 'var(--text-main)', marginBottom: '3px',
                                  whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                                }}>
                                  {item.product_name}
                                </div>
                                <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginBottom: '6px' }}>
                                  <span style={{
                                    padding: '2px 8px', borderRadius: '999px', fontSize: '0.7rem',
                                    background: 'var(--primary-light)', color: 'var(--primary)', fontWeight: 600,
                                  }}>
                                    {item.category}
                                  </span>
                                  <span style={{
                                    padding: '2px 8px', borderRadius: '999px', fontSize: '0.7rem',
                                    background: 'var(--bg-surface-alt)', color: 'var(--text-muted)',
                                    fontFamily: 'var(--font-mono)',
                                  }}>
                                    {item.product_id}
                                  </span>
                                  <span style={{
                                    padding: '2px 8px', borderRadius: '999px', fontSize: '0.7rem',
                                    background: 'rgba(5,150,105,0.1)', color: '#059669', fontWeight: 600,
                                  }}>
                                    from segment {item.source_crop_id}
                                  </span>
                                </div>
                                {/* Similarity bar */}
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                  <div style={{
                                    flex: 1, height: 6, borderRadius: 999,
                                    background: 'var(--border)', overflow: 'hidden',
                                  }}>
                                    <div style={{
                                      height: '100%', borderRadius: 999,
                                      width: `${simPct}%`,
                                      background: parseFloat(simPct) >= 85
                                        ? '#059669'
                                        : parseFloat(simPct) >= 75
                                        ? '#d97706'
                                        : '#ef4444',
                                      transition: 'width 0.4s ease',
                                    }} />
                                  </div>
                                  <span style={{
                                    fontWeight: 800, fontSize: '0.9rem', minWidth: 46, textAlign: 'right',
                                    color: parseFloat(simPct) >= 85 ? '#059669' : parseFloat(simPct) >= 75 ? '#d97706' : '#ef4444',
                                  }}>
                                    {simPct}%
                                  </span>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ) : (
                    <div style={{
                      textAlign: 'center', padding: '2rem',
                      color: 'var(--text-muted)', fontSize: '0.85rem',
                    }}>
                      No items matched the similarity threshold ({threshold.toFixed(2)}).<br />
                      Try lowering the threshold slider.
                    </div>
                  )}

                  {/* ── Region breakdown (secondary, compact) ── */}
                  <details style={{ marginTop: '0.5rem' }}>
                    <summary style={{
                      cursor: 'pointer', fontSize: '0.72rem', fontWeight: 700,
                      textTransform: 'uppercase', letterSpacing: '0.08em',
                      color: 'var(--text-muted)', userSelect: 'none',
                      listStyle: 'none', display: 'flex', alignItems: 'center', gap: '0.4rem',
                      padding: '6px 0', borderTop: '1px solid var(--border)',
                    }}>
                      <span style={{ fontSize: '0.65rem' }}>▶</span>
                      SAM Segments Breakdown ({multiResults.total_crops} items detected)
                    </summary>
                    <div style={{
                      display: 'grid', gridTemplateColumns: '1fr 1fr',
                      gap: '0.4rem', marginTop: '0.6rem',
                    }}>
                      {multiResults.crop_results.map((cr) => {
                        const matchedItem = multiResults.matches.find(m => m.product_id === cr.product_id);
                        const imgUrl = matchedItem?.image_url || (matchedItem?.image_path ? `/${matchedItem.image_path}` : null);
                        return (
                          <div key={cr.crop_id} style={{
                            padding: '0.55rem 0.7rem',
                            borderRadius: '8px',
                            border: `1px solid ${cr.decision === 'MATCH' ? '#059669' : 'var(--border)'}`,
                            background: cr.decision === 'MATCH' ? 'rgba(5,150,105,0.05)' : 'var(--bg-surface-alt)',
                            fontSize: '0.72rem',
                            display: 'flex', gap: '0.5rem', alignItems: 'center',
                          }}>
                            {/* Tiny thumbnail for matched crop */}
                            {cr.decision === 'MATCH' && imgUrl && (
                              <img
                                src={imgUrl}
                                alt=""
                                style={{
                                  width: 32, height: 32, objectFit: 'contain',
                                  borderRadius: '5px', border: '1px solid var(--border)',
                                  background: '#fff', flexShrink: 0,
                                }}
                                onError={(e) => { e.target.style.display = 'none'; }}
                              />
                            )}
                            {cr.decision === 'UNKNOWN' && (
                              <div style={{
                                width: 32, height: 32, borderRadius: '5px',
                                background: 'var(--border)', flexShrink: 0,
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                fontSize: '0.9rem', opacity: 0.5,
                              }}>?</div>
                            )}
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1px' }}>
                                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-main)' }}>
                                  {cr.crop_id}
                                </span>
                                <span style={{
                                  padding: '1px 6px', borderRadius: '5px', fontSize: '0.65rem', fontWeight: 700,
                                  background: cr.decision === 'MATCH' ? '#059669' : '#64748b', color: '#fff',
                                }}>
                                  {cr.decision}
                                </span>
                              </div>
                              {cr.decision === 'MATCH' ? (
                                <div style={{
                                  color: 'var(--text-secondary)', whiteSpace: 'nowrap',
                                  overflow: 'hidden', textOverflow: 'ellipsis',
                                }}>
                                  {matchedItem?.product_name || cr.product_id}
                                  <span style={{ color: '#059669', fontWeight: 700, marginLeft: 4 }}>
                                    {(cr.similarity * 100).toFixed(1)}%
                                  </span>
                                </div>
                              ) : (
                                <div style={{ color: 'var(--text-muted)' }}>
                                  {(cr.similarity * 100).toFixed(1)}% — below threshold
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </details>
                </div>


              ) : (
                <div className="empty-placeholder">
                  <div className="empty-icon-box">
                    <Search size={32} />
                  </div>
                  <div className="empty-title">No Active Query</div>
                  <div className="empty-desc">
                    {searchMode === 'multi'
                      ? 'Upload a photo containing 2–3 jewellery items to identify each product separately.'
                      : 'Upload a jewellery photo or pick one of the catalogue samples to view matching items.'}
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
                  Scanning <strong>{evalMetrics?.total_images || 115}</strong> images from <code>evaluation/images/</code> through CLIP ViT-B/32 + FAISS.
                  {evalMetrics?.scored_images !== undefined && (
                    <> Ground-truth labels available for <strong>{evalMetrics.scored_images}</strong> images (accuracy computed on labelled set only).</>
                  )}
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
                      {evalProgress
                        ? `${evalProgress.progress}/${evalProgress.total} images…`
                        : 'Starting…'}
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

            {/* Progress bar while evaluating */}
            {isEvaluating && evalProgress && (
              <div style={{
                background: 'var(--bg-surface)',
                border: '1px solid var(--primary)',
                borderRadius: '10px',
                padding: '0.75rem 1rem',
                marginBottom: '1rem',
                display: 'flex',
                alignItems: 'center',
                gap: '1rem',
              }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--primary)', marginBottom: 6 }}>
                    Running evaluation — {evalProgress.total > 0 ? `${evalProgress.progress} / ${evalProgress.total} images processed` : 'Starting…'}
                  </div>
                  <div style={{ height: 8, borderRadius: 999, background: 'var(--border)', overflow: 'hidden' }}>
                    <div style={{
                      height: '100%',
                      borderRadius: 999,
                      background: 'var(--primary)',
                      width: evalProgress.total > 0 ? `${Math.round((evalProgress.progress / evalProgress.total) * 100)}%` : '5%',
                      transition: 'width 0.5s ease',
                    }} />
                  </div>
                </div>
                <span style={{ fontSize: '0.85rem', fontWeight: 800, fontFamily: 'var(--font-mono)', minWidth: 60, textAlign: 'right', color: 'var(--primary)' }}>
                  {evalProgress.total > 0 ? `${Math.round((evalProgress.progress / evalProgress.total) * 100)}%` : '…'}
                </span>
              </div>
            )}

            {/* Success toast */}
            {evalToast && (
              <div style={{
                background: 'rgba(5,150,105,0.1)',
                border: '1px solid #059669',
                borderRadius: '10px',
                padding: '0.75rem 1rem',
                marginBottom: '1rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: '0.875rem',
                fontWeight: 600,
                color: '#059669',
              }}>
                <span>{evalToast}</span>
                <button onClick={() => setEvalToast(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#059669', fontSize: '1.1rem', lineHeight: 1 }}>×</button>
              </div>
            )}

            {/* Dashboard Content */}
            {evalMetrics ? (
              <div>
                {/* KPI Cards */}
                <div className="kpi-grid">
                  <div className="kpi-card teal" style={{ gridColumn: 'span 2' }}>
                    <div className="kpi-label">Images Scanned</div>
                    <div className="kpi-value">{evalMetrics.total_images}</div>
                    <div className="kpi-sub">
                      {evalMetrics.scored_images !== undefined
                        ? `${evalMetrics.scored_images} labelled · ${evalMetrics.skipped_images ?? 0} skipped`
                        : 'from evaluation/images/'}
                    </div>
                  </div>

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
                                        src={`/evaluation/images/${row.image_filename || (row.image_id + '.jpeg')}?t=${evalMetrics?.run_at || Date.now()}`}
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

        {/* VIEW 5: AUTOMATED STUMPER */}
        {activeTab === 'automated-stumper' && (
          <AutomatedStumperTab />
        )}
      </main>
    </div>
  );
}
