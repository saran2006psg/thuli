import React, { useState, useEffect } from 'react';
import {
  Database,
  Camera,
  Layers,
  CheckCircle2,
  RotateCw,
  Sparkles,
  PieChart,
  X
} from 'lucide-react';

export default function DatasetTab({ onSelectProductFromPhoto }) {
  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [modalImage, setModalImage] = useState(null);

  const fetchDatasetStats = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/stumper/dataset');
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (err) {
      console.warn('Could not load dataset stats:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDatasetStats();
  }, []);

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '5rem', color: 'var(--text-muted)' }}>
        <RotateCw size={36} className="spin-anim" style={{ marginBottom: '1rem' }} />
        <div>Computing jewellery dataset metrics...</div>
      </div>
    );
  }

  if (!stats) return null;

  // Find max condition count for scaling bars
  const maxConditionCount = Math.max(
    ...(stats.by_condition?.map(c => c.count) || [1]),
    1
  );

  return (
    <div>
      {/* ── High-Level Metric Cards ── */}
      <div className="dataset-stats-grid">
        <div className="metric-card">
          <div className="metric-icon-box" style={{ background: 'var(--primary-light)', color: 'var(--primary)' }}>
            <Database size={24} />
          </div>
          <div>
            <div className="metric-value">
              {stats.total_products_catalogue?.toLocaleString() || '6,157'}
            </div>
            <div className="metric-label">Total Catalogue Products</div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon-box" style={{ background: 'var(--info-bg)', color: 'var(--info)' }}>
            <Camera size={24} />
          </div>
          <div>
            <div className="metric-value">
              {stats.total_stumper_photos?.toLocaleString() || '0'}
            </div>
            <div className="metric-label">Stumper Photos Collected</div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon-box" style={{ background: 'rgba(217, 119, 6, 0.12)', color: 'var(--primary)' }}>
            <Layers size={24} />
          </div>
          <div>
            <div className="metric-value">
              {stats.products_with_stumpers?.toLocaleString() || '0'}
            </div>
            <div className="metric-label">Products with Stumpers</div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon-box" style={{ background: 'var(--success-bg)', color: 'var(--success)' }}>
            <CheckCircle2 size={24} />
          </div>
          <div>
            <div className="metric-value">
              {stats.completed_products_count?.toLocaleString() || '0'}
            </div>
            <div className="metric-label">Complete 10/10 Sets</div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '1.5rem', marginBottom: '1.5rem' }}>
        {/* ── Images by Condition ── */}
        <div className="ui-card">
          <div className="card-title-row">
            <h2 className="card-title">
              <Camera size={18} style={{ color: 'var(--primary)' }} />
              Images by Stumper Condition
            </h2>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {stats.by_condition?.map((cond) => {
              const pct = Math.round((cond.count / maxConditionCount) * 100);
              return (
                <div key={cond.id} className="dist-item">
                  <div className="dist-label">
                    <span>{cond.icon}</span>
                    <span>{cond.name}</span>
                  </div>
                  <div className="dist-bar-track">
                    <div
                      className="dist-bar-fill"
                      style={{
                        width: `${pct}%`,
                        background: cond.count > 0 ? undefined : 'transparent'
                      }}
                    />
                  </div>
                  <div className="dist-count">{cond.count}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Images by Jewellery Type ── */}
        <div className="ui-card">
          <div className="card-title-row">
            <h2 className="card-title">
              <PieChart size={18} style={{ color: 'var(--primary)' }} />
              Images by Jewellery Type
            </h2>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {Object.entries(stats.by_jewellery_type || {}).length > 0 ? (
              Object.entries(stats.by_jewellery_type).map(([jType, count]) => (
                <div
                  key={jType}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.75rem 1rem',
                    background: 'var(--bg-surface-alt)',
                    borderRadius: '10px',
                    border: '1px solid var(--border)'
                  }}
                >
                  <span style={{ fontWeight: 600, textTransform: 'capitalize', color: 'var(--text-main)' }}>
                    {jType}
                  </span>
                  <span style={{
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: '999px',
                    background: 'var(--primary-light)',
                    color: 'var(--primary)',
                    fontSize: '0.85rem'
                  }}>
                    {count} photos
                  </span>
                </div>
              ))
            ) : (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                No stumper photos uploaded yet.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Recent Uploads Gallery ── */}
      {stats.recent_uploads?.length > 0 && (
        <div className="ui-card">
          <div className="card-title-row">
            <h2 className="card-title">
              <Sparkles size={18} style={{ color: 'var(--primary)' }} />
              Recently Captured Stumper Photos
            </h2>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
            gap: '1rem',
          }}>
            {stats.recent_uploads.map((photo, i) => (
              <div
                key={photo.image_id || i}
                style={{
                  border: '1px solid var(--border)',
                  borderRadius: '12px',
                  overflow: 'hidden',
                  background: 'var(--bg-surface)',
                  display: 'flex',
                  flexDirection: 'column',
                }}
              >
                <div
                  style={{ height: '120px', background: '#000', overflow: 'hidden', cursor: 'pointer' }}
                  onClick={() => setModalImage(photo.image_url)}
                >
                  <img
                    src={photo.image_url}
                    alt={photo.condition_name || photo.failure_condition}
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    loading="lazy"
                  />
                </div>
                <div style={{ padding: '0.65rem' }}>
                  <div style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.8rem',
                    fontWeight: 700,
                    color: 'var(--primary)',
                  }}>
                    {photo.product_id}
                  </div>
                  <div style={{
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    color: 'var(--text-main)',
                    textTransform: 'capitalize',
                  }}>
                    {photo.condition_name || photo.failure_condition.replace('_', ' ')}
                  </div>
                  {photo.notes && (
                    <div style={{
                      fontSize: '0.7rem',
                      color: 'var(--text-muted)',
                      fontStyle: 'italic',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      marginTop: '2px',
                    }}>
                      "{photo.notes}"
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Image Modal ── */}
      {modalImage && (
        <div className="modal-overlay" onClick={() => setModalImage(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close-btn" onClick={() => setModalImage(null)}>
              <X size={18} />
            </button>
            <img
              src={modalImage}
              alt="Zoomed stumper view"
              style={{ width: '100%', maxHeight: '75vh', objectFit: 'contain', borderRadius: '10px' }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
