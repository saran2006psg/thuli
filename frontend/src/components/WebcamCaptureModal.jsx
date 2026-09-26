import React, { useState, useEffect, useRef } from 'react';
import {
  Camera,
  X,
  RotateCw,
  Check,
  RefreshCw,
  AlertCircle,
  FlipHorizontal,
  Upload
} from 'lucide-react';

export default function WebcamCaptureModal({
  isOpen,
  title = "Live Camera Capture",
  onCapture,
  onClose,
}) {
  const [stream, setStream] = useState(null);
  const [facingMode, setFacingMode] = useState('environment'); // 'environment' (back) or 'user' (front)
  const [capturedBlob, setCapturedBlob] = useState(null);
  const [capturedPreview, setCapturedPreview] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const [videoReady, setVideoReady] = useState(false);

  const videoRef = useRef(null);
  const fallbackInputRef = useRef(null);

  // Callback ref so srcObject is attached the exact instant the video node mounts
  const handleVideoRef = (node) => {
    videoRef.current = node;
    if (node && stream) {
      node.srcObject = stream;
      node.play().catch(e => console.warn('Video play error on mount:', e));
    }
  };

  // Attach stream whenever stream state changes
  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
      videoRef.current.play().catch(e => console.warn('Video play error on stream update:', e));
    }
  }, [stream]);

  // Start webcam stream
  const startCamera = async (mode = facingMode) => {
    setIsInitializing(true);
    setVideoReady(false);
    setErrorMsg(null);
    setCapturedBlob(null);
    setCapturedPreview(null);

    // Stop existing stream tracks
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Camera access (getUserMedia) is not supported by your browser or requires HTTPS / localhost.');
      }

      let newStream;
      try {
        newStream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: mode },
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
          audio: false,
        });
      } catch (err1) {
        // Fallback without facingMode constraint (laptop webcams often don't have environment mode)
        newStream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        });
      }

      setStream(newStream);
      if (videoRef.current) {
        videoRef.current.srcObject = newStream;
        videoRef.current.play().catch(e => console.warn('Play error:', e));
      }
    } catch (err) {
      console.error('Camera error:', err);
      setErrorMsg(
        err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError'
          ? 'Camera permission was denied. Please allow camera access in your browser address bar.'
          : err.message || 'Unable to access camera.'
      );
    } finally {
      setIsInitializing(false);
    }
  };

  // Toggle front/back camera
  const toggleFacingMode = () => {
    const nextMode = facingMode === 'environment' ? 'user' : 'environment';
    setFacingMode(nextMode);
    startCamera(nextMode);
  };

  // Lifecycle when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      startCamera(facingMode);
    } else {
      stopCamera();
    }
    return () => {
      stopCamera();
    };
  }, [isOpen]);

  // Clean stop
  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
  };

  // Take Snapshot from video
  const handleSnap = () => {
    if (!videoRef.current) return;
    const video = videoRef.current;

    const width = video.videoWidth || 1280;
    const height = video.videoHeight || 720;

    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;

    const ctx = canvas.getContext('2d');
    if (facingMode === 'user') {
      ctx.translate(canvas.width, 0);
      ctx.scale(-1, 1);
    }
    ctx.drawImage(video, 0, 0, width, height);

    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        const previewUrl = URL.createObjectURL(blob);
        setCapturedBlob(blob);
        setCapturedPreview(previewUrl);
      },
      'image/jpeg',
      0.95
    );
  };

  // Retake photo
  const handleRetake = () => {
    if (capturedPreview) {
      URL.revokeObjectURL(capturedPreview);
    }
    setCapturedBlob(null);
    setCapturedPreview(null);
    if (videoRef.current && stream) {
      videoRef.current.play().catch(e => console.warn(e));
    }
  };

  // Confirm and use captured photo
  const handleConfirm = () => {
    if (!capturedBlob) return;
    const file = new File([capturedBlob], `camera_${Date.now()}.jpg`, { type: 'image/jpeg' });
    onCapture(file);
    handleClose();
  };

  const handleClose = () => {
    stopCamera();
    if (capturedPreview) {
      URL.revokeObjectURL(capturedPreview);
    }
    setCapturedBlob(null);
    setCapturedPreview(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={handleClose} style={{ zIndex: 120 }}>
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{
          maxWidth: '680px',
          width: '95%',
          background: '#090d16',
          color: '#ffffff',
          borderRadius: '20px',
          border: '1px solid rgba(255,255,255,0.15)',
          padding: '1.25rem',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '1rem',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.85)',
        }}
      >
        {/* Header */}
        <div style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
          paddingBottom: '0.75rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <div style={{
              width: '2rem',
              height: '2rem',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #f59e0b, #d97706)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Camera size={16} color="#fff" />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '1rem' }}>{title}</div>
              <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.6)' }}>
                Position jewellery inside viewfinder and capture
              </div>
            </div>
          </div>

          <button
            onClick={handleClose}
            style={{
              background: 'rgba(255,255,255,0.1)',
              border: 'none',
              borderRadius: '50%',
              width: '32px',
              height: '32px',
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Viewfinder / Video Container */}
        <div style={{
          width: '100%',
          height: '380px',
          borderRadius: '16px',
          overflow: 'hidden',
          background: '#000000',
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: '1px solid rgba(255,255,255,0.1)',
        }}>
          {/* Always mount video so handleVideoRef attaches immediately */}
          <video
            ref={handleVideoRef}
            autoPlay
            playsInline
            muted
            onLoadedMetadata={() => {
              setVideoReady(true);
              videoRef.current?.play().catch(e => console.warn(e));
            }}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              display: capturedPreview ? 'none' : 'block',
              transform: facingMode === 'user' ? 'scaleX(-1)' : 'none',
            }}
          />

          {/* Captured Preview Overlay */}
          {capturedPreview && (
            <img
              src={capturedPreview}
              alt="Captured"
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'contain',
                position: 'absolute',
                inset: 0,
                background: '#000',
              }}
            />
          )}

          {/* Loading Indicator */}
          {isInitializing && !errorMsg && (
            <div style={{
              position: 'absolute',
              inset: 0,
              background: 'rgba(0,0,0,0.7)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#f59e0b',
              gap: '0.5rem',
              zIndex: 10,
            }}>
              <RotateCw size={36} className="spin-anim" />
              <div style={{ fontSize: '0.85rem' }}>Opening camera stream...</div>
            </div>
          )}

          {/* Error Message */}
          {errorMsg && (
            <div style={{
              position: 'absolute',
              inset: 0,
              background: '#090d16',
              textAlign: 'center',
              padding: '2rem',
              color: '#f87171',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.75rem',
              zIndex: 15,
            }}>
              <AlertCircle size={36} />
              <div style={{ fontSize: '0.95rem', fontWeight: 600 }}>{errorMsg}</div>
              <button
                type="button"
                className="btn-camera"
                style={{ width: 'auto', marginTop: '0.5rem', padding: '0.5rem 1.25rem' }}
                onClick={() => fallbackInputRef.current?.click()}
              >
                <Upload size={16} /> Upload Photo from Device Instead
              </button>
              <input
                type="file"
                ref={fallbackInputRef}
                accept="image/*"
                style={{ display: 'none' }}
                onChange={(e) => {
                  if (e.target.files?.length > 0) {
                    onCapture(e.target.files[0]);
                    handleClose();
                  }
                }}
              />
            </div>
          )}

          {/* Viewfinder Target Framing Overlay */}
          {!capturedPreview && !errorMsg && !isInitializing && (
            <>
              <div style={{
                position: 'absolute',
                inset: '24px',
                border: '2px dashed rgba(245, 158, 11, 0.7)',
                borderRadius: '16px',
                pointerEvents: 'none',
              }} />

              {/* Flip camera toggle button */}
              <button
                type="button"
                onClick={toggleFacingMode}
                title="Switch Camera (Front / Back)"
                style={{
                  position: 'absolute',
                  top: '12px',
                  right: '12px',
                  background: 'rgba(0, 0, 0, 0.6)',
                  backdropFilter: 'blur(8px)',
                  color: '#ffffff',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                  borderRadius: '50%',
                  width: '38px',
                  height: '38px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  zIndex: 5,
                }}
              >
                <FlipHorizontal size={18} />
              </button>
            </>
          )}
        </div>

        {/* Footer Actions */}
        <div style={{ width: '100%', display: 'flex', justifyContent: 'center', gap: '1rem', marginTop: '0.25rem' }}>
          {!capturedPreview && !errorMsg && !isInitializing && (
            <button
              type="button"
              onClick={handleSnap}
              title="Capture Photo"
              style={{
                width: '68px',
                height: '68px',
                borderRadius: '50%',
                background: '#ffffff',
                border: '4px solid #f59e0b',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                boxShadow: '0 0 20px rgba(245, 158, 11, 0.4)',
                transition: 'transform 0.1s ease',
              }}
              onMouseDown={(e) => e.currentTarget.style.transform = 'scale(0.92)'}
              onMouseUp={(e) => e.currentTarget.style.transform = 'scale(1)'}
            >
              <div style={{
                width: '52px',
                height: '52px',
                borderRadius: '50%',
                background: '#f59e0b',
              }} />
            </button>
          )}

          {capturedPreview && (
            <div style={{ display: 'flex', gap: '0.75rem', width: '100%' }}>
              <button
                type="button"
                className="btn-secondary"
                onClick={handleRetake}
                style={{
                  flex: 1,
                  minHeight: '44px',
                  background: 'rgba(255,255,255,0.1)',
                  color: '#ffffff',
                  border: '1px solid rgba(255,255,255,0.2)',
                  fontSize: '0.9rem',
                }}
              >
                <RefreshCw size={16} /> Retake
              </button>

              <button
                type="button"
                className="btn-camera"
                onClick={handleConfirm}
                style={{
                  flex: 1,
                  minHeight: '44px',
                  fontSize: '0.9rem',
                }}
              >
                <Check size={18} /> Use This Photo
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
