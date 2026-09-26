import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  BarChart3,
  RotateCw,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Clock,
  Layers,
  ArrowRight,
  TrendingUp,
  TrendingDown,
  Filter,
  Eye,
  Download,
  ShieldAlert,
  Sliders,
  Check,
  X
} from 'lucide-react';

export default function AutomatedStumperTab() {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [selectedCondition, setSelectedCondition] = useState('all');
  const [selectedFailureType, setSelectedFailureType] = useState('all'); // 'all' | 'unknown' | 'wrong_match'
  const [inspectModalItem, setInspectModalItem] = useState(null);

  const fetchResults = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/automated-stumper/results');
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch (err) {
      console.warn('Could not load automated stumper results:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
  }, []);

  const handleRunEvaluation = async () => {
    if (isRunning) return;
    setIsRunning(true);
    try {
      const res = await fetch('/api/automated-stumper/run', { method: 'POST' });
      if (res.ok) {
        const json = await res.json();
        setData(json);
      } else {
        alert('Evaluation failed. Check server logs.');
      }
    } catch (err) {
      alert('Error triggering evaluation: ' + err.message);
    } finally {
      setIsRunning(false);
    }
  };

  if (isLoading && !data) {
    return (
      <div style={{ textAlign: 'center', padding: '6rem 2rem', color: 'var(--text-muted)' }}>
        <RotateCw size={40} className="spin-anim" style={{ marginBottom: '1.25rem', color: 'var(--primary)' }} />
        <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-main)' }}>
          Loading Automated Stumper Benchmarks...
        </div>
        <p style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>
          Retrieving 900 synthetic test images and comparison metrics.
        </p>
      </div>
    );
  }

  const metrics = data?.metrics || {};
  const comparison = data?.comparison || {};
  const handshot = comparison.handshot || {};
  const automated = comparison.automated || {};
  const delta = comparison.delta || {};
  const perCondition = metrics.per_condition || {};
  const failedExamples = metrics.failed_examples || [];

  // Filter failed examples
  const filteredFailures = failedExamples.filter((item) => {
    if (selectedCondition !== 'all' && item.failure_condition !== selectedCondition) {
      return false;
    }
    if (selectedFailureType === 'unknown' && item.decision !== 'UNKNOWN') {
      return false;
    }
    if (selectedFailureType === 'wrong_match' && (item.decision === 'UNKNOWN' || item.top1_category_correct === 1)) {
      return false;
    }
    return true;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', paddingBottom: '3rem' }}>
      {/* ── Header & Action Bar ── */}
      <div className="eval-header-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{ fontSize: '1.25rem' }}>⚡</span>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 700, margin: 0, color: 'var(--text-main)' }}>
              Automated Stumper Benchmark
            </h2>
            <span className="brand-badge" style={{ background: '#7c3aed18', color: '#7c3aed', borderColor: '#7c3aed40' }}>
              100 Source Items × 9 Conditions = 900 Tests
            </span>
          </div>
          <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)', maxWidth: '750px' }}>
            Stress-tests the production matcher against 9 realistic physical and environmental variations
            (lighting, odd angles, occlusions, clutter, motion blur, reflection, distance, and noise)
            generated with Python, PIL, and OpenCV without changing any matcher logic.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <a
            href="/api/automated-stumper/download"
            className="btn-secondary"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              borderRadius: '8px',
              border: '1px solid var(--border)',
              background: 'var(--bg-surface)',
              color: 'var(--text-main)',
              fontSize: '0.85rem',
              fontWeight: 600,
              textDecoration: 'none',
              cursor: 'pointer'
            }}
          >
            <Download size={15} />
            Export CSV
          </a>

          <button
            className="btn-primary"
            onClick={handleRunEvaluation}
            disabled={isRunning}
            style={{ padding: '8px 18px', fontSize: '0.85rem' }}
          >
            {isRunning ? (
              <>
                <RotateCw size={15} className="spin-anim" />
                Evaluating 900 Images...
              </>
            ) : (
              <>
                <RotateCw size={15} />
                Re-Run Stumper
              </>
            )}
          </button>
        </div>
      </div>

      {/* ── High-Level Metric Tiles ── */}
      <div className="eval-kpi-grid">
        <div className="kpi-card gold">
          <div className="kpi-label">Source Items</div>
          <div className="kpi-value">{metrics.source_images_count || 100}</div>
          <div className="kpi-sub">Catalogue sampled seeds</div>
        </div>

        <div className="kpi-card blue">
          <div className="kpi-label">Generated Tests</div>
          <div className="kpi-value">{metrics.total_images || 900}</div>
          <div className="kpi-sub">9 realistic variations/item</div>
        </div>

        <div className="kpi-card purple">
          <div className="kpi-label">Top-1 Category Acc</div>
          <div className="kpi-value">
            {((metrics.top1_accuracy || 0) * 100).toFixed(1)}%
          </div>
          <div className="kpi-sub">
            {metrics.top1_correct_count ?? 0} / {metrics.total_images ?? 900} correct
          </div>
        </div>

        <div className="kpi-card cyan">
          <div className="kpi-label">Top-5 Category Acc</div>
          <div className="kpi-value">
            {((metrics.top5_accuracy || 0) * 100).toFixed(1)}%
          </div>
          <div className="kpi-sub">
            {metrics.top5_correct_count ?? 0} in Top 5 candidates
          </div>
        </div>

        <div className="kpi-card red">
          <div className="kpi-label">Total Failure Rate</div>
          <div className="kpi-value">
            {((metrics.failure_rate || 0) * 100).toFixed(1)}%
          </div>
          <div className="kpi-sub">
            Wrong ({metrics.wrong_matches_count ?? 0}) + UNKNOWN ({metrics.unknown_count ?? 0})
          </div>
        </div>

        <div className="kpi-card amber">
          <div className="kpi-label">P50 / P95 Latency</div>
          <div className="kpi-value">
            {metrics.median_latency_ms || 0}ms
          </div>
          <div className="kpi-sub">
            P95: {metrics.p95_latency_ms || 0}ms per query
          </div>
        </div>
      </div>

      {/* ── HAND-SHOT vs AUTOMATED COMPARISON SECTION ── */}
      <div className="ui-card" style={{ padding: '1.5rem', border: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldAlert size={20} style={{ color: delta.defeated_higher ? '#dc2626' : '#059669' }} />
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, margin: 0 }}>
                HAND-SHOT vs AUTOMATED STUMPER COMPARISON
              </h3>
            </div>
            <p style={{ margin: '4px 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Core Hypothesis: Does automated realistic transformation defeat the matcher at a higher rate than hand-shot phone photos?
            </p>
          </div>

          <div
            style={{
              padding: '6px 14px',
              borderRadius: '20px',
              fontSize: '0.8rem',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: delta.defeated_higher ? '#fef2f2' : '#ecfdf5',
              color: delta.defeated_higher ? '#dc2626' : '#059669',
              border: `1px solid ${delta.defeated_higher ? '#fecaca' : '#a7f3d0'}`
            }}
          >
            {delta.defeated_higher ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
            {delta.defeated_higher
              ? `Defeats Matcher (+${delta.failure_rate_pct}% Failure Rate)`
              : `Matcher More Resilient (${delta.failure_rate_pct}% vs Hand-Shot)`}
          </div>
        </div>

        {/* Comparison Table */}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border)', background: 'var(--bg-surface-alt)' }}>
                <th style={{ padding: '10px 14px', fontWeight: 700, color: 'var(--text-secondary)' }}>Benchmark Dimension</th>
                <th style={{ padding: '10px 14px', fontWeight: 700, color: 'var(--text-secondary)' }}>
                  Hand-Shot Stumper (111 Photos)
                </th>
                <th style={{ padding: '10px 14px', fontWeight: 700, color: 'var(--primary)' }}>
                  Automated Stumper (900 Tests)
                </th>
                <th style={{ padding: '10px 14px', fontWeight: 700, color: 'var(--text-secondary)' }}>Delta / Shift</th>
                <th style={{ padding: '10px 14px', fontWeight: 700, color: 'var(--text-secondary)' }}>Analysis</th>
              </tr>
            </thead>
            <tbody>
              {/* Top-1 */}
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <td style={{ padding: '12px 14px', fontWeight: 600 }}>Top-1 Accuracy</td>
                <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                  {((handshot.top1_accuracy || 0) * 100).toFixed(2)}%
                </td>
                <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--primary)' }}>
                  {((automated.top1_accuracy || 0) * 100).toFixed(2)}%
                </td>
                <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: delta.top1_pct >= 0 ? '#059669' : '#dc2626' }}>
                  {delta.top1_pct >= 0 ? `+${delta.top1_pct}%` : `${delta.top1_pct}%`}
                </td>
                <td style={{ padding: '12px 14px', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                  {delta.top1_pct < 0 ? 'Synthetic variations created more severe rank-1 drop' : 'Maintained stable category identification'}
                </td>
              </tr>

              {/* Top-5 */}
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <td style={{ padding: '12px 14px', fontWeight: 600 }}>Top-5 Accuracy</td>
                <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                  {((handshot.top5_accuracy || 0) * 100).toFixed(2)}%
                </td>
                <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--primary)' }}>
                  {((automated.top5_accuracy || 0) * 100).toFixed(2)}%
                </td>
                <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: delta.top5_pct >= 0 ? '#059669' : '#dc2626' }}>
                  {delta.top5_pct >= 0 ? `+${delta.top5_pct}%` : `${delta.top5_pct}%`}
                </td>
                <td style={{ padding: '12px 14px', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                  Candidate recall in nearest top-5 neighbours
                </td>
              </tr>

              {/* Failure Rate */}
              <tr style={{ borderBottom: '1px solid var(--border)', background: 'rgba(220, 38, 38, 0.03)' }}>
                <td style={{ padding: '12px 14px', fontWeight: 700, color: '#dc2626' }}>Overall Failure Rate</td>
                <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                  {((handshot.failure_rate || 0) * 100).toFixed(2)}%
                </td>
                <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#dc2626' }}>
                  {((automated.failure_rate || 0) * 100).toFixed(2)}%
                </td>
                <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: delta.failure_rate_pct > 0 ? '#dc2626' : '#059669' }}>
                  {delta.failure_rate_pct >= 0 ? `+${delta.failure_rate_pct}%` : `${delta.failure_rate_pct}%`}
                </td>
                <td style={{ padding: '12px 14px', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                  Total of incorrect match verdicts + sub-threshold UNKNOWN rejections
                </td>
              </tr>

              {/* UNKNOWN */}
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <td style={{ padding: '12px 14px', fontWeight: 600 }}>UNKNOWN Verdicts (&lt; 0.75)</td>
                <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)' }}>
                  {handshot.unknown_count ?? 8} ({((handshot.unknown_rate || 0.0721) * 100).toFixed(1)}%)
                </td>
                <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--primary)' }}>
                  {automated.unknown_count ?? 0} ({((automated.unknown_rate || 0) * 100).toFixed(1)}%)
                </td>
                <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)' }}>
                  {((automated.unknown_rate - handshot.unknown_rate) * 100).toFixed(1)}%
                </td>
                <td style={{ padding: '12px 14px', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                  Sub-threshold rejections where best candidate fell below 0.75
                </td>
              </tr>

              {/* Latency */}
              <tr>
                <td style={{ padding: '12px 14px', fontWeight: 600 }}>Inference Latency</td>
                <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)' }}>
                  P50: {handshot.median_latency_ms || 106.6}ms | P95: {handshot.p95_latency_ms || 136.7}ms
                </td>
                <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--primary)' }}>
                  P50: {automated.median_latency_ms || 0}ms | P95: {automated.p95_latency_ms || 0}ms
                </td>
                <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                  ±{(Math.abs((automated.median_latency_ms || 0) - (handshot.median_latency_ms || 0))).toFixed(1)}ms
                </td>
                <td style={{ padding: '12px 14px', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                  Fast & stable across both realistic synthetic and raw camera uploads
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Dual Label Verification Notice */}
        <div style={{ marginTop: '1.25rem', padding: '1rem', background: 'var(--bg-surface-alt)', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '0.8rem', lineHeight: 1.6 }}>
          <strong>💡 Dual Ground-Truth Analysis:</strong>
          <br />
          • <strong>Category Label Accuracy (Top-1: {((automated.top1_accuracy || 0) * 100).toFixed(1)}% | Top-5: {((automated.top5_accuracy || 0) * 100).toFixed(1)}%)</strong>: Directly comparable to the hand-shot benchmark.
          <br />
          • <strong>Exact SKU Product-ID Retrieval (Top-1: {((automated.top1_product_accuracy || 0) * 100).toFixed(1)}% | Top-5: {((automated.top5_product_accuracy || 0) * 100).toFixed(1)}%)</strong>: Evaluates whether the exact source catalogue item out of 6,189 items is identified under perturbation.
        </div>
      </div>

      {/* ── RESULTS BY FAILURE CONDITION ── */}
      <div className="ui-card" style={{ padding: '1.5rem', border: '1px solid var(--border)' }}>
        <div className="card-title-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <div>
            <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: 0, fontSize: '1.15rem' }}>
              <BarChart3 size={18} style={{ color: 'var(--primary)' }} />
              Accuracy & Resilience by Real-World Condition (100 Tests Each)
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Breakdown across the 9 simulated challenge modes.
            </span>
          </div>

          <div style={{ display: 'flex', gap: '1rem', fontSize: '0.75rem' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: '#d97706' }}></span>
              Top-1 Category
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: '#2563eb' }}></span>
              Top-5 Category
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: '#7c3aed' }}></span>
              Exact SKU Top-1
            </span>
          </div>
        </div>

        <div className="condition-list" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {Object.entries(perCondition)
            .sort((a, b) => b[1].top1_accuracy - a[1].top1_accuracy)
            .map(([cond, vals]) => {
              const t1 = (vals.top1_accuracy * 100).toFixed(0);
              const t5 = (vals.top5_accuracy * 100).toFixed(0);
              const prodT1 = (vals.top1_product_accuracy * 100).toFixed(0);
              const fails = vals.wrong_matches_count + vals.unknown_count;

              return (
                <div key={cond} style={{ display: 'grid', gridTemplateColumns: '150px 1fr 140px', alignItems: 'center', gap: '1rem' }}>
                  <div>
                    <span style={{ fontSize: '0.85rem', fontWeight: 600, textTransform: 'capitalize' }}>
                      {cond.replace(/_/g, ' ')}
                    </span>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      {fails} fails ({vals.unknown_count} UNKNOWN)
                    </div>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {/* Top-1 Category */}
                    <div style={{ height: '7px', background: 'var(--bg-surface-alt)', borderRadius: '3px', overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${t1}%`, background: '#d97706', borderRadius: '3px' }} />
                    </div>
                    {/* Top-5 Category */}
                    <div style={{ height: '7px', background: 'var(--bg-surface-alt)', borderRadius: '3px', overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${t5}%`, background: '#2563eb', borderRadius: '3px' }} />
                    </div>
                    {/* Product SKU Top-1 */}
                    <div style={{ height: '7px', background: 'var(--bg-surface-alt)', borderRadius: '3px', overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${prodT1}%`, background: '#7c3aed', borderRadius: '3px' }} />
                    </div>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                    <span style={{ color: '#d97706', fontWeight: 700 }} title="Top-1 Category">{t1}%</span>
                    <span style={{ color: 'var(--text-muted)' }}>/</span>
                    <span style={{ color: '#2563eb', fontWeight: 700 }} title="Top-5 Category">{t5}%</span>
                    <span style={{ color: 'var(--text-muted)' }}>/</span>
                    <span style={{ color: '#7c3aed', fontWeight: 700 }} title="Exact Product SKU">{prodT1}%</span>
                  </div>
                </div>
              );
            })}
        </div>
      </div>

      {/* ── FAILED EXAMPLES INSPECTOR GALLERY ── */}
      <div className="ui-card" style={{ padding: '1.5rem', border: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, margin: 0 }}>
              Failed Examples Gallery ({filteredFailures.length} Displayed)
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Inspect cases where the model made a wrong match or dropped below threshold (0.75).
            </span>
          </div>

          {/* Filters */}
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
            {/* Condition Filter */}
            <select
              value={selectedCondition}
              onChange={(e) => setSelectedCondition(e.target.value)}
              style={{
                padding: '6px 12px',
                borderRadius: '6px',
                border: '1px solid var(--border)',
                background: 'var(--bg-surface)',
                color: 'var(--text-main)',
                fontSize: '0.8rem'
              }}
            >
              <option value="all">All Conditions</option>
              {Object.keys(perCondition).map((c) => (
                <option key={c} value={c}>
                  {c.replace(/_/g, ' ')}
                </option>
              ))}
            </select>

            {/* Failure Type Filter */}
            <select
              value={selectedFailureType}
              onChange={(e) => setSelectedFailureType(e.target.value)}
              style={{
                padding: '6px 12px',
                borderRadius: '6px',
                border: '1px solid var(--border)',
                background: 'var(--bg-surface)',
                color: 'var(--text-main)',
                fontSize: '0.8rem'
              }}
            >
              <option value="all">All Failures</option>
              <option value="unknown">Sub-Threshold UNKNOWN (&lt; 0.75)</option>
              <option value="wrong_match">Wrong Match (&ge; 0.75 mismatch)</option>
            </select>
          </div>
        </div>

        {/* Grid of Failed Cards */}
        {filteredFailures.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            No failures match the selected filter.
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '1rem' }}>
            {filteredFailures.map((item) => (
              <div
                key={item.image_id}
                style={{
                  border: '1px solid var(--border)',
                  borderRadius: '10px',
                  background: 'var(--bg-surface)',
                  overflow: 'hidden',
                  display: 'flex',
                  flexDirection: 'column',
                  transition: 'transform 0.15s ease, box-shadow 0.15s ease',
                  cursor: 'pointer'
                }}
                onClick={() => setInspectModalItem(item)}
              >
                <div style={{ position: 'relative', width: '100%', height: '160px', background: '#000' }}>
                  <img
                    src={`/${item.generated_image_path}`}
                    alt={item.image_id}
                    style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                  />
                  <span
                    style={{
                      position: 'absolute',
                      top: '8px',
                      left: '8px',
                      background: 'rgba(0,0,0,0.7)',
                      color: '#fff',
                      fontSize: '0.65rem',
                      fontWeight: 700,
                      padding: '2px 6px',
                      borderRadius: '4px',
                      textTransform: 'uppercase'
                    }}
                  >
                    {item.failure_condition.replace(/_/g, ' ')}
                  </span>
                  <span
                    style={{
                      position: 'absolute',
                      top: '8px',
                      right: '8px',
                      background: item.decision === 'UNKNOWN' ? '#dc2626' : '#ea580c',
                      color: '#fff',
                      fontSize: '0.65rem',
                      fontWeight: 700,
                      padding: '2px 6px',
                      borderRadius: '4px'
                    }}
                  >
                    {item.decision}
                  </span>
                </div>

                <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.75rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Ground Truth:</span>
                    <strong style={{ color: 'var(--text-main)', textTransform: 'capitalize' }}>
                      {item.category} ({item.product_id})
                    </strong>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Top-1 Prediction:</span>
                    <strong style={{ color: item.top1_category_correct ? '#059669' : '#dc2626', textTransform: 'capitalize' }}>
                      {item.top1_category || 'None'}
                    </strong>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Best Similarity:</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: item.best_similarity >= 0.75 ? '#059669' : '#dc2626' }}>
                      {(item.best_similarity * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── DETAIL MODAL ── */}
      {inspectModalItem && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.65)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '1rem'
          }}
          onClick={() => setInspectModalItem(null)}
        >
          <div
            style={{
              background: 'var(--bg-surface)',
              borderRadius: '14px',
              maxWidth: '550px',
              width: '100%',
              padding: '1.5rem',
              border: '1px solid var(--border)',
              boxShadow: '0 20px 40px rgba(0,0,0,0.3)',
              position: 'relative'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setInspectModalItem(null)}
              style={{
                position: 'absolute',
                top: '12px',
                right: '12px',
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--text-muted)'
              }}
            >
              <X size={20} />
            </button>

            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, margin: '0 0 1rem' }}>
              Synthetic Failure Inspection
            </h3>

            <div style={{ width: '100%', height: '240px', background: '#000', borderRadius: '8px', overflow: 'hidden', marginBottom: '1rem' }}>
              <img
                src={`/${inspectModalItem.generated_image_path}`}
                alt={inspectModalItem.image_id}
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.85rem' }}>
              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>CONDITION</span>
                <div style={{ fontWeight: 600, textTransform: 'capitalize' }}>
                  {inspectModalItem.failure_condition.replace(/_/g, ' ')}
                </div>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>VERDICT</span>
                <div style={{ fontWeight: 700, color: inspectModalItem.decision === 'UNKNOWN' ? '#dc2626' : '#059669' }}>
                  {inspectModalItem.decision}
                </div>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>GROUND TRUTH</span>
                <div style={{ fontWeight: 600, textTransform: 'capitalize' }}>
                  {inspectModalItem.category} ({inspectModalItem.product_id})
                </div>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>TOP-1 RETRIEVED</span>
                <div style={{ fontWeight: 600, textTransform: 'capitalize', color: inspectModalItem.top1_category_correct ? '#059669' : '#dc2626' }}>
                  {inspectModalItem.top1_category || 'None'} ({inspectModalItem.top1_product_id || 'N/A'})
                </div>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>SIMILARITY SCORE</span>
                <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                  {(inspectModalItem.best_similarity * 100).toFixed(2)}%
                </div>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>LATENCY</span>
                <div style={{ fontFamily: 'var(--font-mono)' }}>
                  {inspectModalItem.latency_ms} ms
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
