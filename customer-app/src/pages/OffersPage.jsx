import React, { useState } from 'react';
import { ArrowLeft, Gift, Check, QrCode } from 'lucide-react';
import QRScanner from '../components/QRScanner';

export default function OffersPage({ offers, onBack, onRedeem, customer }) {
  const [scannerOpen, setScannerOpen] = useState(false);
  const [selectedOffer, setSelectedOffer] = useState(null);

  const handleRedeemClick = (offer) => {
    if (offer.redeemed) return;
    setSelectedOffer(offer);
    setScannerOpen(true);
  };

  const handleScanSuccess = (offer, redemptionDetails) => {
    setScannerOpen(false);
    onRedeem?.(offer, redemptionDetails);
  };

  const activeOffers = offers.filter(o => !o.redeemed);
  const redeemedOffers = offers.filter(o => o.redeemed);

  return (
    <div className="min-h-full">
      {/* Header */}
      <div className="section">
        <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button onClick={onBack} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
            <ArrowLeft size={20} style={{ color: 'var(--text-primary)' }} />
          </button>
          <div>
            <div style={{ fontWeight: '600', fontSize: '16px' }}>Your Offers</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
              {activeOffers.length} active, {redeemedOffers.length} used
            </div>
          </div>
        </div>
      </div>

      {/* Empty State */}
      {offers.length === 0 && (
        <div className="section">
          <div className="empty-state">
            <div className="icon-box" style={{ 
              background: '#F3F4F6', 
              width: '64px', 
              height: '64px', 
              margin: '0 auto 16px',
              borderRadius: '50%'
            }}>
              <Gift size={28} style={{ color: 'var(--text-muted)' }} />
            </div>
            <div style={{ color: 'var(--text-secondary)', fontWeight: '500', marginBottom: '4px' }}>
              No offers yet
            </div>
            <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
              When merchants send you cashback offers, they'll appear here
            </div>
          </div>
        </div>
      )}

      {/* Active Offers */}
      {activeOffers.length > 0 && (
        <>
          <div style={{ 
            padding: '12px 16px 8px', 
            fontSize: '11px', 
            fontWeight: '600', 
            color: 'var(--text-muted)',
            textTransform: 'uppercase',
            letterSpacing: '0.3px'
          }}>
            Active ({activeOffers.length})
          </div>
          
          <div className="section">
            {activeOffers.map((offer) => (
              <OfferCard 
                key={offer.id} 
                offer={offer} 
                onRedeem={() => handleRedeemClick(offer)} 
              />
            ))}
          </div>
        </>
      )}

      {/* Redeemed Offers */}
      {redeemedOffers.length > 0 && (
        <>
          <div style={{ 
            padding: '16px 16px 8px', 
            fontSize: '11px', 
            fontWeight: '600', 
            color: 'var(--text-muted)',
            textTransform: 'uppercase',
            letterSpacing: '0.3px'
          }}>
            Used ({redeemedOffers.length})
          </div>
          
          <div className="section">
            {redeemedOffers.map((offer) => (
              <RedeemedOfferCard key={offer.id} offer={offer} />
            ))}
          </div>
        </>
      )}

      {/* How to redeem */}
      {activeOffers.length > 0 && (
        <div style={{ padding: '16px' }}>
          <div style={{ 
            background: 'var(--accent-light)', 
            borderRadius: '8px', 
            padding: '12px',
            fontSize: '13px',
            color: 'var(--accent)'
          }}>
            <strong>How to redeem:</strong> Tap an offer, scan the merchant's QR code, and enter your payment amount. The discount is applied automatically.
          </div>
        </div>
      )}

      <div style={{ height: '16px' }} />

      {/* QR Scanner */}
      <QRScanner 
        isOpen={scannerOpen}
        onClose={() => setScannerOpen(false)}
        offer={selectedOffer}
        onSuccess={handleScanSuccess}
      />
    </div>
  );
}

function OfferCard({ offer, onRedeem }) {
  return (
    <div style={{ borderBottom: '1px solid var(--divider)' }}>
      <div style={{ padding: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', marginBottom: '12px' }}>
          <div className="icon-box" style={{ background: 'var(--green-bg)', width: '44px', height: '44px' }}>
            <Gift size={20} style={{ color: 'var(--green)' }} />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: '600', marginBottom: '2px' }}>{offer.merchant_name}</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
              Valid for {offer.valid_till}
            </div>
          </div>
        </div>

        <div style={{ 
          background: 'var(--green-bg)', 
          borderRadius: '8px', 
          padding: '12px',
          marginBottom: '12px'
        }}>
          <div style={{ fontSize: '12px', color: 'var(--green)', marginBottom: '2px' }}>Cashback</div>
          <div style={{ fontSize: '28px', fontWeight: '700', color: 'var(--green)' }} className="tabular-nums">
            {offer.cashback_percent}%
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            on your next payment
          </div>
        </div>

        <button onClick={onRedeem} className="btn-primary">
          <QrCode size={18} />
          Scan QR to Redeem
        </button>
      </div>
    </div>
  );
}

function RedeemedOfferCard({ offer }) {
  const details = offer.redemption_details;

  return (
    <div className="list-row" style={{ opacity: 0.7 }}>
      <div className="icon-box" style={{ background: 'var(--green-bg)' }}>
        <Check size={18} style={{ color: 'var(--green)' }} />
      </div>
      <div style={{ flex: 1, marginLeft: '12px' }}>
        <div style={{ fontWeight: '500', fontSize: '13px' }}>{offer.merchant_name}</div>
        <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
          {offer.cashback_percent}% off
          {details && ` · Saved ₹${details.discount_amount}`}
        </div>
      </div>
      <span className="badge badge-green">Used</span>
    </div>
  );
}
