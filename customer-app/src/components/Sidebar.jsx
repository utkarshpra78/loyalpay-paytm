import React from 'react';
import { X, Home, Gift, User, Settings, HelpCircle, LogOut } from 'lucide-react';

export default function Sidebar({ isOpen, onClose, customer, offersCount, onNavigate, activePage }) {
  if (!isOpen) return null;

  return (
    <>
      {/* Overlay */}
      <div 
        className="sidebar-overlay"
        onClick={onClose}
      />
      
      {/* Sidebar */}
      <div className={`sidebar ${isOpen ? 'open' : ''}`}>
        {/* Header */}
        <div style={{ 
          padding: '16px', 
          borderBottom: '1px solid var(--divider)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div>
            <div style={{ fontWeight: '600', fontSize: '16px' }}>{customer.name}</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>{customer.phone}</div>
          </div>
          <button 
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}
          >
            <X size={20} style={{ color: 'var(--text-muted)' }} />
          </button>
        </div>

        {/* Menu Items */}
        <div style={{ padding: '8px 0' }}>
          <MenuItem 
            icon={Home} 
            label="Home" 
            active={activePage === 'home'}
            onClick={() => { onNavigate('home'); onClose(); }}
          />
          <MenuItem 
            icon={Gift} 
            label="Offers" 
            active={activePage === 'offers'}
            badge={offersCount > 0 ? offersCount : null}
            onClick={() => { onNavigate('offers'); onClose(); }}
          />
          <MenuItem 
            icon={User} 
            label="Profile" 
            onClick={onClose}
          />
          <MenuItem 
            icon={Settings} 
            label="Settings" 
            onClick={onClose}
          />
          <MenuItem 
            icon={HelpCircle} 
            label="Help & Support" 
            onClick={onClose}
          />
        </div>

        {/* Footer */}
        <div style={{ 
          position: 'absolute', 
          bottom: 0, 
          left: 0, 
          right: 0, 
          padding: '16px',
          borderTop: '1px solid var(--divider)'
        }}>
          <button style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            color: 'var(--red)',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: '500'
          }}>
            <LogOut size={18} />
            Log out
          </button>
        </div>
      </div>
    </>
  );
}

function MenuItem({ icon: Icon, label, active, badge, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        width: '100%',
        padding: '12px 16px',
        background: active ? 'var(--accent-light)' : 'transparent',
        border: 'none',
        cursor: 'pointer',
        textAlign: 'left'
      }}
    >
      <Icon 
        size={20} 
        style={{ color: active ? 'var(--accent)' : 'var(--text-secondary)' }} 
      />
      <span style={{ 
        flex: 1, 
        fontSize: '14px', 
        fontWeight: active ? '600' : '400',
        color: active ? 'var(--accent)' : 'var(--text-primary)'
      }}>
        {label}
      </span>
      {badge && (
        <span style={{
          background: 'var(--accent)',
          color: 'white',
          fontSize: '11px',
          fontWeight: '600',
          padding: '2px 8px',
          borderRadius: '10px',
          minWidth: '20px',
          textAlign: 'center'
        }}>
          {badge}
        </span>
      )}
    </button>
  );
}
