import React, { useState, useEffect, useRef } from 'react';
import {
  Camera,
  Upload,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
  Search,
  PlusCircle,
  X,
  Eye,
  Trash2,
  Check,
  AlertCircle,
  ExternalLink,
  ChevronRight,
  RefreshCw,
  Info
} from 'lucide-react';
import WebcamCaptureModal from './WebcamCaptureModal';

export const JEWELLERY_TYPES = [
  { id: 'ring', name: 'Ring', icon: '💍' },
  { id: 'necklace', name: 'Necklace', icon: '📿' },
  { id: 'bracelet', name: 'Bracelet', icon: '⭕' },
  { id: 'earring', name: 'Earrings', icon: '✨' },
  { id: 'pendant', name: 'Pendant', icon: '💎' },
  { id: 'chain', name: 'Chain', icon: '🔗' },
  { id: 'anklet', name: 'Anklet', icon: '🦶' },
  { id: 'other', name: 'Other', icon: '🏷️' },
];

export const STUMPER_CONDITIONS = [
  {
    id: 'normal',
    name: 'Normal',
    icon: '☀️',
    description: 'Clear reference photo under clean, balanced ambient lighting.',
  },
  {
    id: 'bad_lighting',
    name: 'Bad Lighting',
    icon: '💡',
    description: 'Underexposed, dim room, harsh shadows, or uneven low light.',
  },
  {
    id: 'bright_lighting',
    name: 'Bright Lighting',
    icon: '⚡',
    description: 'Overexposed, harsh direct sunlight or high-intensity phone flash glare.',
  },
  {
    id: 'odd_angle',
    name: 'Odd Angle',
    icon: '📐',
    description: 'Extreme tilt, steep top-down, side-profile, or diagonal perspective.',
  },
  {
    id: 'occlusion',
    name: 'Occlusion',
    icon: '🙈',
    description: 'Partially covered by fingers, jewellery tag, cloth, or case rim.',
  },
  {
    id: 'clutter',
    name: 'Clutter',
    icon: '📦',
    description: 'Placed next to keys, coins, patterned textiles, or busy background.',
  },
  {
    id: 'motion_blur',
    name: 'Motion Blur',
    icon: '💨',
    description: 'Intentional slight hand movement or camera shake while snapping.',
  },
  {
    id: 'reflection',
    name: 'Reflection',
    icon: '✨',
    description: 'Glass showcase reflection, mirror backdrop, or shiny metallic specular flare.',
  },
  {
    id: 'hand_wrist',
    name: 'Hand/Wrist',
    icon: '✋',
    description: 'Held in palm, worn on finger/wrist, or worn against skin.',
  },
  {
    id: 'distance',
    name: 'Distance',
    icon: '📏',
    description: 'Shot from afar (item occupies < 15% of frame, un-cropped).',
  },
];

