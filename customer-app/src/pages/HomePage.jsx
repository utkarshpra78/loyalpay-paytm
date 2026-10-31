import React from 'react';
import { 
  Bell, Search, QrCode, Users, Building2, History,
  Smartphone, CreditCard, Zap, Car, Gift, ChevronRight,
  Calendar, TrendingUp, Sparkles
} from 'lucide-react';

export default function HomePage({ customer, offers, onMenuOpen, onViewOffers, onScanQR }) {
  const activeOffers = offers.filter(o => !o.redeemed);

  return (
    <div style={{ paddingBottom: '100px', background: 'var(--bg-page)' }}>
      {/* Header - Paytm style with logo */}
      <div style={{ 
        background: 'white', 
        padding: '12px 16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button 
            onClick={onMenuOpen}
            style={{ 
              width: '40px', 
              height: '40px', 
              borderRadius: '50%', 
              background: '#E8E8E8',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: '600',
              fontSize: '14px',
              color: '#666'
            }}
          >
            {customer.name.split(' ').map(n => n[0]).join('')}
          </button>
          
          {/* Paytm Logo */}
          <span style={{ 
            fontWeight: '800', 
            fontSize: '22px', 
            color: '#00357A',
            fontFamily: 'Arial, sans-serif',
            letterSpacing: '-0.5px'
          }}>
            Paytm
          </span>
        </div>
        
        <Bell size={24} style={{ color: 'var(--text-primary)' }} />
      </div>

      {/* Search Bar */}
      <div style={{ background: 'white', padding: '0 16px 16px' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '12px 16px',
          background: '#F5F5F5',
          borderRadius: '24px'
        }}>
          <Search size={20} style={{ color: '#9E9E9E' }} />
          <span style={{ color: '#9E9E9E', fontSize: '15px' }}>Search for contacts to pay</span>
        </div>
      </div>

      {/* Main UPI Actions - Blue filled circles */}
      <div style={{ 
        background: 'white', 
        padding: '20px 16px',
        display: 'flex',
        justifyContent: 'space-around'
      }}>
        <ActionButtonFilled icon={QrCode} label="Scan any QR" />
        <ActionButtonFilled icon={Users} label="Pay Anyone" />
        <ActionButtonFilled icon={Building2} label="To Bank & Self A/c" />
        <ActionButtonFilled icon={History} label="Balance & History" />
      </div>

      {/* Recharge & Bills - Outlined icons */}
      <div className="card" style={{ marginTop: '8px' }}>
        <div className="card-header">
          <span style={{ fontSize: '17px', fontWeight: '700' }}>Recharge & Bills</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--paytm-blue)' }}>
            <span style={{ fontSize: '14px', fontWeight: '600' }}>View All</span>
            <ChevronRight size={18} />
          </div>
        </div>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-around',
          padding: '0 8px 20px'
        }}>
          <ActionButtonOutlined icon={Smartphone} label="Mobile Recharge" />
          <ActionButtonOutlined icon={CreditCard} label="Credit Card Bill" />
          <ActionButtonOutlined icon={Zap} label="Electricity Bill" />
          <ActionButtonOutlined icon={Car} label="FASTag Recharge" />
        </div>
      </div>

      {/* Offer Reminder Card - Like Mobile plan card */}
      {activeOffers.length > 0 && (
        <div className="card">
          <button
            onClick={onViewOffers}
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '16px',
              width: '100%',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              textAlign: 'left'
            }}
          >
            <div style={{
              width: '44px',
              height: '44px',
              borderRadius: '50%',
              background: '#E8F5E9',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginRight: '12px'
            }}>
              <Gift size={22} style={{ color: 'var(--green)' }} />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: '600', fontSize: '15px', color: 'var(--text-primary)' }}>
                {activeOffers[0].merchant_name}
              </div>
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                {activeOffers[0].cashback_percent}% cashback available
              </div>
            </div>
            <button style={{
              background: 'none',
              border: '1.5px solid var(--paytm-blue)',
              color: 'var(--paytm-blue)',
              borderRadius: '16px',
              padding: '6px 16px',
              fontSize: '13px',
              fontWeight: '600',
              cursor: 'pointer'
            }}>
              Redeem
            </button>
          </button>
        </div>
      )}

      {/* Service Cards Grid */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: '1fr 1fr',
        gap: '8px',
        padding: '0 12px'
      }}>
        {/* Your Rewards Card */}
        <div className="card" style={{ margin: 0, padding: '16px' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            background: '#FFF3E0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '10px'
          }}>
            <Sparkles size={20} style={{ color: '#F57C00' }} />
          </div>
          <div style={{ fontWeight: '600', fontSize: '14px' }}>Your Rewards</div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            {activeOffers.length} offers available
          </div>
        </div>

        {/* Book Holidays Card */}
        <div className="card" style={{ margin: 0, padding: '16px' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            background: '#E3F2FD',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '10px'
          }}>
            <Calendar size={20} style={{ color: '#1976D2' }} />
          </div>
          <div style={{ fontWeight: '600', fontSize: '14px' }}>Book for Holidays</div>
        </div>

        {/* Savings Card */}
        <div className="card" style={{ margin: 0, padding: '16px' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            background: '#FFF8E1',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '10px'
          }}>
            <TrendingUp size={20} style={{ color: '#FFA000' }} />
          </div>
          <div style={{ fontWeight: '600', fontSize: '14px' }}>Grow Gold Savings</div>
        </div>

        {/* All Offers Card */}
        <button 
          onClick={onViewOffers}
          className="card" 
          style={{ margin: 0, padding: '16px', border: 'none', cursor: 'pointer', textAlign: 'left' }}
        >
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            background: '#E8F5E9',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '10px'
          }}>
            <Gift size={20} style={{ color: 'var(--green)' }} />
          </div>
          <div style={{ fontWeight: '600', fontSize: '14px' }}>All Offers</div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            View merchant deals
          </div>
        </button>
      </div>

      {/* Horizontal Chips */}
      <div style={{ 
        display: 'flex', 
        gap: '8px', 
        padding: '16px',
        overflowX: 'auto',
        scrollbarWidth: 'none'
      }}>
        <Chip emoji="🎁" label="Cashback & Offers" />
        <Chip emoji="🛍️" label="Shop & Save" />
        <Chip emoji="💳" label="UPI Rewards" />
      </div>

      {/* Floating Scan QR Button - positioned inside phone frame */}
      <button
        onClick={onScanQR}
        style={{
          position: 'absolute',
          bottom: '24px',
          left: '50%',
          transform: 'translateX(-50%)',
          background: 'linear-gradient(135deg, #1565C0 0%, #0D47A1 100%)',
          color: 'white',
          border: 'none',
          borderRadius: '28px',
          padding: '14px 28px',
          fontSize: '16px',
          fontWeight: '600',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          boxShadow: '0 4px 20px rgba(13, 71, 161, 0.4)',
          cursor: 'pointer',
          zIndex: 30
        }}
      >
        <QrCode size={22} />
        Scan QR
      </button>
    </div>
  );
}

