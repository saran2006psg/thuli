import React, { useState, useEffect } from 'react';
import {
  Search,
  Filter,
  Layers,
  Camera,
  RotateCw,
  Eye,
  CheckCircle2,
  ChevronRight,
  X,
  ExternalLink
} from 'lucide-react';
import { JEWELLERY_TYPES } from './CollectDataTab';

export default function CollectionsTab({ onSelectProduct, onTestInSearch }) {
  const [products, setProducts] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all'); // 'all' | 'in_progress' | 'completed' | 'uncollected'
  const [offset, setOffset] = useState(0);
  const limit = 24;

  // Stumper detail modal
  const [modalProduct, setModalProduct] = useState(null);
  const [modalStumpers, setModalStumpers] = useState(null);
  const [isLoadingModal, setIsLoadingModal] = useState(false);

  const fetchProducts = async (resetOffset = false) => {
    setIsLoading(true);
    const targetOffset = resetOffset ? 0 : offset;
    if (resetOffset) setOffset(0);

    const params = new URLSearchParams();
    if (searchQuery.trim()) params.append('q', searchQuery.trim());
    if (selectedCategory !== 'all') params.append('category', selectedCategory);
    if (selectedStatus !== 'all') params.append('status', selectedStatus);
    params.append('limit', String(limit));
    params.append('offset', String(targetOffset));

    try {
      const res = await fetch(`/api/catalogue/products?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setProducts(data.products || []);
        setTotalCount(data.total || 0);
      }
    } catch (err) {
      console.warn('Could not fetch products:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchProducts(true);
    }, 250);
    return () => clearTimeout(timer);
  }, [searchQuery, selectedCategory, selectedStatus]);

  useEffect(() => {
    if (offset > 0) {
      fetchProducts(false);
    }
  }, [offset]);

  // Open preview modal for a product
  const handleOpenPreview = async (product) => {
    setModalProduct(product);
    setIsLoadingModal(true);
    try {
      const res = await fetch(`/api/stumper/product/${product.product_id}`);
      if (res.ok) {
        const data = await res.json();
        setModalStumpers(data);
      }
    } catch (err) {
      console.warn('Could not load modal stumpers:', err);
    } finally {
      setIsLoadingModal(false);
    }
  };

  return (
    <div>
      {/* ── Toolbar: Search & Filters ── */}
      <div className="ui-card" style={{ marginBottom: '1.5rem' }}>
        <div className="collections-toolbar">
          <div className="toolbar-search-row">
            <div style={{ position: 'relative', flex: 1 }}>
              <input
                type="text"
                className="search-input-field"
                placeholder="Search products by ID (e.g. JW_006158) or title..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ width: '100%', paddingLeft: '2.5rem' }}
              />
              <Search
                size={16}
                style={{
                  position: 'absolute',
                  left: '1rem',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: 'var(--text-muted)'
                }}
              />
            </div>
          </div>

          {/* Jewellery Type Filter Pills */}
          <div>
            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.4rem' }}>
              JEWELLERY TYPE
            </div>
            <div className="filter-pills-row">
              <button
                className={`filter-pill-btn ${selectedCategory === 'all' ? 'active' : ''}`}
                onClick={() => setSelectedCategory('all')}
              >
                All Types
              </button>
              {JEWELLERY_TYPES.map((t) => (
                <button
                  key={t.id}
                  className={`filter-pill-btn ${selectedCategory === t.id ? 'active' : ''}`}
                  onClick={() => setSelectedCategory(t.id)}
                >
                  {t.icon} {t.name}
                </button>
              ))}
            </div>
          </div>

          {/* Progress Status Filter Pills */}
          <div>
            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.4rem' }}>
              COLLECTION PROGRESS
            </div>
            <div className="filter-pills-row">
              <button
                className={`filter-pill-btn ${selectedStatus === 'all' ? 'active' : ''}`}
                onClick={() => setSelectedStatus('all')}
              >
                All ({totalCount})
              </button>
              <button
                className={`filter-pill-btn ${selectedStatus === 'in_progress' ? 'active' : ''}`}
                onClick={() => setSelectedStatus('in_progress')}
              >
                In Progress (1-9)
              </button>
              <button
                className={`filter-pill-btn ${selectedStatus === 'completed' ? 'active' : ''}`}
                onClick={() => setSelectedStatus('completed')}
              >
                ✓ Completed (10/10)
              </button>
              <button
                className={`filter-pill-btn ${selectedStatus === 'uncollected' ? 'active' : ''}`}
                onClick={() => setSelectedStatus('uncollected')}
              >
                Not Started (0/10)
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ── Products Grid ── */}
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-muted)' }}>
          <RotateCw size={32} className="spin-anim" style={{ marginBottom: '0.75rem' }} />
          <div>Loading jewellery catalogue collections...</div>
        </div>
      ) : products.length > 0 ? (
        <>
          <div className="products-collection-grid">
            {products.map((p) => {
              const hasPhotos = p.stumper_count > 0;
              const isCompleted = p.is_complete;

              return (
                <div key={p.product_id} className="product-collection-card">
                  {/* Thumbnail Image */}
                  <div
                    className="product-card-img-wrap"
                    onClick={() => handleOpenPreview(p)}
                    style={{ cursor: 'pointer' }}
                  >
                    <img
                      src={p.image_url}
                      alt={p.product_name}
                      className="product-card-img"
                      loading="lazy"
                    />
                    <div style={{
                      position: 'absolute',
                      top: '8px',
                      right: '8px',
                      background: isCompleted ? 'rgba(5, 150, 105, 0.9)' : hasPhotos ? 'rgba(217, 119, 6, 0.9)' : 'rgba(0, 0, 0, 0.65)',
                      color: 'white',
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      padding: '2px 8px',
                      borderRadius: '999px',
                      backdropFilter: 'blur(4px)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}>
                      {isCompleted && <CheckCircle2 size={12} />}
                      {p.stumper_count}/10
                    </div>
                  </div>

                  {/* Body */}
                  <div className="product-card-body">
                    <div className="product-card-title-row">
                      <span className="product-card-pid">{p.product_id}</span>
                      <span className="badge" style={{ textTransform: 'capitalize' }}>
                        {p.category}
                      </span>
                    </div>

                    <div className="product-card-name" title={p.product_name}>
                      {p.product_name}
                    </div>

                    {/* Progress Bar */}
                    <div style={{ marginTop: 'auto', paddingTop: '0.35rem' }}>
                      <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        fontSize: '0.75rem',
                        marginBottom: '4px',
                        color: 'var(--text-secondary)'
                      }}>
                        <span>Stumpers</span>
                        <strong>{p.stumper_count} of 10 ({p.progress_percent}%)</strong>
                      </div>
                      <div className="progress-track" style={{ height: '6px' }}>
                        <div
                          className="progress-fill"
                          style={{
                            width: `${p.progress_percent}%`,
                            background: isCompleted ? 'var(--success)' : undefined
                          }}
                        />
                      </div>
                    </div>

                    {/* Actions */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginTop: '0.5rem' }}>
                      <button
                        className="btn-primary"
                        onClick={() => onSelectProduct(p)}
                        style={{ padding: '0.45rem', fontSize: '0.8rem', justifyContent: 'center' }}
                      >
                        <Camera size={14} />
                        {hasPhotos ? 'Continue' : 'Collect'}
                      </button>
                      <button
                        className="btn-secondary"
                        onClick={() => handleOpenPreview(p)}
                        style={{ padding: '0.45rem', fontSize: '0.8rem', justifyContent: 'center' }}
                      >
                        <Eye size={14} />
                        Details
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pagination Controls */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '1rem',
            marginTop: '2rem',
          }}>
            <button
              className="btn-secondary"
              disabled={offset === 0}
              onClick={() => setOffset(prev => Math.max(0, prev - limit))}
            >
              Previous
            </button>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
              Showing {offset + 1} - {Math.min(offset + limit, totalCount)} of {totalCount} items
            </span>
            <button
              className="btn-secondary"
              disabled={offset + limit >= totalCount}
              onClick={() => setOffset(prev => prev + limit)}
            >
              Next
            </button>
          </div>
        </>
      ) : (
        <div className="ui-card" style={{ textAlign: 'center', padding: '3.5rem', color: 'var(--text-muted)' }}>
          <Layers size={36} style={{ marginBottom: '0.75rem', opacity: 0.5 }} />
          <h3 style={{ color: 'var(--text-main)', marginBottom: '0.5rem' }}>No Products Found</h3>
          <p>Try adjusting your search query, jewellery type, or progress filter.</p>
        </div>
      )}

      {/* ── Collection Details Modal ── */}
      {modalProduct && (
        <div className="modal-overlay" onClick={() => setModalProduct(null)}>
          <div
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: '750px' }}
          >
            <button className="modal-close-btn" onClick={() => setModalProduct(null)}>
              <X size={18} />
            </button>

            {/* Product Header */}
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1.25rem' }}>
              <img
                src={modalProduct.image_url}
                alt={modalProduct.product_name}
                style={{ width: '70px', height: '70px', borderRadius: '10px', objectFit: 'cover' }}
              />
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <h3 style={{ fontFamily: 'var(--font-mono)', fontSize: '1.2rem' }}>
                    {modalProduct.product_id}
                  </h3>
                  <span className="badge" style={{ textTransform: 'capitalize' }}>
                    {modalProduct.category}
                  </span>
                </div>
                <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                  {modalProduct.product_name}
                </div>
              </div>
            </div>

            {/* Modal Actions */}
            <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem' }}>
              <button
                className="btn-primary"
                onClick={() => {
                  onSelectProduct(modalProduct);
                  setModalProduct(null);
                }}
                style={{ flex: 1 }}
              >
                <Camera size={16} />
                Open in Collect Data Page
              </button>
              <button
                className="btn-secondary"
                onClick={() => {
                  onTestInSearch(modalProduct);
                  setModalProduct(null);
                }}
                style={{ flex: 1 }}
              >
                <Search size={16} />
                Test in Visual Search
              </button>
            </div>

            {/* Condition Photos Grid */}
            <h4 style={{ fontSize: '0.9rem', marginBottom: '0.75rem', color: 'var(--text-main)' }}>
              Captured Conditions ({modalStumpers?.completed_count || 0}/10)
            </h4>

            {isLoadingModal ? (
              <div style={{ textAlign: 'center', padding: '2rem' }}>
                <RotateCw size={24} className="spin-anim" />
              </div>
            ) : modalStumpers?.conditions ? (
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))',
                gap: '0.75rem',
              }}>
                {modalStumpers.conditions.map((c) => (
                  <div
                    key={c.id}
                    style={{
                      border: '1px solid var(--border)',
                      borderRadius: '10px',
                      overflow: 'hidden',
                      background: 'var(--bg-surface-alt)',
                      padding: '0.5rem',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: '0.35rem',
                    }}
                  >
                    <div style={{
                      width: '100%',
                      height: '90px',
                      borderRadius: '6px',
                      overflow: 'hidden',
                      background: '#000',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}>
                      {c.record ? (
                        <img
                          src={c.record.image_url}
                          alt={c.name}
                          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                        />
                      ) : (
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          Pending
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '0.75rem', fontWeight: 600, textAlign: 'center' }}>
                      {c.icon} {c.name}
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
