import React, { useState, useEffect } from 'react';
import { X, Camera, Check, AlertTriangle } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '';

export default function QRScanner({ isOpen, onClose, offer, onSuccess }) {
  const [stage, setStage] = useState('scanning'); // scanning | amount | processing | success | error
  const [scannedMerchant, setScannedMerchant] = useState(null);
  const [paymentAmount, setPaymentAmount] = useState('150');
  const [redemptionDetails, setRedemptionDetails] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (isOpen) {
      setStage('scanning');
      setScannedMerchant(null);
      setPaymentAmount('150');
      setRedemptionDetails(null);
      setErrorMessage('');
    }
  }, [isOpen]);

  const handleScan = (isCorrectMerchant) => {
    if (isCorrectMerchant) {
      setScannedMerchant(offer.merchant_name);
      setStage('amount');
    } else {
      setScannedMerchant('Sharma General Store');
      setErrorMessage('This offer is only valid at ' + offer.merchant_name);
      setStage('error');
    }
  };

  const handlePay = async () => {
    if (!paymentAmount || parseFloat(paymentAmount) <= 0) return;
    
    setStage('processing');
    
    try {
      const campaignId = offer.campaign_id || parseInt(offer.id.split('_')[0]);
      const customerId = offer.customer_id || parseInt(offer.id.split('_')[1]);
      
      const response = await fetch(`${API_BASE}/customer/${customerId}/redeem/${campaignId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payment_amount: parseFloat(paymentAmount) })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setRedemptionDetails(data.redemption);
        setStage('success');
        setTimeout(() => onSuccess?.(offer, data.redemption), 2500);
      } else {
        setErrorMessage(data.message || 'Could not redeem offer');
        setStage('error');
      }
    } catch (error) {
      setErrorMessage('Connection error. Please try again.');
      setStage('error');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="scanner-overlay" style={{ display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ padding: '48px 16px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <button 
          onClick={onClose}
          style={{ 
            background: 'rgba(255,255,255,0.1)', 
            border: 'none', 
            borderRadius: '50%',
            width: '40px',
            height: '40px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer'
          }}
        >
          <X size={20} style={{ color: 'white' }} />
        </button>
        <div style={{ color: 'white', fontWeight: '600', fontSize: '16px' }}>Scan & Pay</div>
        <div style={{ width: '40px' }} />
      </div>

      {/* Content */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '24px' }}>
        
        {/* Scanning */}
        {stage === 'scanning' && (
          <>
            <div className="scanner-frame" style={{ marginBottom: '24px' }}>
              <div className="scanner-corner tl" />
              <div className="scanner-corner tr" />
              <div className="scanner-corner bl" />
              <div className="scanner-corner br" />
              <div className="scan-line" />
              <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Camera size={48} style={{ color: 'rgba(255,255,255,0.2)' }} />
              </div>
            </div>
            
            <div style={{ color: 'white', textAlign: 'center', marginBottom: '8px' }}>
              Point camera at merchant's QR code
            </div>
            <div style={{ color: 'rgba(255,255,255,0.6)', textAlign: 'center', fontSize: '13px', marginBottom: '24px' }}>
              {offer?.merchant_name}
            </div>

            {/* Offer reminder */}
            <div style={{ 
              background: 'rgba(255,255,255,0.1)', 
              borderRadius: '8px', 
              padding: '12px 16px',
              width: '100%',
              maxWidth: '280px'
            }}>
              <div style={{ color: 'rgba(255,255,255,0.7)', fontSize: '12px' }}>Your offer</div>
              <div style={{ color: 'white', fontSize: '24px', fontWeight: '700' }}>{offer?.cashback_percent}% off</div>
            </div>

            {/* Demo buttons */}
            <div style={{ marginTop: '32px', width: '100%', maxWidth: '280px' }}>
              <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '11px', textAlign: 'center', marginBottom: '8px' }}>
                Demo: Simulate scan
              </div>
              <button
                onClick={() => handleScan(true)}
                style={{
                  width: '100%',
                  padding: '12px',
                  background: 'var(--green)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontWeight: '500',
                  cursor: 'pointer',
                  marginBottom: '8px'
                }}
              >
                Scan correct merchant
              </button>
              <button
                onClick={() => handleScan(false)}
                style={{
                  width: '100%',
                  padding: '12px',
                  background: 'var(--red)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontWeight: '500',
                  cursor: 'pointer'
                }}
              >
                Scan wrong merchant
              </button>
            </div>
          </>
        )}

        {/* Amount Input */}
        {stage === 'amount' && (
          <div style={{ width: '100%', maxWidth: '280px', textAlign: 'center' }}>
            <div style={{ 
              width: '64px', 
              height: '64px', 
              background: 'var(--accent)', 
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px'
            }}>
              <Check size={32} style={{ color: 'white' }} />
            </div>
            
            <div style={{ color: 'white', fontWeight: '600', fontSize: '18px', marginBottom: '4px' }}>
              Merchant Verified
            </div>
            <div style={{ color: 'rgba(255,255,255,0.7)', fontSize: '14px', marginBottom: '24px' }}>
              {scannedMerchant}
            </div>

            <div style={{ 
              background: 'rgba(255,255,255,0.1)', 
              borderRadius: '8px', 
              padding: '16px',
              marginBottom: '16px'
            }}>
              <div style={{ color: 'rgba(255,255,255,0.7)', fontSize: '12px', marginBottom: '8px' }}>
                Enter payment amount
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}>
                <span style={{ color: 'white', fontSize: '24px' }}>₹</span>
                <input
                  type="number"
                  value={paymentAmount}
                  onChange={(e) => setPaymentAmount(e.target.value)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'white',
                    fontSize: '32px',
                    fontWeight: '700',
                    width: '100px',
                    textAlign: 'center',
                    outline: 'none'
                  }}
                  className="tabular-nums"
                />
              </div>
              
              <div style={{ 
                borderTop: '1px solid rgba(255,255,255,0.2)', 
                marginTop: '12px', 
                paddingTop: '12px',
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: '14px'
              }}>
                <span style={{ color: 'rgba(255,255,255,0.7)' }}>You pay</span>
                <span style={{ color: 'var(--green)', fontWeight: '600' }} className="tabular-nums">
                  ₹{Math.round(parseFloat(paymentAmount || 0) * (1 - offer?.cashback_percent / 100))}
                </span>
              </div>
            </div>

            <button
              onClick={handlePay}
              style={{
                width: '100%',
                padding: '14px',
                background: 'var(--accent)',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                fontWeight: '600',
                fontSize: '15px',
                cursor: 'pointer'
              }}
            >
              Pay ₹{Math.round(parseFloat(paymentAmount || 0) * (1 - offer?.cashback_percent / 100))}
            </button>
          </div>
        )}

        {/* Processing */}
        {stage === 'processing' && (
          <div style={{ textAlign: 'center' }}>
            <div style={{ 
              width: '48px', 
              height: '48px', 
              border: '3px solid rgba(255,255,255,0.2)',
              borderTopColor: 'white',
              borderRadius: '50%',
              margin: '0 auto 16px',
              animation: 'spin 1s linear infinite'
            }} />
            <div style={{ color: 'white', fontWeight: '500' }}>Processing payment...</div>
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          </div>
        )}

        {/* Success */}
        {stage === 'success' && redemptionDetails && (
          <div style={{ width: '100%', maxWidth: '280px', textAlign: 'center' }}>
            <div style={{ 
              width: '72px', 
              height: '72px', 
              background: 'var(--green)', 
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px'
            }}>
              <Check size={36} style={{ color: 'white' }} />
            </div>
            
            <div style={{ color: 'white', fontWeight: '600', fontSize: '20px', marginBottom: '24px' }}>
              Payment Successful
            </div>

            <div style={{ 
              background: 'rgba(255,255,255,0.1)', 
              borderRadius: '8px', 
              padding: '16px',
              textAlign: 'left'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: '13px' }}>Original amount</span>
                <span style={{ color: 'white', fontSize: '13px' }} className="tabular-nums">₹{redemptionDetails.original_amount}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: 'var(--green)', fontSize: '13px' }}>Discount ({redemptionDetails.discount_percent}%)</span>
                <span style={{ color: 'var(--green)', fontSize: '13px', fontWeight: '500' }} className="tabular-nums">-₹{redemptionDetails.discount_amount}</span>
              </div>
              <div style={{ 
                borderTop: '1px solid rgba(255,255,255,0.2)', 
                marginTop: '8px', 
                paddingTop: '8px',
                display: 'flex', 
                justifyContent: 'space-between'
              }}>
                <span style={{ color: 'white', fontWeight: '600' }}>You paid</span>
                <span style={{ color: 'white', fontWeight: '700', fontSize: '18px' }} className="tabular-nums">₹{redemptionDetails.final_amount}</span>
              </div>
            </div>

            <div style={{ color: 'var(--green)', marginTop: '16px', fontSize: '14px' }}>
              You saved ₹{redemptionDetails.discount_amount}!
            </div>
          </div>
        )}

        {/* Error */}
        {stage === 'error' && (
          <div style={{ width: '100%', maxWidth: '280px', textAlign: 'center' }}>
            <div style={{ 
              width: '72px', 
              height: '72px', 
              background: 'var(--red)', 
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px'
            }}>
              <AlertTriangle size={36} style={{ color: 'white' }} />
            </div>
            
            <div style={{ color: 'white', fontWeight: '600', fontSize: '18px', marginBottom: '8px' }}>
              {scannedMerchant ? 'Wrong Merchant' : 'Error'}
            </div>
            <div style={{ color: 'rgba(255,255,255,0.7)', fontSize: '14px', marginBottom: '24px' }}>
              {errorMessage}
            </div>

            <button
              onClick={() => setStage('scanning')}
              style={{
                width: '100%',
                padding: '14px',
                background: 'white',
                color: 'var(--text-primary)',
                border: 'none',
                borderRadius: '8px',
                fontWeight: '600',
                cursor: 'pointer'
              }}
            >
              Try Again
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
