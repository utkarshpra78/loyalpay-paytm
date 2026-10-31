import React, { useEffect } from 'react';
import { X, Gift } from 'lucide-react';

export default function NotificationToast({ notification, onDismiss, onClick }) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onDismiss();
    }, 5000);

    return () => clearTimeout(timer);
  }, [onDismiss]);

  if (!notification) return null;

  return (
    <div 
      className="notification-toast"
      onClick={onClick}
      style={{ cursor: 'pointer' }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
        <div className="icon-box" style={{ background: 'var(--green-bg)', flexShrink: 0 }}>
          <Gift size={18} style={{ color: 'var(--green)' }} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: '600', fontSize: '13px', marginBottom: '2px' }}>
            {notification.title}
          </div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
            {notification.message}
          </div>
        </div>
        <button 
          onClick={(e) => { e.stopPropagation(); onDismiss(); }}
          style={{ 
            background: 'none', 
            border: 'none', 
            cursor: 'pointer', 
            padding: '2px',
            flexShrink: 0
          }}
        >
          <X size={16} style={{ color: 'var(--text-muted)' }} />
        </button>
      </div>
    </div>
  );
}