function ActionButtonFilled({ icon: Icon, label }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
      <div style={{
        width: '56px',
        height: '56px',
        borderRadius: '50%',
        background: 'var(--paytm-blue)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <Icon size={24} style={{ color: 'white' }} strokeWidth={1.75} />
      </div>
      <span style={{ 
        fontSize: '12px', 
        color: 'var(--text-primary)', 
        textAlign: 'center',
        maxWidth: '70px',
        lineHeight: '1.3'
      }}>{label}</span>
    </div>
  );
}

function ActionButtonOutlined({ icon: Icon, label }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
      <div style={{
        width: '48px',
        height: '48px',
        borderRadius: '12px',
        border: '1.5px solid #E0E0E0',
        background: 'white',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <Icon size={22} style={{ color: 'var(--paytm-blue)' }} strokeWidth={1.75} />
      </div>
      <span style={{ 
        fontSize: '11px', 
        color: 'var(--text-secondary)', 
        textAlign: 'center',
        maxWidth: '65px',
        lineHeight: '1.3'
      }}>{label}</span>
    </div>
  );
}

function Chip({ emoji, label }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '6px',
      padding: '8px 14px',
      background: 'white',
      borderRadius: '20px',
      border: '1px solid #E8E8E8',
      whiteSpace: 'nowrap',
      fontSize: '13px'
    }}>
      <span>{emoji}</span>
      <span style={{ fontWeight: '500' }}>{label}</span>
    </div>
  );
}