export default function CollectDataTab({
  selectedProduct,
  onProductSelected,
  onTestInSearch,
  onStatsRefresh,
}) {
  // Step 1: Selected Jewellery Type
  const [selectedType, setSelectedType] = useState('ring');

  // Step 2: Mode ("select" existing catalogue item vs "create" new product)
  const [productMode, setProductMode] = useState('select');

  // Catalogue product search & selection
  const [catalogueQuery, setCatalogueQuery] = useState('');
  const [catalogueResults, setCatalogueResults] = useState([]);
  const [isLoadingCatalogue, setIsLoadingCatalogue] = useState(false);

  // New Product Creation Form
  const [newProductId, setNewProductId] = useState('');
  const [newProductName, setNewProductName] = useState('');
  const [newProductFile, setNewProductFile] = useState(null);
  const [newProductPreview, setNewProductPreview] = useState(null);
  const [isCreatingProduct, setIsCreatingProduct] = useState(false);
  const [createSuccessMsg, setCreateSuccessMsg] = useState(null);

  // Stumper Progress & Photos
  const [stumperData, setStumperData] = useState(null);
  const [isLoadingStumpers, setIsLoadingStumpers] = useState(false);
  const [uploadingCondition, setUploadingCondition] = useState(null);
  const [conditionNotes, setConditionNotes] = useState({});
  const [uploadError, setUploadError] = useState(null);

  // Full screen image preview modal
  const [modalImage, setModalImage] = useState(null);

  // Live Webcam Modal State
  const [webcamConfig, setWebcamConfig] = useState({
    isOpen: false,
    title: '',
    onCapture: null,
  });

  const openWebcam = (title, onCapture) => {
    setWebcamConfig({
      isOpen: true,
      title,
      onCapture,
    });
  };

  const closeWebcam = () => {
    setWebcamConfig(prev => ({ ...prev, isOpen: false }));
  };

  // Camera & File input refs
  const newProductCameraRef = useRef(null);
  const newProductUploadRef = useRef(null);

  // Load next sequential product ID when entering create mode
  const fetchNextId = async () => {
    try {
      const res = await fetch('/api/catalogue/next-id');
      if (res.ok) {
        const data = await res.json();
        setNewProductId(data.next_product_id);
      }
    } catch (err) {
      console.warn('Could not fetch next product ID:', err);
    }
  };

  useEffect(() => {
    if (productMode === 'create' && !newProductId) {
      fetchNextId();
    }
  }, [productMode]);

  // Load catalogue items when searching or category changes
  useEffect(() => {
    if (productMode === 'select') {
      const timer = setTimeout(() => {
        searchCatalogueItems();
      }, 250);
      return () => clearTimeout(timer);
    }
  }, [catalogueQuery, selectedType, productMode]);

  const searchCatalogueItems = async () => {
    setIsLoadingCatalogue(true);
    try {
      const params = new URLSearchParams();
      params.append('category', selectedType);
      if (catalogueQuery.trim()) {
        params.append('q', catalogueQuery.trim());
      }
      params.append('limit', '18');

      const res = await fetch(`/api/catalogue/products?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setCatalogueResults(data.products || []);
      }
    } catch (err) {
      console.warn('Error fetching catalogue items:', err);
    } finally {
      setIsLoadingCatalogue(false);
    }
  };

  // Fetch stumper photos whenever selectedProduct changes
  const loadProductStumpers = async (productId) => {
    if (!productId) return;
    setIsLoadingStumpers(true);
    setUploadError(null);
    try {
      const res = await fetch(`/api/stumper/product/${productId}`);
      if (res.ok) {
        const data = await res.json();
        setStumperData(data);
      }
    } catch (err) {
      console.warn('Could not load product stumpers:', err);
    } finally {
      setIsLoadingStumpers(false);
    }
  };

  useEffect(() => {
    if (selectedProduct?.product_id) {
      loadProductStumpers(selectedProduct.product_id);
    } else {
      setStumperData(null);
    }
  }, [selectedProduct]);

  // Handle selecting a catalogue product
  const handleSelectProduct = (prod) => {
    onProductSelected(prod);
    setCreateSuccessMsg(null);
    setUploadError(null);
  };

  // Handle choosing clean image for new product
  const handleNewProductImageSelect = (file) => {
    if (!file || !file.type.startsWith('image/')) {
      alert('Please upload a valid image file (JPEG, PNG, WebP).');
      return;
    }
    setNewProductFile(file);
    const reader = new FileReader();
    reader.onload = (e) => setNewProductPreview(e.target.result);
    reader.readAsDataURL(file);
  };

  // Create Product & Index into FAISS
  const handleCreateProduct = async (e) => {
    e.preventDefault();
    if (!newProductFile) {
      alert('Please take or upload an original clean photo of the jewellery item.');
      return;
    }

    setIsCreatingProduct(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append('file', newProductFile);
    formData.append('jewellery_type', selectedType);
    if (newProductId.trim()) formData.append('product_id', newProductId.trim());
    if (newProductName.trim()) formData.append('product_name', newProductName.trim());

    try {
      const res = await fetch('/api/catalogue/create', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Failed to create product');
      }

      const created = await res.json();
      setCreateSuccessMsg(`Product ${created.product_id} successfully created, indexed in FAISS, and added to catalogue!`);

      // Refresh global stats
      if (onStatsRefresh) onStatsRefresh();

      // Set as active product
      const activeProd = {
        product_id: created.product_id,
        product_name: created.product_name,
        category: created.category,
        image_url: created.image_url,
      };
      onProductSelected(activeProd);

      // Reset new product form
      setNewProductFile(null);
      setNewProductPreview(null);
      setNewProductName('');
      fetchNextId();
    } catch (err) {
      setUploadError('Product Creation Error: ' + err.message);
    } finally {
      setIsCreatingProduct(false);
    }
  };

  // Upload stumper photo for a condition
  const handleUploadStumperPhoto = async (conditionId, file) => {
    if (!selectedProduct?.product_id) {
      alert('Please select or create a product first.');
      return;
    }

    if (!file || !file.type.startsWith('image/')) {
      alert('Please upload a valid image (JPEG, PNG, WebP).');
      return;
    }

    setUploadingCondition(conditionId);
    setUploadError(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('product_id', selectedProduct.product_id);
    formData.append('failure_condition', conditionId);
    formData.append('jewellery_type', selectedProduct.category || selectedType);

    const note = conditionNotes[conditionId] || '';
    if (note.trim()) {
      formData.append('notes', note.trim());
    }

    try {
      const res = await fetch('/api/stumper/upload', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Failed to upload photo');
      }

      // Reload stumper details
      await loadProductStumpers(selectedProduct.product_id);
      if (onStatsRefresh) onStatsRefresh();
    } catch (err) {
      setUploadError(`Upload failed for ${conditionId}: ` + err.message);
    } finally {
      setUploadingCondition(null);
    }
  };

  // Delete/Retake condition photo
  const handleDeleteStumper = async (conditionId) => {
    if (!selectedProduct?.product_id) return;
    if (!window.confirm('Delete this photo to take a new one?')) return;

    try {
      const res = await fetch(`/api/stumper/${selectedProduct.product_id}/${conditionId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        loadProductStumpers(selectedProduct.product_id);
      }
    } catch (err) {
      console.warn('Delete failed:', err);
    }
  };

  return (
    <div>
      {/* ── Stepper Navigation ── */}
      <div className="collector-stepper">
        <div className={`step-item ${selectedType ? 'completed' : 'active'}`}>
          <div className="step-num">1</div>
          <span>Jewellery Type</span>
        </div>
        <div className="step-divider" />
        <div className={`step-item ${selectedProduct ? 'completed' : 'active'}`}>
          <div className="step-num">2</div>
          <span>Select / Create Product</span>
        </div>
        <div className="step-divider" />
        <div className={`step-item ${selectedProduct ? 'active' : ''}`}>
          <div className="step-num">3</div>
          <span>Collect 10 Conditions</span>
        </div>
      </div>

      {/* ── Error Banner ── */}
      {uploadError && (
        <div style={{
          padding: '1rem 1.25rem',
          background: 'var(--danger-bg)',
          border: '1px solid var(--danger-border)',
          borderRadius: '12px',
          color: 'var(--danger)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          marginBottom: '1.5rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <AlertCircle size={20} />
            <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>{uploadError}</span>
          </div>
          <button
            onClick={() => setUploadError(null)}
            style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--danger)' }}
          >
            <X size={18} />
          </button>
        </div>
      )}

      {/* ── STEP 1: Select Jewellery Type ── */}
      <div className="ui-card" style={{ marginBottom: '1.5rem' }}>
        <div className="card-title-row">
          <h2 className="card-title">
            <span style={{ fontSize: '1.2rem' }}>1.</span>
            Select Jewellery Type
          </h2>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Active: <strong style={{ color: 'var(--primary)', textTransform: 'capitalize' }}>{selectedType}</strong>
          </span>
        </div>

        <div className="type-grid">
          {JEWELLERY_TYPES.map((t) => (
            <button
              key={t.id}
              className={`type-card-btn ${selectedType === t.id ? 'active' : ''}`}
              onClick={() => setSelectedType(t.id)}
            >
              <span className="type-icon">{t.icon}</span>
              <span>{t.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* ── STEP 2: Choose / Create Product ── */}
      <div className="ui-card" style={{ marginBottom: '1.5rem' }}>
        <div className="card-title-row">
          <h2 className="card-title">
            <span style={{ fontSize: '1.2rem' }}>2.</span>
            Product Selection & Catalogue Original Image
          </h2>
          {selectedProduct && (
            <button
              className="btn-secondary"
              onClick={() => onProductSelected(null)}
              style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
            >
              Switch Product
            </button>
          )}
        </div>

        {!selectedProduct ? (
          <div>
            {/* Mode group */}
            <div className="mode-toggle-group">
              <button
                className={`mode-toggle-btn ${productMode === 'select' ? 'active' : ''}`}
                onClick={() => setProductMode('select')}
              >
                <Search size={15} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
                Select Existing Catalogue Item
              </button>
              <button
                className={`mode-toggle-btn ${productMode === 'create' ? 'active' : ''}`}
                onClick={() => setProductMode('create')}
              >
                <PlusCircle size={15} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
                Create New Product & Index
              </button>
            </div>

            {/* Mode A: Select from Catalogue */}
            {productMode === 'select' && (
              <div>
                <div style={{ position: 'relative', marginBottom: '1rem' }}>
                  <input
                    type="text"
                    className="search-input-field"
                    placeholder={`Search ${selectedType}s by Product ID (e.g. JW_000105) or name...`}
                    value={catalogueQuery}
                    onChange={(e) => setCatalogueQuery(e.target.value)}
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

                {isLoadingCatalogue ? (
                  <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                    <RotateCw size={24} className="spin-anim" style={{ marginBottom: '0.5rem' }} />
                    <div>Loading catalogue {selectedType}s...</div>
                  </div>
                ) : catalogueResults.length > 0 ? (
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
                    gap: '0.85rem',
                    maxHeight: '360px',
                    overflowY: 'auto',
                    padding: '0.25rem',
                  }}>
                    {catalogueResults.map((item) => (
                      <div
                        key={item.product_id}
                        onClick={() => handleSelectProduct(item)}
                        style={{
                          border: '1.5px solid var(--border)',
                          borderRadius: '12px',
                          overflow: 'hidden',
                          cursor: 'pointer',
                          background: 'var(--bg-surface)',
                          transition: 'all 0.18s ease',
                          display: 'flex',
                          flexDirection: 'column',
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--primary)'}
                        onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
                      >
                        <div style={{ height: '110px', background: '#000', overflow: 'hidden' }}>
                          <img
                            src={item.image_url}
                            alt={item.product_name}
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
                            {item.product_id}
                          </div>
                          <div style={{
                            fontSize: '0.75rem',
                            color: 'var(--text-secondary)',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}>
                            {item.product_name}
                          </div>
                          <div style={{
                            marginTop: '0.4rem',
                            fontSize: '0.7rem',
                            color: item.stumper_count > 0 ? 'var(--success)' : 'var(--text-muted)',
                            fontWeight: 600,
                          }}>
                            {item.stumper_count > 0 ? `✓ ${item.stumper_count}/10 photos` : '0/10 photos'}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                    No items found matching '{catalogueQuery}'. Try another query or create a new product.
                  </div>
                )}
              </div>
            )}

            {/* Mode B: Create New Product */}
            {productMode === 'create' && (
              <form onSubmit={handleCreateProduct}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem', marginBottom: '1.25rem' }}>
                  <div>
                    <label className="form-label">
                      Product ID <span style={{ color: 'var(--text-muted)' }}>(auto-generated or custom)</span>
                    </label>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <input
                        type="text"
                        className="form-input"
                        placeholder="e.g. JW_006159"
                        value={newProductId}
                        onChange={(e) => setNewProductId(e.target.value)}
                        style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}
                        required
                      />
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={fetchNextId}
                        title="Generate next sequential ID"
                        style={{ padding: '0.5rem 0.85rem' }}
                      >
                        <RefreshCw size={15} />
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="form-label">Product Name / Title</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder={`e.g. 18K Solitaire ${selectedType}`}
                      value={newProductName}
                      onChange={(e) => setNewProductName(e.target.value)}
                    />
                  </div>
                </div>

                {/* Camera / Photo Capture for Original Clean Photo */}
                <div style={{ marginBottom: '1.5rem' }}>
                  <label className="form-label" style={{ marginBottom: '0.5rem' }}>
                    Original Clean Photo (Phone Camera or File Upload)
                  </label>

                  {/* Hidden camera input with capture="environment" */}
                  <input
                    type="file"
                    ref={newProductCameraRef}
                    accept="image/*"
                    capture="environment"
                    style={{ display: 'none' }}
                    onChange={(e) => {
                      if (e.target.files?.length > 0) {
                        handleNewProductImageSelect(e.target.files[0]);
                      }
                    }}
                  />

                  {/* Hidden file upload input */}
                  <input
                    type="file"
                    ref={newProductUploadRef}
                    accept="image/*"
                    style={{ display: 'none' }}
                    onChange={(e) => {
                      if (e.target.files?.length > 0) {
                        handleNewProductImageSelect(e.target.files[0]);
                      }
                    }}
                  />

                  {!newProductPreview ? (
                    <div className="camera-action-group">
                      <button
                        type="button"
                        className="btn-camera"
                        onClick={() => openWebcam('Capture Original Clean Photo', handleNewProductImageSelect)}
                      >
                        <Camera size={18} />
                        Take Photo with Camera / Webcam
                      </button>
                      <button
                        type="button"
                        className="btn-upload-file"
                        onClick={() => newProductUploadRef.current?.click()}
                      >
                        <Upload size={18} />
                        Upload from Device
                      </button>
                    </div>
                  ) : (
                    <div style={{
                      position: 'relative',
                      borderRadius: '12px',
                      overflow: 'hidden',
                      height: '240px',
                      background: '#000',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}>
                      <img
                        src={newProductPreview}
                        alt="Preview"
                        style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                      />
                      <button
                        type="button"
                        onClick={() => {
                          setNewProductFile(null);
                          setNewProductPreview(null);
                        }}
                        style={{
                          position: 'absolute',
                          top: '10px',
                          right: '10px',
                          background: 'rgba(0,0,0,0.65)',
                          color: 'white',
                          border: 'none',
                          borderRadius: '50%',
                          width: '32px',
                          height: '32px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          cursor: 'pointer',
                        }}
                      >
                        <X size={16} />
                      </button>
                    </div>
                  )}
                </div>

                <button
                  type="submit"
                  className="btn-primary"
                  style={{ width: '100%', minHeight: '46px' }}
                  disabled={isCreatingProduct || !newProductFile}
                >
                  {isCreatingProduct ? (
                    <>
                      <RotateCw size={18} className="spin-anim" />
                      Computing CLIP Embedding & Adding to FAISS Index...
                    </>
                  ) : (
                    <>
                      <PlusCircle size={18} />
                      Create Product & Save Original Image
                    </>
                  )}
                </button>
              </form>
            )}
          </div>
        ) : (
          /* Active Selected Product Card */
          <div>
            {createSuccessMsg && (
              <div style={{
                padding: '0.85rem 1.25rem',
                background: 'var(--success-bg)',
                border: '1px solid var(--success-border)',
                borderRadius: '10px',
                color: 'var(--success)',
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                marginBottom: '1rem',
                fontSize: '0.875rem',
                fontWeight: 600,
              }}>
                <CheckCircle2 size={18} />
                <span>{createSuccessMsg}</span>
              </div>
            )}

            <div style={{
              display: 'flex',
              gap: '1.25rem',
              alignItems: 'center',
              padding: '1rem',
              borderRadius: '14px',
              border: '1.5px solid var(--primary-border)',
              background: 'var(--primary-light)',
              flexWrap: 'wrap',
            }}>
              <div
                style={{
                  width: '90px',
                  height: '90px',
                  borderRadius: '10px',
                  overflow: 'hidden',
                  background: '#000',
                  flexShrink: 0,
                  cursor: 'pointer',
                }}
                onClick={() => setModalImage(selectedProduct.image_url)}
              >
                <img
                  src={selectedProduct.image_url}
                  alt={selectedProduct.product_name}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
              </div>

              <div style={{ flex: 1, minWidth: '200px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.2rem' }}>
                  <span style={{
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 800,
                    fontSize: '1.1rem',
                    color: 'var(--text-main)',
                  }}>
                    {selectedProduct.product_id}
                  </span>
                  <span className="badge" style={{ textTransform: 'capitalize' }}>
                    {selectedProduct.category || selectedType}
                  </span>
                </div>
                <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                  {selectedProduct.product_name}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--success)', fontWeight: 600 }}>
                  ✓ Indexed in FAISS • Ready for Stumper Collection
                </div>
              </div>

              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                <button
                  className="btn-secondary"
                  onClick={() => onTestInSearch(selectedProduct)}
                  style={{ fontSize: '0.85rem' }}
                >
                  <Search size={15} />
                  Test in Visual Search
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── STEP 3: Collect 10 Stumper Conditions ── */}
      {selectedProduct && (
        <div className="ui-card">
          {/* Progress Header */}
          <div className="stumper-progress-card">
            <div className="progress-header-row">
              <div className="progress-title-text">
                <Camera size={20} style={{ color: 'var(--primary)' }} />
                <span>3. Collect 10 Stumper Conditions</span>
              </div>
              <div className={`progress-counter-badge ${stumperData?.is_complete ? 'completed' : ''}`}>
                {stumperData ? `${stumperData.completed_count} / ${stumperData.total_conditions} Completed` : '0 / 10 Completed'}
                {stumperData && ` (${stumperData.percent}%)`}
              </div>
            </div>

            <div className="progress-track">
              <div
                className="progress-fill"
                style={{ width: `${stumperData?.percent || 0}%` }}
              />
            </div>

            <div style={{
              marginTop: '0.75rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.8rem',
              color: 'var(--text-muted)'
            }}>
              <Info size={14} />
              <span>
                Real phone camera photos only. Every uploaded condition is immediately connected to <strong>{selectedProduct.product_id}</strong>.
              </span>
            </div>
          </div>

          {/* 10 Conditions Grid */}
          {isLoadingStumpers ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
              <RotateCw size={28} className="spin-anim" style={{ marginBottom: '0.5rem' }} />
              <div>Loading stumper conditions for {selectedProduct.product_id}...</div>
            </div>
          ) : (
            <div className="conditions-grid">
              {STUMPER_CONDITIONS.map((cond) => {
                const isCaptured = stumperData?.stumpers?.[cond.id];
                const capturedRecord = isCaptured ? stumperData.stumpers[cond.id] : null;
                const isUploading = uploadingCondition === cond.id;

                return (
                  <ConditionCard
                    key={cond.id}
                    condition={cond}
                    capturedRecord={capturedRecord}
                    isUploading={isUploading}
                    noteValue={conditionNotes[cond.id] || ''}
                    onNoteChange={(val) => setConditionNotes(prev => ({ ...prev, [cond.id]: val }))}
                    onTriggerCamera={() => openWebcam(`Capture ${cond.name} Photo`, (file) => handleUploadStumperPhoto(cond.id, file))}
                    onPhotoSelected={(file) => handleUploadStumperPhoto(cond.id, file)}
                    onDelete={() => handleDeleteStumper(cond.id)}
                    onViewModal={(imgUrl) => setModalImage(imgUrl)}
                  />
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── Image Zoom Modal ── */}
      {modalImage && (
        <div className="modal-overlay" onClick={() => setModalImage(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close-btn" onClick={() => setModalImage(null)}>
              <X size={18} />
            </button>
            <img
              src={modalImage}
              alt="Zoomed view"
              style={{ width: '100%', maxHeight: '75vh', objectFit: 'contain', borderRadius: '10px' }}
            />
          </div>
        </div>
      )}

      {/* ── Live Webcam Capture Modal ── */}
      <WebcamCaptureModal
        isOpen={webcamConfig.isOpen}
        title={webcamConfig.title}
        onCapture={webcamConfig.onCapture}
        onClose={closeWebcam}
      />
    </div>
  );
}

// ── Condition Card Component ────────────────────────────────────────────────
function ConditionCard({
  condition,
  capturedRecord,
  isUploading,
  noteValue,
  onNoteChange,
  onTriggerCamera,
  onPhotoSelected,
  onDelete,
  onViewModal,
}) {
  const cameraInputRef = useRef(null);
  const uploadInputRef = useRef(null);

  return (
    <div className={`condition-card ${capturedRecord ? 'is-captured' : ''}`}>
      {/* Hidden native camera capture input */}
      <input
        type="file"
        ref={cameraInputRef}
        accept="image/*"
        capture="environment"
        style={{ display: 'none' }}
        onChange={(e) => {
          if (e.target.files?.length > 0) {
            onPhotoSelected(e.target.files[0]);
          }
        }}
      />

      {/* Hidden standard file picker */}
      <input
        type="file"
        ref={uploadInputRef}
        accept="image/*"
        style={{ display: 'none' }}
        onChange={(e) => {
          if (e.target.files?.length > 0) {
            onPhotoSelected(e.target.files[0]);
          }
        }}
      />

      {/* Header */}
      <div className="condition-header">
        <div className="condition-title-group">
          <div className="condition-icon-badge">{condition.icon}</div>
          <div className="condition-name">{condition.name}</div>
        </div>
        {capturedRecord ? (
          <span style={{
            fontSize: '0.75rem',
            fontWeight: 700,
            background: 'var(--success-bg)',
            color: 'var(--success)',
            border: '1px solid var(--success-border)',
            padding: '2px 8px',
            borderRadius: '999px',
            display: 'flex',
            alignItems: 'center',
            gap: '3px',
          }}>
            <Check size={12} /> Captured
          </span>
        ) : (
          <span style={{
            fontSize: '0.75rem',
            color: 'var(--text-muted)',
            background: 'var(--bg-surface-alt)',
            padding: '2px 8px',
            borderRadius: '999px',
          }}>
            Pending
          </span>
        )}
      </div>

      {/* Description / Guideline */}
      <div className="condition-desc">{condition.description}</div>

      {/* Captured Image or Upload Action */}
      {capturedRecord ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <div className="condition-thumbnail-box">
            <img
              src={capturedRecord.image_url}
              alt={condition.name}
              className="condition-thumbnail-img"
              onClick={() => onViewModal(capturedRecord.image_url)}
            />
          </div>

          {capturedRecord.notes && (
            <div className="condition-note-preview">
              "{capturedRecord.notes}"
            </div>
          )}

          <div className="condition-actions">
            <button
              type="button"
              className="btn-secondary"
              onClick={onTriggerCamera}
              style={{ flex: 1, padding: '0.45rem', fontSize: '0.75rem' }}
            >
              <Camera size={14} /> Retake
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => uploadInputRef.current?.click()}
              style={{ flex: 1, padding: '0.45rem', fontSize: '0.75rem' }}
            >
              <Upload size={14} /> Replace
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={onDelete}
              title="Delete photo"
              style={{ color: 'var(--danger)', padding: '0.45rem 0.65rem' }}
            >
              <Trash2 size={14} />
            </button>
          </div>
        </div>
      ) : isUploading ? (
        <div style={{
          height: '160px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--bg-surface-alt)',
          borderRadius: '10px',
          color: 'var(--primary)',
          gap: '0.5rem',
        }}>
          <RotateCw size={26} className="spin-anim" />
          <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Saving real photo...</span>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <input
            type="text"
            className="form-input"
            placeholder="Optional note (e.g. tungsten bulb, tilt 45°)..."
            value={noteValue}
            onChange={(e) => onNoteChange(e.target.value)}
            style={{ fontSize: '0.8rem', padding: '0.4rem 0.65rem' }}
          />

          <div className="camera-action-group" style={{ margin: 0 }}>
            <button
              type="button"
              className="btn-camera"
              onClick={onTriggerCamera}
            >
              <Camera size={16} />
              Take Photo
            </button>
            <button
              type="button"
              className="btn-upload-file"
              onClick={() => uploadInputRef.current?.click()}
            >
              <Upload size={16} />
              Upload
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
